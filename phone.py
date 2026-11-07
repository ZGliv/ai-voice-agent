"""Phone calls with JARVIS through Twilio Media Streams.

A separate loopback server (VOICE_PHONE_PORT, default 4324) exposes only /twilio/*. It is
published with Tailscale Funnel; the main companion stays private. The one webhook must
carry a valid X-Twilio-Signature and only Zack's own number may call in. The call audio
then flows both ways over a WebSocket: Deepgram Flux (built for phone audio; key in
DATA/deepgram-api-key) hears Zack and decides when he has finished, with the local Kyutai
model as the fallback, the companion answers as a normal turn, and the Fish reply is streamed back
while it is still being generated. Each media stream must present a one-time token that
was only ever handed to Twilio. Config: DATA/twilio.json
  {"account_sid","auth_token","from_number","my_number","public_url"}
The same bridge accepts Stripe webhooks at /stripe/webhook (signed with DATA/stripe-webhook-secret)
so a new Parl.ai sale rings Zack.
"""
import base64, hashlib, hmac, json, os, queue, re, secrets, sys, threading, time, traceback, uuid, wave
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape, quoteattr
import fish_voice
import phone_media
from phone_media import Closed, Downsampler, Socket, Upsampler, accept_key

PORT=int(os.environ.get('VOICE_PHONE_PORT','4324'))
PENDING={}    # one-time stream token -> {'conversation','opening','expires'}
LIVE={}       # conversation id -> Call
LOCK=threading.Lock()
GOODBYE=re.compile(r"\W*(?:(?:ok(?:ay)?,? )?(?:good)?bye(?: now)?|that'?s all|hang up|(?:thanks|thank you),? (?:good)?bye)(?:,? jarvis)?\W*",re.I)
LINES=['Yes, sir?','Bear with me. I am still waking up.','Bear with me.','Very good, sir.','I shall leave you to it.','I could not finish that one. Please try again.']
HOLD_AFTER=7.0   # only a genuinely slow reply earns "Bear with me."
IDLE_LIMIT=60    # seconds of nobody talking before Jarvis hangs up
CHUNK=3840       # 80 ms of 24 kHz PCM16 per recognition step (one Kyutai frame)
FLUX='wss://api.deepgram.com/v2/listen'
FLUX_CHUNK=640   # 80 ms of 8 kHz mu-law, Deepgram's recommended frame
# Said on a live call while a lookup works, so a long search is never dead air.
PROGRESS={'gmail':'Going through your inbox now.','notion':'Checking your Notion.','calendar':'Looking at your calendar.',
  'drive':'Searching your Drive.','supabase':'Checking the database.','vercel':'Checking Vercel.','web':'Having a look online.'}
PROGRESS_GAP=5.0 # seconds of Jarvis silence before a progress line is worth saying
WAKING=(8,22)    # proactive calls only ring between these hours; otherwise Telegram
SEEN_EVENTS=set()

def log(*parts):
    # Goes to the service's error log; never includes audio, tokens or secrets.
    print(time.strftime('%H:%M:%S'),'phone:',*parts,file=sys.stderr,flush=True)

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

def cached(core,text):
    """The pre-rendered clip for a fixed line, or None if it has not been made yet."""
    path=core.DATA/'phone'/(hashlib.sha256((fish_voice.MODEL+text).encode()).hexdigest()[:24]+'.wav')
    return path if fish_voice.key(core.DATA) and path.is_file() else None

def warm(core,lines):
    # Fixed lines are synthesized once so they play instantly later.
    for line in lines:
        try:spoken(core,line)
        except Exception:pass

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

def hearing_key(data):
    if os.environ.get('DEEPGRAM_API_KEY'):return os.environ['DEEPGRAM_API_KEY'].strip()
    try:return (data/'deepgram-api-key').read_text().strip() or None
    except OSError:return None

def awake_hours(now=None):
    return WAKING[0]<=(now or datetime.now()).hour<WAKING[1]

def progress(core,conversation,tool):
    """A lookup from this call used `tool`; say what Jarvis is doing if he has been quiet a while."""
    with LOCK:live=LIVE.get(conversation)
    name=tool.lower()
    line=next((text for key,text in PROGRESS.items() if key in name),None)
    if live and line:live.update(line)

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
        self.last_spoke=time.monotonic();self.said=set()

    # Outgoing audio
    def send_pcm(self,pcm,downsampler):
        payload=downsampler.process(pcm);self.sending=True
        for start in range(0,len(payload),3200):
            self.socket.send({'event':'media','streamSid':self.stream,'media':{'payload':base64.b64encode(payload[start:start+3200]).decode()}})
    def mark(self):
        with self.lock:self.marks+=1;name=str(self.marks)
        self.socket.send({'event':'mark','streamSid':self.stream,'mark':{'name':name}})
        self.sending=False;self.last_spoke=time.monotonic()
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
                if generation==self.generation:self.say_line('I could not finish that one. Please try again.',generation)
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
                held=True;self.say_line('Bear with me.',generation)
            time.sleep(.04)
        if generation==self.generation:self.mark()

    def answer(self,text):
        core=self.core
        if GOODBYE.fullmatch(text):
            self.say_line('Very good, sir.');self.hang_up(after_playback=True);return
        with self.lock:self.generation+=1;generation=self.generation;self.said.clear()
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

    def update(self,line):
        # Progress lines are optional: never repeat one, never talk over anything, never crowd the last line.
        if line in self.said or self.busy or self.speaking() or not self.lines.empty():return
        if time.monotonic()-self.last_spoke<PROGRESS_GAP:return
        self.said.add(line);self.lines.put(line)

    def speak_text(self,text):
        """Speak an arbitrary line (e.g. a finished task) streamed straight from Fish."""
        secret=fish_voice.key(self.core.DATA)
        if not secret:return
        downsampler=Downsampler();folder=self.core.DATA/'phone';folder.mkdir(mode=0o700,exist_ok=True)
        target=folder/('line-'+uuid.uuid4().hex+'.wav')
        try:fish_voice.synthesize(text,target,secret,threading.Event(),on_chunk=lambda pcm:self.send_pcm(pcm,downsampler))
        finally:target.unlink(missing_ok=True)
        self.mark()

    def waiting(self):
        # A task Zack asked for on this call is still running; stay on the line for its answer.
        with self.core.connect() as db:
            return bool(db.execute("SELECT 1 FROM codex_jobs j JOIN turns t ON t.id=j.source_turn_id WHERE t.conversation_id=? AND j.status IN ('preparing','running') LIMIT 1",(self.conversation,)).fetchone())

    def worker(self):
        """Answers and announcements, one at a time, so replies never overlap."""
        while not self.done.is_set():
            try:kind,value=self.pending.get(timeout=.1)
            except queue.Empty:
                if not self.busy and not self.speaking():
                    try:text=self.lines.get_nowait()
                    except queue.Empty:
                        if time.monotonic()-self.heard>IDLE_LIMIT*(3 if self.waiting() else 1):
                            self.say_line('I shall leave you to it.');self.hang_up(after_playback=True)
                        continue
                    self.busy=True
                    try:
                        clip=cached(self.core,text)
                        if clip:self.play_wav(clip)
                        else:self.speak_text(text)
                    except Exception:pass
                    finally:self.busy=False;self.heard=time.monotonic()
                continue
            self.busy=True
            try:self.answer(value)
            except Closed:return
            except Exception:
                log('answer failed\n'+traceback.format_exc())
                try:self.say_line('Something went wrong on my end, sir.')
                except Exception:pass
            finally:self.busy=False;self.heard=time.monotonic()

    # Listening
    def heard_words(self,text,last):
        """Partial transcript bookkeeping shared by both recognizers; returns the new `last`."""
        if text and text!=last:
            self.heard=time.monotonic()
            # Zack talking over Jarvis stops the reply, like a person would.
            if self.speaking() and len(text.split())>=2:self.interrupt()
        return text or last

    def listen(self):
        secret=hearing_key(self.core.DATA)
        if secret:
            try:
                if self.listen_flux(secret):return
            except Exception as error:log('deepgram failed, using local recognition:',type(error).__name__,str(error)[:120])
        self.listen_local()

    def listen_flux(self,secret):
        """Deepgram Flux: phone-band audio in as-is, its own end-of-turn decision out. False = fall back."""
        query=urlencode({'model':'flux-general-en','encoding':'mulaw','sample_rate':'8000','eot_threshold':'0.7','eot_timeout_ms':'4000'})
        ws=phone_media.connect(FLUX+'?'+query,{'Authorization':'Token '+secret})
        log('listening with deepgram')
        failed=threading.Event()
        def read():
            last=''
            try:
                while not self.done.is_set():
                    message=ws.receive()
                    if message.get('type')=='Error':log('deepgram error:',str(message.get('description') or message)[:160]);break
                    event=message.get('event')
                    if not event:continue
                    text=(message.get('transcript') or '').strip()
                    if event=='EndOfTurn':
                        last=''
                        if text:
                            log('heard',len(text.split()),'words via deepgram')
                            self.pending.put(('answer',text))
                    else:last=self.heard_words(text,last)
            except Closed:pass
            except Exception:log('deepgram reader failed\n'+traceback.format_exc())
            if not self.done.is_set():failed.set()
        reader=threading.Thread(target=read,daemon=True);reader.start()
        buffer=b''
        try:
            while not self.done.is_set() and not failed.is_set():
                try:buffer+=self.audio.get(timeout=.2)
                except queue.Empty:continue
                while len(buffer)>=FLUX_CHUNK:
                    ws.send_bytes(buffer[:FLUX_CHUNK]);buffer=buffer[FLUX_CHUNK:]
        except Closed:failed.set()
        finally:
            try:ws.send({'type':'CloseStream'})
            except Closed:pass
            ws.close()
        if failed.is_set() and not self.done.is_set():
            log('deepgram stream dropped mid-call; switching to local recognition')
            return False
        return True

    def listen_local(self):
        recognizer=self.core.STREAMING.worker;stop=threading.Event();upsampler=Upsampler()
        session=uuid.uuid4().hex;buffer=b'';samples=0;last=''
        while not self.done.is_set():
            try:buffer+=upsampler.process(self.audio.get(timeout=.2))
            except queue.Empty:continue
            if len(buffer)<CHUNK:continue
            pcm,buffer=buffer[:CHUNK],buffer[CHUNK:]
            try:result=recognizer.call({'session':session,'pcm':base64.b64encode(pcm).decode()},stop,10)
            except Exception as error:result={'error':True};log('recognition failed:',type(error).__name__)
            samples+=CHUNK//2
            if result.get('error') or samples>24000*55:
                session=uuid.uuid4().hex;samples=0;last='';continue
            text=(result.get('text') or '').strip()
            last=self.heard_words(text,last)
            if result.get('end') and text:
                log('heard',len(text.split()),'words; backlog',self.audio.qsize())
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
            if not hearing_key(self.core.DATA) and not self.core.STREAMING.ready:
                # Right after a restart the recognition model is still loading.
                log('recognition still loading')
                self.say_line('Bear with me. I am still waking up.')
            while not self.done.is_set():
                message=self.socket.receive()
                event=message.get('event')
                if event=='media':
                    # Raw 8 kHz mu-law; each recognizer converts what it needs.
                    try:self.audio.put_nowait(base64.b64decode(message['media']['payload']))
                    except queue.Full:pass
                elif event=='mark':
                    try:self.played=max(self.played,int(message['mark']['name']))
                    except (KeyError,ValueError):pass
                elif event=='stop':log('caller hung up');break
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
        log('GET',urlparse(self.path).path,'upgrade=',self.headers.get('Upgrade'),'key=',bool(self.headers.get('Sec-WebSocket-Key')))
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
            if not state or state['expires']<time.time():log('stream refused: unknown or expired token');return socket.close()
            log('stream started',message.get('streamSid'))
            self.connection.settimeout(30)
            Call(self.core,socket,message.get('streamSid') or message['start'].get('streamSid'),state['conversation']).run(state['opening'])
        except Closed:log('stream closed')
        except Exception:log('stream failed\n'+traceback.format_exc())
        finally:socket.close()

    def do_POST(self):
        core=self.core
        if urlparse(self.path).path=='/stripe/webhook':return self.stripe()
        settings=config(core.DATA)
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

    def stripe(self):
        secret=stripe_secret(self.core.DATA)
        try:size=int(self.headers.get('Content-Length','0'))
        except ValueError:size=-1
        if not secret:return self.reply(404,'Not found','text/plain')
        if not 0<=size<=512000:return self.reply(400,'Bad request','text/plain')
        body=self.rfile.read(size)
        if not stripe_valid(secret,body,self.headers.get('Stripe-Signature','')):return self.reply(400,'Bad signature','text/plain')
        try:event=json.loads(body)
        except ValueError:return self.reply(400,'Bad request','text/plain')
        self.reply(200,'{"received":true}','application/json')
        threading.Thread(target=stripe_event,args=(self.core,event),daemon=True).start()

def stripe_secret(data):
    try:return (data/'stripe-webhook-secret').read_text().strip() or None
    except OSError:return None

def stripe_valid(secret,body,header,now=None,tolerance=300):
    """Stripe's scheme: HMAC-SHA256 of "<t>.<raw body>", any v1 entry may match, timestamp within 5 minutes."""
    fields=[part.split('=',1) for part in header.split(',') if '=' in part]
    stamps=[v for k,v in fields if k.strip()=='t'];given=[v for k,v in fields if k.strip()=='v1']
    if not stamps or not given or not stamps[0].isdigit():return False
    if abs((now or time.time())-int(stamps[0]))>tolerance:return False
    expected=hmac.new(secret.encode(),stamps[0].encode()+b'.'+body,hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected,v) for v in given)

def money(cents,currency):
    amount=(cents or 0)/100
    symbol={'usd':'$','gbp':'£','eur':'€'}.get((currency or '').lower())
    text=(f'{amount:,.0f}' if amount==int(amount) else f'{amount:,.2f}')
    return symbol+text if symbol else text+' '+(currency or '').upper()

def stripe_message(event):
    """(spoken line, ring?) for the Stripe events Zack cares about, else None."""
    kind=event.get('type');item=(event.get('data') or {}).get('object') or {}
    test='' if event.get('livemode',True) else 'Test mode: '
    if kind=='checkout.session.completed' and item.get('payment_status') in {'paid','no_payment_required'}:
        what='a new subscription' if item.get('mode')=='subscription' else 'a payment'
        return test+f'Good news. {what[0].upper()+what[1:]} just came through on Parl.ai, {money(item.get("amount_total"),item.get("currency"))}.',True
    if kind=='customer.subscription.deleted':
        return test+'A Parl.ai subscription was just cancelled.',False
    if kind=='invoice.payment_failed':
        return test+f'A Parl.ai renewal payment of {money(item.get("amount_due"),item.get("currency"))} just failed.',False
    return None

def stripe_event(core,event):
    import notify
    with LOCK:
        if event.get('id') in SEEN_EVENTS:return
        SEEN_EVENTS.add(event.get('id'))
    found=stripe_message(event)
    if not found:return
    text,ring=found
    log('stripe event',event.get('type'))
    if ring and ready(core.DATA) and awake_hours():
        try:deliver(core,text);return
        except Exception:log('stripe call failed\n'+traceback.format_exc())
    try:notify.send(core,'Parl.ai · '+text)
    except Exception:pass

def start(core):
    if not ready(core.DATA):return None
    Bridge.core=core
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Bridge)
    threading.Thread(target=warm,args=(core,LINES+list(PROGRESS.values())),daemon=True).start()
    threading.Thread(target=server.serve_forever,daemon=True).start()
    return server
