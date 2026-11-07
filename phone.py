"""Phone calls with JARVIS through Twilio Media Streams.

A separate loopback server (VOICE_PHONE_PORT, default 4324) exposes only /twilio/*. It is
published with Tailscale Funnel; the main companion stays private. The one webhook must
carry a valid X-Twilio-Signature and only Zack's own number may call in. The call audio
then flows both ways over a WebSocket: Kyutai hears Zack live and decides when he has
finished, the companion answers as a normal turn, and the Fish reply is streamed back
while it is still being generated. Each media stream must present a one-time token that
was only ever handed to Twilio. Config: DATA/twilio.json
  {"account_sid","auth_token","from_number","my_number","public_url"}
"""
import base64, hashlib, hmac, json, os, queue, re, secrets, threading, time, uuid, wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape, quoteattr
import fish_voice
from phone_media import Closed, Downsampler, Socket, Upsampler, accept_key

PORT=int(os.environ.get('VOICE_PHONE_PORT','4324'))
PENDING={}    # one-time stream token -> {'conversation','opening','expires'}
LIVE={}       # conversation id -> Call
LOCK=threading.Lock()
GOODBYE=re.compile(r"\W*(?:(?:ok(?:ay)?,? )?(?:good)?bye(?: now)?|that'?s all|hang up|(?:thanks|thank you),? (?:good)?bye)(?:,? jarvis)?\W*",re.I)
LINES=['Yes, sir?','One moment, sir.','Very good, sir.','I shall leave you to it, sir.','I could not finish that one, sir. Please try again.']
HOLD_AFTER=3.0   # seconds after Zack stops talking before "One moment, sir."
IDLE_LIMIT=60    # seconds of nobody talking before Jarvis hangs up
CHUNK=7680       # 160 ms of 24 kHz PCM16 per recognition step

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

def spoken(core,text):
    """A fixed line in the Jarvis voice as cached 24 kHz WAV, or None without Fish."""
    secret=fish_voice.key(core.DATA)
    if not secret:return None
    folder=core.DATA/'phone';folder.mkdir(mode=0o700,exist_ok=True)
    path=folder/(hashlib.sha256((fish_voice.MODEL+text).encode()).hexdigest()[:24]+'.wav')
    if not path.is_file():
        pending=path.with_suffix('.pending.wav')
        fish_voice.synthesize(text,pending,secret,threading.Event())
        pending.replace(path)
    return path

def new_conversation(core,title,opening=None):
    now=time.time();cid=uuid.uuid4().hex
    with core.connect() as db:
        db.execute('INSERT INTO conversations VALUES(?,?,?,?)',(cid,title,now,now))
    if opening:remember(core,cid,opening)
    return cid

def remember(core,conversation,opening):
    # Record what Jarvis opened the call with, so "yes, go ahead" has something to refer to.
    now=time.time()
    with core.connect() as db:
        db.execute("INSERT INTO turns(id,conversation_id,source,status,input_text,output_text,created,updated) VALUES(?,?,'phone','complete',?,?,?,?)",
          (uuid.uuid4().hex,conversation,'(Jarvis phoned Zack.)',opening,now,now))

def stream_twiml(core,settings,conversation,opening=None):
    try:audio=spoken(core,opening) if opening else None
    except Exception:audio=None
    token=secrets.token_hex(16)
    with LOCK:
        now=time.time()
        for key in [k for k,v in PENDING.items() if v['expires']<now]:PENDING.pop(key,None)
        PENDING[token]={'conversation':conversation,'opening':audio,'expires':now+120}
    url='wss://'+urlparse(settings['public_url']).netloc+'/twilio/media'
    before=say(opening) if opening and not audio else ''
    return twiml(before+f'<Connect><Stream url={quoteattr(url)}><Parameter name="token" value="{token}"/></Stream></Connect>')

def call(core,text,conversation=None):
    """Ring Zack and open with `text` in the Jarvis voice; he can reply and keep talking."""
    settings=config(core.DATA)
    if not settings:raise core.Problem('Phone calls are not set up yet.',503)
    if conversation:remember(core,conversation,text)
    else:conversation=new_conversation(core,'Phone call',text)
    body=urlencode({'To':settings['my_number'],'From':settings['from_number'],'Timeout':'25',
      'Twiml':stream_twiml(core,settings,conversation,text)}).encode()
    auth=base64.b64encode(f"{settings['account_sid']}:{settings['auth_token']}".encode()).decode()
    request=Request(f"https://api.twilio.com/2010-04-01/Accounts/{settings['account_sid']}/Calls.json",data=body,
      headers={'Authorization':'Basic '+auth,'Content-Type':'application/x-www-form-urlencoded'})
    with urlopen(request,timeout=15) as response:
        return {'call_sid':json.load(response).get('sid'),'status':'ringing'}

def deliver(core,text,conversation=None):
    """Say `text` on the call in progress, or ring Zack with it."""
    with LOCK:live=LIVE.get(conversation) or next(iter(LIVE.values()),None)
    if live:live.announce(text);return 'spoken'
    call(core,text,conversation);return 'called'

def is_phone_conversation(core,conversation):
    with core.connect() as db:
        row=db.execute('SELECT title FROM conversations WHERE id=?',(conversation,)).fetchone()
    return bool(row) and row[0].startswith('Phone call')

class Call:
    """One live media stream: listen with Kyutai, answer as companion turns, stream the voice back."""
    def __init__(self,core,socket,stream,conversation):
        self.core=core;self.socket=socket;self.stream=stream;self.conversation=conversation
        self.audio=queue.Queue(maxsize=400);self.lines=queue.Queue();self.pending=queue.Queue()
        self.generation=0;self.marks=0;self.played=0;self.sending=False;self.turn=None;self.busy=False
        self.heard=time.monotonic();self.done=threading.Event();self.lock=threading.Lock()

    # Outgoing audio
    def send_pcm(self,pcm,downsampler):
        payload=downsampler.process(pcm);self.sending=True
        for start in range(0,len(payload),3200):
            self.socket.send({'event':'media','streamSid':self.stream,'media':{'payload':base64.b64encode(payload[start:start+3200]).decode()}})
    def mark(self):
        with self.lock:self.marks+=1;name=str(self.marks)
        self.socket.send({'event':'mark','streamSid':self.stream,'mark':{'name':name}})
        self.sending=False
    def speaking(self):
        # Audio is still being sent, or Twilio has not yet played up to our last mark.
        return self.sending or self.played<self.marks
    def play_wav(self,path,generation=None):
        downsampler=Downsampler()
        with wave.open(str(path),'rb') as audio:
            while chunk:=audio.readframes(4800):
                if generation is not None and generation!=self.generation:return
                self.send_pcm(chunk,downsampler)
        self.mark()
    def say_line(self,text,generation=None):
        path=spoken(self.core,text)
        if path:self.play_wav(path,generation)
    def interrupt(self):
        with self.lock:self.generation+=1;turn=self.turn
        self.socket.send({'event':'clear','streamSid':self.stream})
        self.played=self.marks;self.sending=False
        core=self.core
        if turn and core.CURRENT==turn:core.STOP.set()

    # Answering
    def follow(self,tid,generation):
        """Stream a companion turn's reply as it is synthesized (reply.pcm, then reply.wav)."""
        core=self.core;directory=core.DATA/'turns'/tid;offset=0;started=time.monotonic();held=False
        downsampler=Downsampler();deadline=started+120
        while time.monotonic()<deadline and generation==self.generation:
            item=core.turn(tid)
            if item['status'] in {'failed','cancelled','interrupted','unheard'}:
                if generation==self.generation:self.say_line('I could not finish that one, sir. Please try again.',generation)
                return
            path=directory/('reply.wav' if item['status']=='complete' else 'reply.pcm')
            chunk=b''
            try:
                if item['status']=='complete':
                    with wave.open(str(path),'rb') as audio:audio.setpos(offset//2);chunk=audio.readframes(12000)
                else:
                    with path.open('rb') as audio:audio.seek(offset);chunk=audio.read(24000)
            except (FileNotFoundError,wave.Error,EOFError):pass
            if chunk:
                offset+=len(chunk);self.send_pcm(chunk,downsampler);continue
            if item['status']=='complete':break
            if not held and not offset and time.monotonic()-started>HOLD_AFTER:
                held=True;self.say_line('One moment, sir.',generation)
            time.sleep(.04)
        if generation==self.generation:self.mark()

    def answer(self,text):
        core=self.core
        if GOODBYE.fullmatch(text):
            self.say_line('Very good, sir.');self.hang_up(after_playback=True);return
        with self.lock:self.generation+=1;generation=self.generation
        # A barge-in may still be cancelling the previous reply.
        for _ in range(100):
            if not core.CURRENT:break
            time.sleep(.05)
        try:item=core.create_turn(self.conversation,text=text[:4000])
        except core.Problem:
            self.say_line('I am still finishing something, sir. One moment.');return
        with self.lock:self.turn=item['id']
        try:self.follow(item['id'],generation)
        finally:
            with self.lock:
                if self.turn==item['id']:self.turn=None

    def announce(self,text):
        self.lines.put(text)

    def speak_text(self,text):
        """Speak an arbitrary line (e.g. a finished task) streamed straight from Fish."""
        secret=fish_voice.key(self.core.DATA)
        if not secret:return
        downsampler=Downsampler();folder=self.core.DATA/'phone';folder.mkdir(mode=0o700,exist_ok=True)
        target=folder/('line-'+uuid.uuid4().hex+'.wav')
        try:fish_voice.synthesize(text,target,secret,threading.Event(),on_chunk=lambda pcm:self.send_pcm(pcm,downsampler))
        finally:target.unlink(missing_ok=True)
        self.mark()

    def worker(self):
        """Answers and announcements, one at a time, so replies never overlap."""
        while not self.done.is_set():
            try:kind,value=self.pending.get(timeout=.1)
            except queue.Empty:
                if not self.busy and not self.speaking():
                    try:text=self.lines.get_nowait()
                    except queue.Empty:
                        if time.monotonic()-self.heard>IDLE_LIMIT:
                            self.say_line('I shall leave you to it, sir.');self.hang_up(after_playback=True)
                        continue
                    self.busy=True
                    try:self.speak_text(text)
                    except Exception:pass
                    finally:self.busy=False;self.heard=time.monotonic()
                continue
            self.busy=True
            try:self.answer(value)
            except Closed:return
            except Exception:
                try:self.say_line('Something went wrong on my end, sir.')
                except Exception:pass
            finally:self.busy=False;self.heard=time.monotonic()

    # Listening
    def listen(self):
        recognizer=self.core.STREAMING.worker;stop=threading.Event()
        session=uuid.uuid4().hex;buffer=b'';samples=0;last=''
        while not self.done.is_set():
            try:buffer+=self.audio.get(timeout=.2)
            except queue.Empty:continue
            if len(buffer)<CHUNK:continue
            pcm,buffer=buffer[:CHUNK],buffer[CHUNK:]
            try:result=recognizer.call({'session':session,'pcm':base64.b64encode(pcm).decode()},stop,10)
            except Exception:result={'error':True}
            samples+=CHUNK//2
            if result.get('error') or samples>24000*55:
                session=uuid.uuid4().hex;samples=0;last='';continue
            text=(result.get('text') or '').strip()
            if text and text!=last:
                last=text;self.heard=time.monotonic()
                # Zack talking over Jarvis stops the reply, like a person would.
                if self.speaking() and len(text.split())>=2:self.interrupt()
            if result.get('end') and text:
                session=uuid.uuid4().hex;samples=0;last=''
                self.pending.put(('answer',text))

    def hang_up(self,after_playback=False):
        deadline=time.monotonic()+15
        while after_playback and self.speaking() and time.monotonic()<deadline:time.sleep(.05)
        self.done.set();self.socket.close()

    def run(self,opening):
        with LOCK:LIVE[self.conversation]=self
        threads=[threading.Thread(target=self.listen,daemon=True),threading.Thread(target=self.worker,daemon=True)]
        for thread in threads:thread.start()
        try:
            if opening:self.play_wav(opening)
            upsampler=Upsampler()
            while not self.done.is_set():
                message=self.socket.receive()
                event=message.get('event')
                if event=='media':
                    try:self.audio.put_nowait(upsampler.process(base64.b64decode(message['media']['payload'])))
                    except queue.Full:pass
                elif event=='mark':
                    try:self.played=max(self.played,int(message['mark']['name']))
                    except (KeyError,ValueError):pass
                elif event=='stop':break
        except Closed:pass
        finally:
            self.done.set()
            with LOCK:
                if LIVE.get(self.conversation) is self:LIVE.pop(self.conversation,None)
            turn=self.turn
            if turn and self.core.CURRENT==turn:self.core.STOP.set()

class Bridge(BaseHTTPRequestHandler):
    core=None
    protocol_version='HTTP/1.1'  # WebSocket upgrades require it
    def log_message(self,*args):pass
    def reply(self,status,body,kind='text/xml'):
        data=body.encode() if isinstance(body,str) else body
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store');self.end_headers()
        try:self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError):pass

    def do_GET(self):
        if urlparse(self.path).path!='/twilio/media' or self.headers.get('Upgrade','').lower()!='websocket' or not self.headers.get('Sec-WebSocket-Key'):
            return self.reply(404,'Not found','text/plain')
        if not config(self.core.DATA):return self.reply(503,'Not configured','text/plain')
        self.send_response(101);self.send_header('Upgrade','websocket');self.send_header('Connection','Upgrade')
        self.send_header('Sec-WebSocket-Accept',accept_key(self.headers['Sec-WebSocket-Key']));self.end_headers()
        self.close_connection=True
        socket=Socket(self.rfile,self.wfile)
        try:
            self.connection.settimeout(10)
            while True:
                message=socket.receive()
                if message.get('event')=='start':break
            token=(message.get('start',{}).get('customParameters') or {}).get('token','')
            with LOCK:state=PENDING.pop(token,None)
            if not state or state['expires']<time.time():return socket.close()
            self.connection.settimeout(30)
            Call(self.core,socket,message.get('streamSid') or message['start'].get('streamSid'),state['conversation']).run(state['opening'])
        except (Closed,OSError,KeyError,ValueError):pass
        finally:socket.close()

    def do_POST(self):
        core=self.core;settings=config(core.DATA)
        if not settings:return self.reply(503,twiml(say('Phone access is not configured.')))
        try:size=int(self.headers.get('Content-Length','0'))
        except ValueError:size=-1
        if not 0<=size<=20000:return self.reply(400,'Bad request','text/plain')
        params={k:v[0] for k,v in parse_qs(self.rfile.read(size).decode(),keep_blank_values=True).items()}
        if not valid(settings['auth_token'],settings['public_url'].rstrip('/')+self.path,params,self.headers.get('X-Twilio-Signature','')):
            return self.reply(403,'Forbidden','text/plain')
        if urlparse(self.path).path!='/twilio/voice':return self.reply(404,'Not found','text/plain')
        if digits(params.get('From',''))!=digits(settings['my_number']):return self.reply(200,twiml('<Reject reason="rejected"/>'))
        try:return self.reply(200,stream_twiml(core,settings,new_conversation(core,'Phone call'),'Yes, sir?'))
        except Exception:return self.reply(200,twiml(say('Something went wrong on my end, sir.')))

def start(core):
    if not ready(core.DATA):return None
    Bridge.core=core
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Bridge)
    def warm():
        # Fixed lines are synthesized once so the first call has no extra pause.
        for line in LINES:
            try:spoken(core,line)
            except Exception:pass
    threading.Thread(target=warm,daemon=True).start()
    threading.Thread(target=server.serve_forever,daemon=True).start()
    return server
