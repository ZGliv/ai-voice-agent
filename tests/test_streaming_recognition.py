import io,time,unittest,wave
from streaming_recognition import StreamingRecognition
class RecognitionTests(unittest.TestCase):
 def test_transcript_receipt_binds_final_pcm_conversation_and_sequence(self):
  service=StreamingRecognition('/tmp');pcm=b'\x01\x01'*5760
  service.current={'id':'session','cid':'conversation','sequence':2,'updated':time.monotonic(),'pcm':bytearray(pcm),'result':{'end':True,'text':'Hello sir'}}
  audio=io.BytesIO()
  with wave.open(audio,'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(pcm)
  self.assertIsNone(service.take('session',2,'other',audio.getvalue()))
  self.assertIsNone(service.take('session',1,'conversation',audio.getvalue()))
  self.assertIsNone(service.take('session',2,'conversation',audio.getvalue()[:-2]+b'\0\0'))
  self.assertEqual(service.take('session',2,'conversation',audio.getvalue()),'Hello sir')
  self.assertIsNone(service.current)
