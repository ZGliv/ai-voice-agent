import json,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from native_transcriber import NativeTranscriber,speech_text

class NativeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.model=Path(self.tmp.name)/'model.bin';self.model.touch();self.worker=NativeTranscriber('whisper-cli',self.model)
 def test_cancelled_call_never_starts_process(self):
  stop=threading.Event();stop.set()
  with patch('native_transcriber.subprocess.Popen') as spawn:
   with self.assertRaises(InterruptedError):self.worker.call({'source':'audio.wav'},stop)
   spawn.assert_not_called()
 def test_output_parsing_and_temp_cleanup(self):
  paths=[]
  def spawn(command,**kwargs):
   output=Path(command[command.index('-of')+1]).with_suffix('.json');paths.append(output)
   output.write_text(json.dumps({'transcription':[{'text':' Hello'},{'text':' Zack.'}]}))
   process=Mock();process.poll.return_value=0;process.returncode=0;return process
  with patch('native_transcriber.subprocess.Popen',side_effect=spawn):result=self.worker.call({'source':'audio.wav'},threading.Event())
  self.assertEqual(result,{'text':'Hello Zack.','segments':[]});self.assertFalse(paths[0].exists());self.assertIsNone(self.worker.process)
 def test_warmup_runs_native_inference_on_temporary_silence(self):
  seen=[]
  def spawn(command,**kwargs):
   import wave
   source=Path(command[command.index('-f')+1]);seen.append(source)
   with wave.open(str(source)) as audio:self.assertEqual(audio.getnframes(),16000)
   process=Mock();process.poll.return_value=0;process.returncode=0;return process
  with patch('native_transcriber.subprocess.Popen',side_effect=spawn) as launch:
   self.assertEqual(self.worker.call({'warm':True},threading.Event()),{'ready':True})
  launch.assert_called_once();self.assertFalse(seen[0].exists())
 def test_cancel_terminates_inflight_native_process(self):
  stop=threading.Event();process=Mock();process.poll.return_value=None
  def spawn(*args,**kwargs):stop.set();return process
  with patch('native_transcriber.subprocess.Popen',side_effect=spawn):
   with self.assertRaises(InterruptedError):self.worker.call({'source':'audio.wav'},stop)
  process.terminate.assert_called_once();self.assertIsNone(self.worker.process)
 def test_missing_model_does_not_download(self):
  self.model.unlink()
  with self.assertRaises(RuntimeError):self.worker.call({'warm':True},threading.Event())

 def test_sound_only_annotations_are_not_commands(self):
  for text in ['(water running)','(soft music)','[BLANK_AUDIO]','(wind noise) [music]']:
   self.assertEqual(speech_text([{'text':text}]),'')
  for text in ['Play soft music.','Remember to fix the running water.','(Please stop the build)','(music) Hello Jarvis.']:
   self.assertEqual(speech_text([{'text':text}]),text)
