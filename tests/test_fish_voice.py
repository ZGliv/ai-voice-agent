import tempfile,unittest,threading,json,wave,io
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
import fish_voice as f
class FishVoiceTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.data=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def test_free_model_voice_and_no_context_in_request(self):
  class Response:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self,n):return b'test audio'
  def decode(command,**kwargs):
   with wave.open(command[-1],'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\x01\x01'*4800)
  with patch.object(f,'urlopen',return_value=Response()) as request,patch.object(f.subprocess,'run',side_effect=decode):
   f.synthesize('A reply',self.data/'sample.wav','test-secret-value',threading.Event())
  req=request.call_args.args[0];self.assertEqual(req.get_header('Model'),'s2.1-pro-free')
  body=json.loads(req.data);self.assertEqual(body['reference_id'],f.VOICE);self.assertEqual(body['text'],'A reply');self.assertNotIn('context',body)
 def test_payment_error_never_retries_paid_model(self):
  with patch.object(f,'urlopen',side_effect=HTTPError('url',402,'payment',{},io.BytesIO())) as request:
   with self.assertRaisesRegex(f.VoiceError,'No paid model'):f.synthesize('Reply',self.data/'out.wav','secret',threading.Event())
  self.assertEqual(request.call_count,1);self.assertFalse((self.data/'out.wav').exists())
 def test_key_only_saved_after_success_and_status_never_exposes_it(self):
  secret='private-test-key-12345'
  with patch.object(f,'synthesize',side_effect=f.VoiceError('Denied')):
   with self.assertRaises(f.VoiceError):f.connect(self.data,secret)
  self.assertFalse((self.data/'fish-api-key').exists())
  def sample(text,path,key,stop):path.write_bytes(b'sample')
  with patch.object(f,'synthesize',side_effect=sample):result=f.connect(self.data,secret)
  self.assertTrue(result['connected']);self.assertNotIn(secret,json.dumps(result));self.assertEqual((self.data/'fish-api-key').stat().st_mode&0o777,0o600)
 def test_cancelled_request_does_not_contact_provider(self):
  stop=threading.Event();stop.set()
  with patch.object(f,'urlopen') as request:
   with self.assertRaises(InterruptedError):f.synthesize('reply',self.data/'out.wav','secret',stop)
  request.assert_not_called()
 def test_pcm_stream_delivers_before_end_and_keeps_free_voice(self):
  chunks=[]
  class Response:
   index=0
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read1(self,n):
    self.index+=1
    return [b'\x01'*2401,b'\x01'*2401,b''][self.index-1]
  target=self.data/'stream.wav'
  with patch.object(f,'urlopen',return_value=Response()) as request:
   f.synthesize('A reply',target,'secret',threading.Event(),on_chunk=chunks.append)
  self.assertEqual(b''.join(chunks),b'\x01'*4802)
  with wave.open(str(target),'rb') as wav:self.assertEqual(wav.getnframes(),2401)
  req=request.call_args.args[0];self.assertEqual(req.get_header('Model'),f.MODEL)
  self.assertEqual(json.loads(req.data)['reference_id'],f.VOICE);self.assertEqual(json.loads(req.data)['format'],'pcm')
 def test_stream_payment_failure_does_not_fallback(self):
  with patch.object(f,'urlopen',side_effect=HTTPError('url',402,'payment',{},io.BytesIO())) as request:
   with self.assertRaisesRegex(f.VoiceError,'No paid model'):f.synthesize('Reply',self.data/'stream.wav','secret',threading.Event(),on_chunk=lambda _:None)
  self.assertEqual(request.call_count,1);self.assertFalse((self.data/'stream.wav').exists())
