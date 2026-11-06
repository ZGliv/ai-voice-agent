import tempfile,threading,unittest,time,wave
from pathlib import Path
from unittest.mock import patch
import fish_text_stream as f

@unittest.skipUnless(f.available(),'Install requirements.txt to test WebSocket speech')
class TextStreamTests(unittest.TestCase):
 def test_exact_free_voice_pcm_before_text_finishes_and_one_stop(self):
  import msgpack
  sent=[];first=threading.Event()
  class Socket:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def send(self,data):sent.append(msgpack.unpackb(data,raw=False))
   def recv(self,timeout):
    if any(e['event']=='text' for e in sent) and not first.is_set():
     first.set();return msgpack.packb({'event':'audio','audio':b'\x01\x01'*2400},use_bin_type=True)
    if any(e['event']=='stop' for e in sent):return msgpack.packb({'event':'finish','reason':'stop'},use_bin_type=True)
    time.sleep(.001);raise TimeoutError()
  with tempfile.TemporaryDirectory() as temp,patch('websockets.sync.client.connect',return_value=Socket()) as connect:
   stream=f.TextSpeech(temp,'fake-secret',threading.Event());stream.feed('First sentence. ')
   self.assertTrue(first.wait(2));self.assertIsNone(stream.text_done)
   stream.finish('First sentence. Second sentence.');metrics=stream.wait();stream.close()
   self.assertEqual(connect.call_args.kwargs['additional_headers']['model'],'s2.1-pro-free')
   self.assertEqual(sent[0]['request']['reference_id'],f.fish_voice.VOICE)
   self.assertEqual(''.join(e['text'] for e in sent if e['event']=='text'),'First sentence. Second sentence. ')
   self.assertEqual(sum(e['event']=='stop' for e in sent),1)
   with wave.open(str(Path(temp)/'reply.pending.wav')) as wav:self.assertEqual(wav.getnframes(),2400)
 def test_error_finish_is_not_success_and_never_falls_back(self):
  import msgpack
  class Socket:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def send(self,data):pass
   def recv(self,timeout):return msgpack.packb({'event':'finish','reason':'error'},use_bin_type=True)
  with tempfile.TemporaryDirectory() as temp,patch('websockets.sync.client.connect',return_value=Socket()) as connect:
   stream=f.TextSpeech(temp,'secret',threading.Event())
   with self.assertRaises(f.fish_voice.VoiceError):stream.wait()
   stream.close();self.assertEqual(connect.call_count,1)
 def test_cancel_closes_socket_without_committing_wav(self):
  class Socket:
   closed=False
   def __enter__(self):return self
   def __exit__(self,*args):self.closed=True
   def send(self,data):pass
   def recv(self,timeout):time.sleep(.01);raise TimeoutError()
  socket=Socket();stop=threading.Event()
  with tempfile.TemporaryDirectory() as temp,patch('websockets.sync.client.connect',return_value=socket):
   stream=f.TextSpeech(temp,'secret',stop);time.sleep(.03);stop.set()
   with self.assertRaises(InterruptedError):stream.wait()
   stream.close();self.assertTrue(socket.closed);self.assertFalse((Path(temp)/'reply.wav').exists())
