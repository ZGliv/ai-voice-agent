"""Explicitly free-only Fish speech; credentials stay in the private data folder."""
import json, os, queue, threading, time, subprocess, wave
from urllib.request import Request, urlopen
from urllib.error import HTTPError
MODEL='s2.1-pro-free'
VOICE='612b878b113047d9a770c069c8b4fdfe'
class VoiceError(Exception): pass

def key(data):
    path=data/'fish-api-key'
    try:return path.read_text().strip()
    except FileNotFoundError:return ''

def status(data):
    return {'connected':bool(key(data)),'model':MODEL,'voice':'Jarvis (MCU)','sample':(data/'fish-sample.wav').is_file()}

def synthesize(text,destination,secret,stop,on_chunk=None):
    if on_chunk is not None:return synthesize_stream(text,destination,secret,stop,on_chunk)
    if stop.is_set():raise InterruptedError()
    events=queue.Queue(maxsize=1)
    def request():
        try:
            body=json.dumps({'text':text,'reference_id':VOICE,'format':'mp3','latency':'balanced'}).encode()
            req=Request('https://api.fish.audio/v1/tts',data=body,headers={'Authorization':'Bearer '+secret,'Content-Type':'application/json','model':MODEL})
            with urlopen(req,timeout=45) as response:
                audio=response.read(8*1024*1024+1)
            if not audio or len(audio)>8*1024*1024:raise VoiceError('Fish returned an empty or oversized recording.')
            events.put(audio)
        except HTTPError as error:
            code=error.code;error.close()
            events.put(VoiceError({401:'Fish rejected the API key. Check the key in Settings.',403:'Fish denied access to this voice or model.',402:'Fish requested payment. No paid model was used; check free-model access.',429:'Fish is busy or rate limited. Wait a moment and retry.'}.get(code,'Fish speech is unavailable. Your text reply is saved; retry later.')))
        except Exception:events.put(VoiceError('Could not reach Fish Audio. Your text reply is saved; check your connection and retry.'))
    threading.Thread(target=request,daemon=True).start()
    deadline=time.monotonic()+50
    while True:
        if stop.is_set():raise InterruptedError()
        if time.monotonic()>deadline:raise VoiceError('Fish speech timed out. No paid fallback was used; retry later.')
        try:result=events.get(timeout=.1);break
        except queue.Empty:pass
    if isinstance(result,Exception):raise result
    if stop.is_set():raise InterruptedError()
    try:
        subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y','-i','pipe:0','-ac','1','-ar','24000','-c:a','pcm_s16le',str(destination)],input=result,capture_output=True,timeout=15,check=True)
        with wave.open(str(destination),'rb') as audio:
            if audio.getnframes()<2400:raise ValueError()
    except Exception:
        destination.unlink(missing_ok=True)
        raise VoiceError('Fish returned unreadable audio. Your text reply is saved.') from None
    if stop.is_set():destination.unlink(missing_ok=True);raise InterruptedError()

def synthesize_stream(text,destination,secret,stop,on_chunk):
    """Stream unchanged free-model voice as PCM; commit a normal WAV for history."""
    if stop.is_set():raise InterruptedError()
    events=queue.Queue(maxsize=16);abandoned=threading.Event()
    def publish(value):
        while not abandoned.is_set():
            try:events.put(value,timeout=.1);return
            except queue.Full:pass
    def request():
        try:
            body=json.dumps({'text':text,'reference_id':VOICE,'format':'pcm','sample_rate':24000,'latency':'balanced'}).encode()
            req=Request('https://api.fish.audio/v1/tts',data=body,headers={'Authorization':'Bearer '+secret,'Content-Type':'application/json','model':MODEL})
            with urlopen(req,timeout=45) as response:
                while not abandoned.is_set():
                    chunk=response.read1(4096)
                    if not chunk:break
                    publish(chunk)
            publish(None)
        except HTTPError as error:
            code=error.code;error.close()
            publish(VoiceError({401:'Fish rejected the API key. Check the key in Settings.',403:'Fish denied access to this voice or model.',402:'Fish requested payment. No paid model was used; check free-model access.',429:'Fish is busy or rate limited. Wait a moment and retry.'}.get(code,'Fish speech is unavailable. Your text reply is saved; retry later.')))
        except Exception:publish(VoiceError('Fish audio streaming was interrupted. Your text reply is saved; retry later.'))
    threading.Thread(target=request,daemon=True).start()
    deadline=time.monotonic()+90;total=0;tail=b''
    try:
        with wave.open(str(destination),'wb') as output:
            output.setparams((1,2,24000,0,'NONE','not compressed'))
            while True:
                if stop.is_set():raise InterruptedError()
                if time.monotonic()>deadline:raise VoiceError('Fish speech timed out. No paid fallback was used.')
                try:chunk=events.get(timeout=.05)
                except queue.Empty:continue
                if isinstance(chunk,Exception):raise chunk
                if chunk is None:break
                chunk=tail+chunk;tail=chunk[len(chunk)//2*2:];chunk=chunk[:len(chunk)//2*2]
                total+=len(chunk)
                if total>8*1024*1024:raise VoiceError('Fish returned oversized audio.')
                if chunk:output.writeframesraw(chunk);on_chunk(chunk)
            if tail or total<4800:raise VoiceError('Fish returned incomplete audio. Your text reply is saved.')
    except BaseException:
        destination.unlink(missing_ok=True);raise
    finally:abandoned.set()

def connect(data,secret):
    if not isinstance(secret,str) or not 16<=len(secret.strip())<=512 or any(c.isspace() for c in secret.strip()):
        raise VoiceError('Paste a valid Fish API key.')
    secret=secret.strip()
    pending=data/'fish-sample.pending.wav'
    try:
        synthesize('Good evening, Zack. Systems are ready. What shall we build next?',pending,secret,threading.Event())
        temporary=data/'fish-api-key.pending'
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as file:file.write(secret)
        os.chmod(temporary,0o600)
        temporary.replace(data/'fish-api-key')
        pending.replace(data/'fish-sample.wav')
    finally:pending.unlink(missing_ok=True)
    return status(data)

LOCK=threading.Lock()
def dispatch(handler,method,path,core):
    if path=='/api/voice/sample' and method=='GET':
        sample=core.DATA/'fish-sample.wav'
        if not sample.is_file():raise core.Problem('Connect Fish voice first.',404)
        handler.send(200,sample.read_bytes(),'audio/wav');return True
    if path!='/api/voice':return False
    if method=='GET':handler.send(200,status(core.DATA));return True
    if method not in {'POST','DELETE'}:return False
    if not LOCK.acquire(blocking=False):raise core.Problem('A voice connection is already being checked.',409)
    try:
        with core.GATE:
            if core.CURRENT:raise core.Problem('Wait for the current reply before changing voices.',409)
            if method=='DELETE':
                (core.DATA/'fish-api-key').unlink(missing_ok=True)
                (core.DATA/'fish-sample.wav').unlink(missing_ok=True)
                result=status(core.DATA)
            else:
                body=json.loads(handler.body())
                try:result=connect(core.DATA,body.get('api_key'))
                except VoiceError as error:raise core.Problem(str(error),400) from None
            core.HEALTH_CACHE=(0,None)
        handler.send(200,result);return True
    finally:LOCK.release()
