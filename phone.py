"""Phone calls with JARVIS through Twilio.

A separate loopback server (VOICE_PHONE_PORT, default 4324) exposes only /twilio/*. It is
published with Tailscale Funnel; the main companion stays private. Every webhook must carry
a valid X-Twilio-Signature, and only Zack's own number may call in. Each call is a normal
conversation: Twilio transcribes speech, the companion answers, the reply plays in the
selected voice. Config: DATA/twilio.json
  {"account_sid","auth_token","from_number","my_number","public_url"}
"""
import base64, hashlib, hmac, json, os, re, secrets, subprocess, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape
import fish_voice

PORT=int(os.environ.get('VOICE_PHONE_PORT','4324'))
CALLS={}      # CallSid or outbound id -> {'conversation': id, 'empty': n, 'opening': audio token}
AUDIO={}      # token -> (path, expires)
LOCK=threading.Lock()
WAIT_LIMIT=40 # 40 x ~1s polls before giving up on a reply
GATHER='<Gather input="speech" action="{action}" method="POST" timeout="10" speechTimeout="auto" speechModel="phone_call" enhanced="true" language="en-US" actionOnEmptyResult="true">{inner}</Gather>'

def config(data):
    try:value=json.loads((data/'twilio.json').read_text())
    except (OSError,ValueError):return None
    needed=['account_sid','auth_token','from_number','my_number','public_url']
    return value if all(isinstance(value.get(k),str) and value[k] for k in needed) else None

def ready(data):
    return config(data) is not None

def digits(number):
    return re.sub(r'\D','',number or '')

def signature(token,url,params):
    payload=url+''.join(k+v for k,v in sorted(params.items()))
    return base64.b64encode(hmac.new(token.encode(),payload.encode(),hashlib.sha1).digest()).decode()

def valid(token,url,params,given):
    # Twilio signs a URL on a non-default port either with or without the port; its own libraries accept both.
    parts=urlparse(url)
    bare=parts._replace(netloc=parts.hostname or '').geturl()
    return any(hmac.compare_digest(signature(token,candidate,params),given) for candidate in {url,bare})

def twiml(body):
    return '<?xml version="1.0" encoding="UTF-8"?><Response>'+body+'</Response>'

def say(text):
    return '<Say voice="Polly.Brian">'+escape(text)+'</Say>'

def audio_token(path,ttl=900):
    token=secrets.token_hex(16)
    with LOCK:
        now=time.time()
        for key in [k for k,(_,expires) in AUDIO.items() if expires<now]:AUDIO.pop(key,None)
        AUDIO[token]=(path,now+ttl)
    return token

def phone_audio(core,source):
    """8 kHz mono mu-law WAV: the format Twilio plays without resampling surprises."""
    target=source.with_name(source.stem+'.phone.wav')
    if not target.is_file() or target.stat().st_mtime<source.stat().st_mtime:
        subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(source),'-ar','8000','-ac','1','-c:a','pcm_mulaw',str(target)],check=True,timeout=30)
    return target

def spoken(core,text):
    """Synthesize a fixed line in the Jarvis voice (cached), or None to fall back to <Say>."""
    secret=fish_voice.key(core.DATA)
    if not secret:return None
    folder=core.DATA/'phone';folder.mkdir(mode=0o700,exist_ok=True)
    path=folder/(hashlib.sha256((fish_voice.MODEL+text).encode()).hexdigest()[:24]+'.wav')
    if not path.is_file():
        pending=path.with_suffix('.pending.wav')
        fish_voice.synthesize(text,pending,secret,threading.Event())
        pending.replace(path)
    return phone_audio(core,path)

def play_or_say(core,base,text):
    try:audio=spoken(core,text)
    except Exception:audio=None
    return f'<Play>{base}/twilio/audio/{audio_token(audio)}.wav</Play>' if audio else say(text)

def new_conversation(core,title):
    item={'id':uuid.uuid4().hex,'title':title,'created':time.time(),'updated':time.time()}
    with core.connect() as db:db.execute('INSERT INTO conversations VALUES(:id,:title,:created,:updated)',item)
    return item['id']

def call(core,text):
    """Ring Zack and open with `text` in the Jarvis voice; he can reply and keep talking."""
    settings=config(core.DATA)
    if not settings:raise core.Problem('Phone calls are not set up yet.',503)
    opening=play_or_say(core,settings['public_url'].rstrip('/'),text)
    key=uuid.uuid4().hex
    with LOCK:CALLS[key]={'conversation':new_conversation(core,'Phone call'),'empty':0,'opening':opening}
    body=urlencode({'To':settings['my_number'],'From':settings['from_number'],'Timeout':'25',
      'Url':settings['public_url'].rstrip('/')+'/twilio/outbound?call='+key,'Method':'POST'}).encode()
    auth=base64.b64encode(f"{settings['account_sid']}:{settings['auth_token']}".encode()).decode()
    request=Request(f"https://api.twilio.com/2010-04-01/Accounts/{settings['account_sid']}/Calls.json",data=body,
      headers={'Authorization':'Basic '+auth,'Content-Type':'application/x-www-form-urlencoded'})
    with urlopen(request,timeout=15) as response:
        return {'call_sid':json.load(response).get('sid'),'status':'ringing'}

def gather(base,inner=''):
    return GATHER.format(action=base+'/twilio/heard',inner=inner)

class Bridge(BaseHTTPRequestHandler):
    core=None
    def log_message(self,*args):pass
    def reply(self,status,body,kind='text/xml'):
        data=body.encode() if isinstance(body,str) else body
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store');self.end_headers()
        try:self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError):pass

    def do_GET(self):
        match=re.fullmatch(r'/twilio/audio/([0-9a-f]{32})\.wav',urlparse(self.path).path)
        with LOCK:entry=AUDIO.get(match[1]) if match else None
        if not entry or entry[1]<time.time() or not entry[0].is_file():return self.reply(404,'Not found','text/plain')
        self.reply(200,entry[0].read_bytes(),'audio/wav')

    def do_POST(self):
        core=self.core;settings=config(core.DATA)
        if not settings:return self.reply(503,twiml(say('Phone access is not configured.')))
        try:size=int(self.headers.get('Content-Length','0'))
        except ValueError:size=-1
        if not 0<=size<=20000:return self.reply(400,'Bad request','text/plain')
        params={k:v[0] for k,v in parse_qs(self.rfile.read(size).decode(),keep_blank_values=True).items()}
        base=settings['public_url'].rstrip('/')
        if not valid(settings['auth_token'],base+self.path,params,self.headers.get('X-Twilio-Signature','')):
            return self.reply(403,'Forbidden','text/plain')
        path=urlparse(self.path).path;query=parse_qs(urlparse(self.path).query)
        sid=params.get('CallSid','')
        try:
            if path=='/twilio/voice':
                caller=params.get('From','') if params.get('Direction','inbound')=='inbound' else params.get('To','')
                if digits(caller)!=digits(settings['my_number']):return self.reply(200,twiml('<Reject reason="rejected"/>'))
                with LOCK:CALLS[sid]={'conversation':new_conversation(core,'Phone call'),'empty':0}
                return self.reply(200,twiml(gather(base,play_or_say(core,base,'Yes, sir?'))))
            if path=='/twilio/outbound':
                key=query.get('call',[''])[0]
                with LOCK:state=CALLS.pop(key,None)
                if not state or digits(params.get('To',''))!=digits(settings['my_number']):return self.reply(200,twiml('<Hangup/>'))
                with LOCK:CALLS[sid]=state
                return self.reply(200,twiml(gather(base,state.pop('opening',''))))
            with LOCK:state=CALLS.get(sid)
            if not state:return self.reply(200,twiml(say('This call has expired. Goodbye, sir.')+'<Hangup/>'))
            if path=='/twilio/heard':
                text=params.get('SpeechResult','').strip()
                if not text:
                    state['empty']+=1
                    if state['empty']>=3:return self.reply(200,twiml(play_or_say(core,base,'I shall leave you to it, sir.')+'<Hangup/>'))
                    return self.reply(200,twiml(gather(base,play_or_say(core,base,'I didn\'t catch that, sir.'))))
                state['empty']=0
                if re.fullmatch(r'\W*(bye|goodbye|that\'?s all|hang up|thanks,? bye|thank you,? bye)\W*',text,re.I):
                    return self.reply(200,twiml(play_or_say(core,base,'Very good, sir.')+'<Hangup/>'))
                try:item=core.create_turn(state['conversation'],text=text[:4000])
                except core.Problem:
                    return self.reply(200,twiml(say('I am busy with another reply. Please try again in a moment.')+gather(base)))
                return self.reply(200,twiml(f'<Pause length="1"/><Redirect method="POST">{base}/twilio/wait?turn={item["id"]}&amp;n=0</Redirect>'))
            if path=='/twilio/wait':
                tid=query.get('turn',[''])[0];count=int(query.get('n',['0'])[0])
                if not re.fullmatch(r'[0-9a-f]{32}',tid):return self.reply(400,'Bad request','text/plain')
                item=core.turn(tid)
                if item['conversation_id']!=state['conversation']:return self.reply(403,'Forbidden','text/plain')
                if item['status']=='complete' and item['has_audio']:
                    audio=phone_audio(core,core.DATA/'turns'/tid/'reply.wav')
                    return self.reply(200,twiml(gather(base,f'<Play>{base}/twilio/audio/{audio_token(audio)}.wav</Play>')))
                if item['status'] in {'failed','cancelled','interrupted','unheard'} or count>=WAIT_LIMIT:
                    message=item.get('output_text') or 'I could not finish that one, sir. Please try again.'
                    return self.reply(200,twiml(gather(base,say(message[:600]))))
                # A few seconds in, reassure the caller once instead of leaving dead air.
                hold=play_or_say(core,base,'One moment, sir.') if count==3 else '<Pause length="1"/>'
                return self.reply(200,twiml(f'{hold}<Redirect method="POST">{base}/twilio/wait?turn={tid}&amp;n={count+1}</Redirect>'))
        except Exception:
            return self.reply(200,twiml(say('Something went wrong on my end, sir.')+gather(base)))
        return self.reply(404,'Not found','text/plain')

def start(core):
    if not ready(core.DATA):return None
    Bridge.core=core
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Bridge)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    return server
