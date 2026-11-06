import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import preview_verifier as verifier

class VerificationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.plan=self.root/'.jarvis-checks.json'
 def test_missing_plan_is_load_only(self):self.assertEqual(verifier.load_steps(self.root),[])
 def test_rejects_executable_actions_and_unbounded_waits(self):
  for plan in [[{'action':'evaluate','text':'alert(1)'}],[{'action':'wait','ms':2001}],[{'action':'wait','ms':2000}]*5,[{'action':'visible','selector':'x'*301}]]:
   self.plan.write_text(json.dumps(plan))
   with self.assertRaises(ValueError):verifier.load_steps(self.root)
 def test_symlink_plan_is_rejected(self):
  other=self.root/'other';other.write_text('[]');self.plan.symlink_to(other)
  with self.assertRaises(ValueError):verifier.load_steps(self.root)
 def test_unconfigured_never_passes(self):
  self.assertEqual(verifier.verify(SimpleNamespace(DATA=self.root),{},'http://127.0.0.1:1234/')['status'],'unavailable')
 def test_failed_cli_never_passes(self):
  (self.root/'browser-session').write_text('existing-session');(self.root/'jobs'/'a').mkdir(parents=True)
  with patch('preview_verifier.shutil.which',return_value='/bin/npx'),patch('preview_verifier.subprocess.run',return_value=SimpleNamespace(returncode=1,stdout='')):
   report=verifier.verify(SimpleNamespace(DATA=self.root),{'id':'a','worktree':str(self.root)},'http://127.0.0.1:1234/')
  self.assertEqual(report['status'],'unavailable')
