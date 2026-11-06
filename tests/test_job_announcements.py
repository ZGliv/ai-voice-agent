import tempfile,unittest,threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import job_announcements as a
import companion
class AnnouncementTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.core=SimpleNamespace(DATA=Path(self.tmp.name),PIPER_MODEL='test',CURRENT=None,Problem=companion.Problem,SPEECH=Mock())
  self.job={'id':'a'*32,'status':'completed','project_id':'__research__','result':'malicious text must never be spoken','preview_dir':''}
 def tearDown(self):self.tmp.cleanup()
 def test_announcement_is_factual_and_cached(self):
  def speak(request,*args):Path(request['destination']).write_bytes(b'test audio')
  self.core.SPEECH.call.side_effect=speak
  path=a.prepare(self.core,self.job);self.assertTrue(path.is_file());a.prepare(self.core,self.job)
  self.core.SPEECH.call.assert_called_once();self.assertNotIn('malicious',self.core.SPEECH.call.call_args.args[0]['text'])
 def test_busy_and_running_jobs_do_not_synthesize(self):
  self.core.CURRENT='turn'
  with self.assertRaises(companion.Problem):a.prepare(self.core,self.job)
  self.core.CURRENT=None;self.job['status']='running'
  with self.assertRaises(companion.Problem):a.prepare(self.core,self.job)
  self.core.SPEECH.call.assert_not_called()
 def test_failed_provider_does_not_cache_success(self):
  self.core.SPEECH.call.side_effect=RuntimeError('secret provider error')
  with self.assertRaises(companion.Problem) as raised:a.prepare(self.core,self.job)
  self.assertNotIn('secret',raised.exception.message);self.assertFalse(a.audio_path(self.core,self.job).exists())
