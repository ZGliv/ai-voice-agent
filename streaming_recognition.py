"""Private, ordered PCM transport to a resident Kyutai semantic STT worker."""
import hashlib,io,re,threading,time,wave
from pathlib import Path
import local_runtime

class StreamingRecognition:
 def __init__(self,root):
  self.python=Path(root)/'.venv-kyutai/bin/python'
  self.worker=local_runtime.Worker([str(self.python),str(Path(root)/'kyutai_worker.py')])
  self.lock=threading.RLock();self.current=None;self.ready=False
 def warm(self):
  if self.python.is_file():
   try:self.worker.call({'warm':True},threading.Event(),60);self.ready=True
   except Exception:self.ready=False
 def dispatch(self,h,method,path,c):
  match=re.fullmatch(r'/api/listen/([a-f0-9]{32})',path)
  if not match:return False
  sid=match[1]
  if method=='DELETE':
   with self.lock:
    if self.current and self.current['id']==sid:self.current=None
   h.send(200,{'closed':True});return True
  if method!='POST':raise c.Problem('Invalid streaming method.',405)
  if not self.ready:raise c.Problem('Streaming recognition is warming up. Please reconnect in a moment.',503)
  query=c.parse_qs(c.urlparse(h.path).query);cid=query.get('conversation_id',[''])[0];seq=int(query.get('sequence',['-1'])[0])
  pcm=h.body()
  if len(pcm)!=11520:raise c.Problem('Use three 80ms PCM frames.')
  with c.connect() as db:
   if not db.execute('SELECT id FROM conversations WHERE id=?',(cid,)).fetchone():raise c.Problem('Choose a conversation first.',404)
  with self.lock:
   state=self.current
   if not state or state['id']!=sid:
    if seq!=0:raise c.Problem('The audio stream expired. Reconnect the microphone.',409)
    state={'id':sid,'cid':cid,'sequence':-1,'pcm':bytearray(),'result':{},'updated':time.monotonic()};self.current=state
   if state['cid']!=cid or time.monotonic()-state['updated']>15:raise c.Problem('Audio session expired.',409)
   if seq==state['sequence']:h.send(200,state['result']);return True
   if seq!=state['sequence']+1 or seq>249:raise c.Problem('Audio packets arrived out of order.',409)
   result=self.worker.call({'session':sid,'pcm':c.base64.b64encode(pcm).decode()},threading.Event(),10)
   state['pcm'].extend(pcm);state['sequence']=seq;state['updated']=time.monotonic();state['result']=result
   h.send(200,result);return True
 def take(self,sid,sequence,cid,audio):
  with self.lock:
   state=self.current
   if not state or state['id']!=sid or state['cid']!=cid or state['sequence']!=sequence:return None
   if time.monotonic()-state['updated']>15 or not state['result'].get('end'):return None
   try:
    with wave.open(io.BytesIO(audio)) as wav:
     if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())!=(1,2,24000):return None
     pcm=wav.readframes(wav.getnframes())
   except Exception:return None
   if hashlib.sha256(pcm).digest()!=hashlib.sha256(state['pcm']).digest():return None
   self.current=None
   return state['result']['text']
 def close(self):self.current=None;self.worker.close()
