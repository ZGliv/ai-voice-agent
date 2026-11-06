"""Ephemeral rolling recognition and speech preparation. Never executes tools."""
import hashlib,io,re,shutil,threading,time,uuid,wave
import native_transcriber

class Draft:
    def __init__(self,c,cid,audio,prepare):
        self.c=c;self.cid=cid;self.digest=hashlib.sha256(audio).digest();self.id=uuid.uuid4().hex
        self.path=c.DATA/'turns'/self.id;self.path.mkdir(mode=0o700);(self.path/'draft-only').touch(mode=0o600)
        self.stop=threading.Event();self.recognized=threading.Event();self.done=threading.Event()
        self.text='';self.answer='';self.error=None;self.speech=None;self.promoted=False;self.timings={};self.prepare=prepare
        self.thread=threading.Thread(target=self.run,args=(audio,),daemon=True);self.thread.start()
        self.timer=threading.Timer(90,self.cancel);self.timer.daemon=True;self.timer.start()
    def cancel(self):
        if self.promoted:return
        self.stop.set();self.timer.cancel()
        if self.done.is_set():shutil.rmtree(self.path,ignore_errors=True)
    def run(self,audio):
        c=self.c;start=time.monotonic()
        try:
            # Establish the free speech connection while local recognition runs.
            # No text/audio is sent until a conversational answer is produced.
            if self.prepare and c.fish_voice.key(c.DATA) and c.fish_text_stream.available():
                self.speech=c.fish_text_stream.TextSpeech(self.path,c.fish_voice.key(c.DATA),self.stop)
            source=self.path/'input.wav';source.write_bytes(audio)
            worker=native_transcriber.NativeTranscriber(c.NATIVE_WHISPER,c.NATIVE_MODEL)
            result=worker.call({'source':str(source)},self.stop)
            self.text=result.get('text','').strip();self.timings['recognition']=round(time.monotonic()-start,3);self.recognized.set()
            if not self.text or not self.prepare or c.needs_tools(self.text):return
            if not c.fish_voice.key(c.DATA) or not c.fish_text_stream.available():return
            with c.connect() as db:
                history=db.execute("SELECT input_text,output_text FROM turns WHERE conversation_id=? AND status='complete' ORDER BY created DESC LIMIT 8",(self.cid,)).fetchall()
            messages=[{'role':'system','content':c.CONVERSATION_PROMPT}]
            for row in reversed(history):messages.extend([{'role':'user','content':row['input_text']},{'role':'assistant','content':row['output_text']}])
            messages.append({'role':'user','content':self.text})
            while sum(len(m['content']) for m in messages)>16000 and len(messages)>2:del messages[1:3]
            def partial(raw):
                prefix=re.match(r'^SAY[ \t]*\r?\n',raw)
                if not prefix:return
                body=raw[prefix.end():]
                if not body:return
                if self.speech is None:self.speech=c.fish_text_stream.TextSpeech(self.path,c.fish_voice.key(c.DATA),self.stop)
                self.speech.feed(body)
            reply=c.local_runtime.chat(c.OLLAMA+'/api/chat',{'model':c.LLM,'think':False,'keep_alive':-1,'messages':messages,'options':{'num_ctx':c.LLM_CONTEXT,'num_predict':300,'temperature':.2}},self.stop,partial)
            if reply.get('tool_calls'):raise RuntimeError('No tools permitted in a draft')
            raw=reply.get('content','');prefix=re.match(r'^SAY[ \t]*\r?\n',raw)
            if not prefix:return
            partial(raw);self.answer=raw[prefix.end():].strip()
            if self.speech:
                self.speech.finish(raw[prefix.end():]);self.timings['speech']=self.speech.wait()
        except Exception:self.error=True
        finally:
            if self.speech:self.speech.close()
            self.recognized.set();self.done.set()
            if self.stop.is_set() and not self.promoted:shutil.rmtree(self.path,ignore_errors=True)

class Drafts:
    def __init__(self):self.lock=threading.RLock();self.current=None;self.versions={};self.adopted={}
    def replace(self,c,session,revision,cid,audio=None,prepare=False):
        with self.lock:
            previous=self.versions.get(session,-1)
            if revision<=previous:return False
            self.versions[session]=revision
            if len(self.versions)>64:del self.versions[next(iter(self.versions))]
            old=self.current
            if old and audio is None and old[0]!=session:return False
            if old:
                old[2].cancel()
                # Serialize native inference; don't pile up GPU work on rapid revisions.
                old[2].thread.join(timeout=2)
                if old[2].thread.is_alive():self.current=None;return False
            self.current=None
            if audio is not None:self.current=(session,revision,Draft(c,cid,audio,prepare))
            return True
    def take(self,session,revision,cid,audio):
        with self.lock:
            current=self.current
            if not current or current[:2]!=(session,revision):return None
            draft=current[2]
            if draft.cid!=cid:return None
            if draft.digest!=hashlib.sha256(audio).digest():
                draft.cancel();self.current=None;self.versions[session]=revision+1;return None
            if draft.stop.is_set() or draft.error:return None
            draft.promoted=True;draft.timer.cancel();self.current=None;self.adopted[draft.id]=draft
            return draft
    def shutdown(self):
        with self.lock:
            if self.current:self.current[2].cancel();self.current=None
    def dispatch(self,h,method,path,c):
        match=re.fullmatch(r'/api/drafts/([a-f0-9]{32})',path)
        if not match:return False
        query=c.parse_qs(c.urlparse(h.path).query);revision=int(query.get('revision',['-1'])[0]);cid=query.get('conversation_id',[''])[0]
        if not 0<=revision<=10000:raise c.Problem('Invalid draft revision.')
        if method=='DELETE':self.replace(c,match[1],revision,cid);h.send(200,{'cancelled':True});return True
        if method!='POST':raise c.Problem('Invalid draft method.',405)
        with c.connect() as db:
            if not db.execute('SELECT id FROM conversations WHERE id=?',(cid,)).fetchone():raise c.Problem('Choose a conversation first.',404)
        if c.CURRENT or not c.USE_NATIVE:raise c.Problem('Live recognition is busy.',409)
        audio=h.body()
        try:
            with wave.open(io.BytesIO(audio)) as wav:
                if wav.getnchannels()!=1 or wav.getsampwidth()!=2 or not 8000<=wav.getframerate()<=48000 or not .2<=wav.getnframes()/wav.getframerate()<=61:raise ValueError()
        except Exception:raise c.Problem('Invalid live recording.')
        accepted=self.replace(c,match[1],revision,cid,audio,query.get('prepare',['0'])[0]=='1')
        h.send(202,{'accepted':accepted});return True

DRAFTS=Drafts()
