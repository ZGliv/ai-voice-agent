import hashlib,threading,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from live_drafts import Drafts

class DraftTests(unittest.TestCase):
 def fake(self,c,cid,audio,prepare):
  return SimpleNamespace(cid=cid,digest=hashlib.sha256(audio).digest(),id='draft',stop=threading.Event(),error=None,promoted=False,timer=Mock(),cancel=Mock(),thread=Mock(is_alive=lambda:False))
 def test_only_exact_final_recording_in_same_conversation_can_be_adopted(self):
  manager=Drafts()
  with patch('live_drafts.Draft',side_effect=self.fake):manager.replace(None,'session',1,'conversation',b'whole recording',True)
  self.assertIsNone(manager.take('session',1,'other',b'whole recording'))
  draft=manager.take('session',1,'conversation',b'whole recording')
  self.assertTrue(draft.promoted);draft.timer.cancel.assert_called_once();self.assertIsNone(manager.current)
 def test_continuing_speech_cancels_preparation_and_late_upload_cannot_revive_it(self):
  manager=Drafts()
  with patch('live_drafts.Draft',side_effect=self.fake):
   manager.replace(None,'session',1,'conversation',b'first',True);draft=manager.current[2]
   manager.replace(None,'session',2,'conversation');draft.cancel.assert_called_once()
   self.assertFalse(manager.replace(None,'session',1,'conversation',b'first',True))
   self.assertIsNone(manager.current)
 def test_old_session_cancel_does_not_cancel_new_utterance(self):
  manager=Drafts()
  with patch('live_drafts.Draft',side_effect=self.fake):manager.replace(None,'new',1,'conversation',b'new')
  draft=manager.current[2];manager.replace(None,'old',5,'conversation');draft.cancel.assert_not_called()
 def test_action_draft_never_generates_speech_or_executes_tools(self):
  import tempfile
  from pathlib import Path
  from live_drafts import Draft
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'turns').mkdir()
   speech=Mock();c=SimpleNamespace(DATA=root,NATIVE_WHISPER='native',NATIVE_MODEL=root/'model',fish_voice=Mock(),fish_text_stream=Mock(),needs_tools=lambda text:True,local_runtime=Mock(),companion_tools=Mock())
   c.fish_text_stream.TextSpeech.return_value=speech
   with patch('live_drafts.native_transcriber.NativeTranscriber') as worker:
    worker.return_value.call.return_value={'text':'Build me a website'}
    draft=Draft(c,'conversation',b'fixture',True);self.assertTrue(draft.done.wait(2));draft.cancel()
   c.local_runtime.chat.assert_not_called();c.companion_tools.execute.assert_not_called();speech.feed.assert_not_called()
   self.assertEqual(draft.text,'Build me a website');self.assertFalse(draft.path.exists())

 def test_changed_final_audio_cancels_draft_and_falls_back(self):
  manager=Drafts()
  with patch('live_drafts.Draft',side_effect=self.fake):manager.replace(None,'session',1,'conversation',b'first',True)
  draft=manager.current[2];self.assertIsNone(manager.take('session',1,'conversation',b'continued recording'))
  draft.cancel.assert_called_once();self.assertIsNone(manager.current)
