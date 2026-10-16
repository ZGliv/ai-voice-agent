#!/usr/bin/env python3
"""Loopback-only voice companion. No microphone access, cloud calls or dummy model output."""
import json, mimetypes, os, re, shutil, signal, sqlite3, subprocess, threading, time, uuid, wave
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('VOICE_DATA_DIR', Path.home() / '.local/share/ai-voice-agent')).expanduser()
PORT = int(os.environ.get('VOICE_PORT', '4321'))
WHISPER = os.environ.get('VOICE_WHISPER', shutil.which('whisper') or 'whisper')
MODEL_DIR = Path(os.environ.get('VOICE_WHISPER_MODELS', Path.home() / '.cache/whisper')).expanduser()
MODEL = os.environ.get('VOICE_WHISPER_MODEL', 'base')
PIPER_PYTHON = os.environ.get('VOICE_PIPER_PYTHON', str(Path.home() / 'Developer/shortgen/.venv/bin/python'))
PIPER_MODEL = Path(os.environ.get('VOICE_PIPER_MODEL', Path.home() / 'Developer/shortgen/models/en/en_US/ljspeech/high/en_US-ljspeech-high.onnx')).expanduser()
OLLAMA = 'http://127.0.0.1:11434'  # Intentionally local; no remote/cloud fallback.
LLM = 'qwen3:8b'
MAX_BODY = 10 * 1024 * 1024
ACTIVE = {'queued', 'transcribing', 'thinking', 'synthesizing'}
GATE = threading.RLock()
CURRENT = None
STOP = threading.Event()
PROCESS = None

class Problem(Exception):
    def __init__(self, message, status=400): self.message, self.status = message, status
class Cancelled(Exception): pass

@contextmanager
def connect():
    db = sqlite3.connect(DATA / 'history.sqlite3', timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        with db:
            yield db
    finally:
        db.close()

def initialize():
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    (DATA / 'turns').mkdir(exist_ok=True, mode=0o700)
    with connect() as db:
        db.executescript('''PRAGMA journal_mode=WAL;
          CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,title TEXT NOT NULL,created REAL,updated REAL);
          CREATE TABLE IF NOT EXISTS turns(id TEXT PRIMARY KEY,conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
            source TEXT,status TEXT,input_text TEXT DEFAULT '',output_text TEXT DEFAULT '',error TEXT DEFAULT '',
            created REAL,updated REAL,timings TEXT DEFAULT '{}');''')
        db.execute("UPDATE turns SET status='interrupted',error='The companion stopped during this turn. Retry to continue.' WHERE status IN ('queued','transcribing','thinking','synthesizing')")
    os.chmod(DATA / 'history.sqlite3', 0o600)

def title_for(text):
    title=re.split(r'[.!?\n]',text,maxsplit=1)[0].strip() or 'Voice conversation'
    return title if len(title)<=64 else title[:64].rsplit(' ',1)[0]+'…'

def row_turn(row):
    if not row: raise Problem('That turn no longer exists.', 404)
    item = dict(row)
    item['timings'] = json.loads(item['timings'])
    item['has_audio'] = (DATA / 'turns' / item['id'] / 'reply.wav').is_file()
    return item

def turn(turn_id):
    with connect() as db: return row_turn(db.execute('SELECT * FROM turns WHERE id=?', (turn_id,)).fetchone())

def update(turn_id, **values):
    values['updated'] = time.time()
    with connect() as db:
        db.execute('UPDATE turns SET ' + ','.join(k+'=?' for k in values) + ' WHERE id=?', [*values.values(), turn_id])

def dependency_status():
    checks = {
        'transcription': bool(shutil.which(WHISPER) and (MODEL_DIR / (MODEL + '.pt')).is_file()),
        'audio': bool(shutil.which('ffmpeg') and shutil.which('ffprobe')),
        'speech': bool(Path(PIPER_PYTHON).is_file() and PIPER_MODEL.is_file() and Path(str(PIPER_MODEL)+'.json').is_file()),
        'reasoning': False,
    }
    try:
        with urlopen(OLLAMA + '/api/tags', timeout=2) as response:
            checks['reasoning'] = any(m['name'] == LLM for m in json.load(response)['models'])
    except Exception: pass
    return {'local': True, 'ready': all(checks.values()), 'checks': checks, 'active': CURRENT,
            'models': {'transcription': 'Whisper ' + MODEL, 'reasoning': LLM, 'speech': 'Piper · LJ Speech'},
            'storage': 'This computer · SQLite and local audio files', 'max_seconds': 60}

def run_process(args, timeout=180):
    global PROCESS
    if STOP.is_set(): raise Cancelled()
    with GATE:
        if STOP.is_set(): raise Cancelled()
        PROCESS = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        process = PROCESS
    started = time.monotonic()
    try:
        while True:
            try:
                stdout, stderr = process.communicate(timeout=.2)
                break
            except subprocess.TimeoutExpired:
                if STOP.is_set() or time.monotonic()-started > timeout:
                    os.killpg(process.pid, signal.SIGTERM)
                    try: process.communicate(timeout=2)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL); process.communicate()
                    if STOP.is_set(): raise Cancelled()
                    raise Problem('This step took too long. Retry, or send a shorter message.', 503)
        if STOP.is_set(): raise Cancelled()
        if process.returncode:
            # Tool stderr may contain transcripts/paths: never expose it to browser or logs.
            raise Problem('The local tool could not finish this step. Check the local setup and retry.', 503)
        return stdout
    finally:
        with GATE:
            if PROCESS is process: PROCESS = None

def work(turn_id):
    global CURRENT
    directory = DATA / 'turns' / turn_id
    item = turn(turn_id)
    timings = item['timings']
    stage = 'queued'
    try:
        if not item['input_text']:
            stage = 'transcribing'; update(turn_id, status=stage, error='')
            start = time.monotonic()
            if not shutil.which(WHISPER) or not (MODEL_DIR / (MODEL+'.pt')).is_file():
                raise Problem('Whisper is not installed or its cached model is missing. Text input still works.', 503)
            run_process(['ffmpeg','-nostdin','-v','error','-y','-protocol_whitelist','file,pipe','-format_whitelist','wav,mp3,mov,matroska,webm,ogg,flac,aac','-i',str(directory/'input.audio'),'-t','61.1','-ar','16000','-ac','1','-c:a','pcm_s16le',str(directory/'input.wav')], 20)
            with wave.open(str(directory/'input.wav'), 'rb') as audio:
                duration = audio.getnframes() / audio.getframerate()
                if not .25 <= duration <= 60.5: raise Problem('Use an audio clip between 1 and 60 seconds.')
                import array, math
                samples = array.array('h', audio.readframes(audio.getnframes()))
                rms = math.sqrt(sum(x*x for x in samples) / max(1,len(samples)))
                if rms < 35: raise Problem('No audible speech was found. Check your microphone, try another clip, or type instead.')
            run_process([WHISPER,str(directory/'input.wav'),'--model',str(MODEL_DIR/(MODEL+'.pt')),'--model_dir',str(MODEL_DIR),
                '--device','cpu','--fp16','False','--language','en','--threads','4','--output_format','json',
                '--output_dir',str(directory),'--verbose','False'], 180)
            result = json.loads((directory/'input.json').read_text())
            text = result.get('text','').strip()
            if not text or all(s.get('no_speech_prob',0) > .8 for s in result.get('segments',[]) or [{}]):
                raise Problem('No clear speech was transcribed. Try a clearer recording or type instead.')
            item['input_text'] = text[:4000]
            timings[stage] = round(time.monotonic()-start,2)
            update(turn_id, input_text=item['input_text'], timings=json.dumps(timings))
            with connect() as db:
                db.execute("UPDATE conversations SET title=? WHERE id=? AND title='Voice conversation'",(title_for(item['input_text']),item['conversation_id']))
            for name in ['input.wav','input.json']:
                (directory/name).unlink(missing_ok=True)
        if not item['output_text']:
            stage = 'thinking'; update(turn_id, status=stage, error='')
            start = time.monotonic()
            with connect() as db:
                history = db.execute("SELECT input_text,output_text FROM turns WHERE conversation_id=? AND created<? AND status='complete' ORDER BY created DESC LIMIT 8",(item['conversation_id'],item['created'])).fetchall()
            messages = [{'role':'system','content':'You are a thoughtful, concise local voice companion. Answer in plain spoken English, normally one to three short sentences. No Markdown. You can discuss and help think through ideas, but cannot browse, access files, perform actions, remember outside the provided conversation, or check current facts. Say so when relevant. Do not claim actions you cannot perform. Keep answers under 100 words.'}]
            for previous in reversed(history):
                messages.extend([{'role':'user','content':previous['input_text']},{'role':'assistant','content':previous['output_text']}])
            messages.append({'role':'user','content':item['input_text']})
            while sum(len(m['content']) for m in messages)>16000 and len(messages)>2:
                del messages[1:3]
            request_path = directory/'request.json'
            request_path.write_text(json.dumps({'model':LLM,'messages':messages,'think':False,'stream':False,'keep_alive':'5m',
                'options':{'num_predict':180,'num_ctx':8192,'temperature':.6}}))
            try:
                response = json.loads(run_process(['curl','--silent','--show-error','--fail','--max-time','180','-H','Content-Type: application/json','--data-binary','@'+str(request_path),OLLAMA+'/api/chat'],190))
            finally: request_path.unlink(missing_ok=True)
            text = response.get('message',{}).get('content','').strip()
            if not text: raise Problem('Ollama returned no answer. Confirm qwen3:8b is installed, then retry.',503)
            if response.get('done_reason') == 'length': text += ' [Response reached the length limit.]'
            item['output_text'] = text
            timings[stage] = round(time.monotonic()-start,2)
            update(turn_id, output_text=text, timings=json.dumps(timings))
        stage = 'synthesizing'; update(turn_id, status=stage, error='')
        start = time.monotonic()
        if not Path(PIPER_PYTHON).is_file() or not PIPER_MODEL.is_file():
            raise Problem('Piper speech is not installed. Your answer is saved as text; retry after restoring the local voice.',503)
        (directory/'reply.txt').write_text(item['output_text'])
        run_process([PIPER_PYTHON,str(ROOT/'synthesize.py'),str(PIPER_MODEL),str(directory/'reply.txt'),str(directory/'reply.pending.wav')],90)
        with wave.open(str(directory/'reply.pending.wav'),'rb') as audio:
            if audio.getnframes() < audio.getframerate()*.1: raise Problem('Speech synthesis returned an empty recording.',503)
            import array
            samples=array.array('h',audio.readframes(audio.getnframes()))
            if not samples or max(abs(x) for x in samples)<100: raise Problem('Speech synthesis returned silent audio. Your text answer is saved.',503)
        with GATE:
            if STOP.is_set(): raise Cancelled()
            (directory/'reply.pending.wav').replace(directory/'reply.wav')
            timings[stage] = round(time.monotonic()-start,2)
            update(turn_id, status='complete', error='', timings=json.dumps(timings))
        # Uploaded source is only retained while needed for retry, never indefinitely after success.
        (directory/'input.audio').unlink(missing_ok=True)
        (directory/'reply.txt').unlink(missing_ok=True)
    except Cancelled:
        update(turn_id, status='cancelled', error='Stopped. Your completed steps are saved; retry when you’re ready.')
    except Exception as error:
        message = error.message if isinstance(error,Problem) else 'The local '+stage+' step failed. Your completed steps are saved. Check setup, then retry.'
        update(turn_id, status='failed', error=message)
    finally:
        (directory/'reply.pending.wav').unlink(missing_ok=True)
        with GATE: CURRENT = None

def launch(turn_id):
    global CURRENT
    if CURRENT: raise Problem('Another turn is running. Wait for it or cancel it first.',409)
    STOP.clear(); CURRENT = turn_id
    threading.Thread(target=work,args=(turn_id,),daemon=True).start()

def create_turn(conversation_id, text=None, audio=None):
    with GATE:
        if CURRENT: raise Problem('Another turn is running. Wait for it or cancel it first.',409)
        with connect() as db:
            if db.execute('SELECT COUNT(*) FROM turns').fetchone()[0] >= 500:
                raise Problem('This local library has reached 500 turns. Export and delete an old conversation to make room.',409)
            if not db.execute('SELECT id FROM conversations WHERE id=?',(conversation_id,)).fetchone(): raise Problem('Choose a conversation first.',404)
            if sum(p.stat().st_size for p in (DATA/'turns').rglob('*') if p.is_file()) > 500*1024*1024:
                raise Problem('Local audio storage has reached 500 MB. Export transcripts and delete an old conversation.',409)
            turn_id = uuid.uuid4().hex
            directory = DATA/'turns'/turn_id; directory.mkdir(mode=0o700)
            if audio is not None: (directory/'input.audio').write_bytes(audio)
            now = time.time()
            db.execute('INSERT INTO turns(id,conversation_id,source,status,input_text,created,updated) VALUES(?,?,?,?,?,?,?)',
                       (turn_id,conversation_id,'audio' if audio is not None else 'text','queued',text or '',now,now))
            title = title_for(text or 'Voice conversation')
            db.execute("UPDATE conversations SET title=CASE WHEN title='New conversation' THEN ? ELSE title END,updated=? WHERE id=?",(title,now,conversation_id))
        launch(turn_id)
        return turn(turn_id)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def guard(self):
        if self.headers.get('Host') not in {f'127.0.0.1:{PORT}',f'localhost:{PORT}'}: raise Problem('Use the local companion address.',403)
        origin = self.headers.get('Origin')
        if origin and origin not in {f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'}: raise Problem('Cross-origin access is not allowed.',403)
        if self.headers.get('Sec-Fetch-Site') in {'cross-site','same-site'} and (self.path.startswith('/api/') or self.command!='GET'):
            raise Problem('Open the companion directly to use it.',403)
        if self.path.startswith('/api/') and not self.path.endswith('/audio') and self.headers.get('X-Voice-Client') != '1':
            raise Problem('Open the companion app to use this endpoint.',403)
    def send(self,status,body,kind='application/json'):
        if isinstance(body,(dict,list)): body=json.dumps(body).encode()
        if isinstance(body,str): body=body.encode()
        self.send_response(status)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cross-Origin-Resource-Policy','same-origin')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; media-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        try: self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError): pass
    def body(self):
        try: size=int(self.headers.get('Content-Length','0'))
        except ValueError: raise Problem('Invalid upload length.')
        if not 0 < size <= MAX_BODY: raise Problem('Upload an audio file smaller than 10 MB.',413)
        self.connection.settimeout(15)
        content=self.rfile.read(size)
        if len(content)!=size: raise Problem('The upload was interrupted. Please try again.')
        return content
    def dispatch(self,method):
        try:
            self.guard()
            path=urlparse(self.path).path
            if path == '/api/health' and method=='GET': return self.send(200,dependency_status())
            if path == '/api/conversations':
                with connect() as db:
                    if method=='GET': return self.send(200,[dict(x) for x in db.execute('SELECT * FROM conversations ORDER BY updated DESC')])
                    if method=='POST':
                        if db.execute('SELECT COUNT(*) FROM conversations').fetchone()[0]>=100: raise Problem('Maximum 100 conversations. Delete an old conversation first.',409)
                        item={'id':uuid.uuid4().hex,'title':'New conversation','created':time.time(),'updated':time.time()}
                        db.execute('INSERT INTO conversations VALUES(:id,:title,:created,:updated)',item)
                        db.commit()
                        return self.send(201,item)
            match=re.fullmatch(r'/api/conversations/([a-f0-9]{32})(/export)?',path)
            if match:
                cid=match[1]
                with GATE, connect() as db:
                    conversation=db.execute('SELECT * FROM conversations WHERE id=?',(cid,)).fetchone()
                    if not conversation: raise Problem('Conversation not found.',404)
                    rows=[row_turn(x) for x in db.execute('SELECT * FROM turns WHERE conversation_id=? ORDER BY created',(cid,))]
                    if method=='DELETE':
                        if any(x['status'] in ACTIVE for x in rows): raise Problem('Cancel the active turn before deleting this conversation.',409)
                        db.execute('DELETE FROM conversations WHERE id=?',(cid,))
                        db.commit()
                        for item in rows: shutil.rmtree(DATA/'turns'/item['id'],ignore_errors=True)
                        return self.send(200,{'deleted':True})
                    if method=='GET': return self.send(200,{'version':1,'conversation':dict(conversation),'turns':rows})
            if path == '/api/turns' and method=='POST':
                data=json.loads(self.body())
                text=data.get('text','')
                if not isinstance(text,str) or not 1 <= len(text.strip()) <= 4000: raise Problem('Type between 1 and 4,000 characters.')
                return self.send(202,create_turn(data.get('conversation_id'),text=text.strip()))
            if path == '/api/audio' and method=='POST':
                data=self.body()
                return self.send(202,create_turn(parse_qs(urlparse(self.path).query).get('conversation_id',[None])[0],audio=data))
            match=re.fullmatch(r'/api/turns/([a-f0-9]{32})(/(cancel|retry|audio))?',path)
            if match:
                tid,action=match[1],match[3]
                item=turn(tid)
                if method=='GET' and action is None: return self.send(200,item)
                if method=='GET' and action=='audio':
                    audio=DATA/'turns'/tid/'reply.wav'
                    if not audio.is_file(): raise Problem('No spoken response is available yet.',404)
                    return self.send(200,audio.read_bytes(),'audio/wav')
                if method=='POST':
                    with GATE:
                        if action=='cancel':
                            if CURRENT==tid: STOP.set()
                            return self.send(200,{'cancel_requested':CURRENT==tid})
                        if action=='retry':
                            if CURRENT: raise Problem('Another turn is running. Wait or cancel it first.',409)
                            if item['status'] not in {'failed','cancelled','interrupted'}: raise Problem('Only stopped or failed turns can be retried.',409)
                            update(tid,status='queued',error=''); launch(tid)
                            return self.send(202,turn(tid))
            if path.startswith('/api/') or method!='GET': raise Problem('Endpoint not found.',404)
            relative=unquote(path).lstrip('/') or 'index.html'
            file=(ROOT/'dist'/relative).resolve()
            if not file.is_relative_to((ROOT/'dist').resolve()): raise Problem('Not found.',404)
            if not file.is_file(): raise Problem('Build the frontend with npm run build first.',404)
            return self.send(200,file.read_bytes(),mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
        except Problem as error: self.send(error.status,{'error':error.message})
        except (json.JSONDecodeError,TypeError,ValueError): self.send(400,{'error':'That request could not be read. Please try again.'})
        except Exception: self.send(500,{'error':'The companion could not save this change. Check disk space and restart it.'})
    def do_GET(self): self.dispatch('GET')
    def do_POST(self): self.dispatch('POST')
    def do_DELETE(self): self.dispatch('DELETE')
    def do_OPTIONS(self): self.send(403,{'error':'Cross-origin access is not allowed.'})

if __name__=='__main__':
    os.umask(0o077)
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
    initialize()
    print(f'AI Voice Agent · http://127.0.0.1:{PORT} · Ctrl-C to stop',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt:
        STOP.set()
        with GATE:
            if PROCESS and PROCESS.poll() is None:
                try: os.killpg(PROCESS.pid,signal.SIGTERM)
                except ProcessLookupError: pass
        server.server_close()
