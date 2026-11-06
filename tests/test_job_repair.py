import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import companion as core,codex_jobs as jobs

class RepairTests(unittest.TestCase):
 def setUp(self):
  catalog_patch=patch('project_memory.catalog',return_value=[]);catalog_patch.start();self.addCleanup(catalog_patch.stop)
  self.temp=tempfile.TemporaryDirectory();self.old=core.DATA;core.DATA=Path(self.temp.name);core.initialize()
  self.job=jobs.draft(core,'__new_site__','Build a working timer.',None);jobs.update(core,self.job['id'],status='preparing')
  self.directory=core.DATA/'jobs'/self.job['id'];self.workspace=self.directory/'workspace';self.workspace.mkdir(parents=True)
  self.steps=[{'action':'click','selector':'#reset'},{'action':'expect_text','selector':'#time','text':'25:00'}]
  (self.workspace/'.jarvis-checks.json').write_text(json.dumps(self.steps))
 def tearDown(self):core.DATA=self.old;self.temp.cleanup()
 def run_case(self,reports,cancel=False):
  def execute(core,job,command,prompt,directory,**kwargs):
   (directory/('repair-result.txt' if kwargs else 'result.txt')).write_text('Worker result')
   if kwargs:
    self.assertEqual(kwargs['limit'],300)
    (self.workspace/'.jarvis-checks.json').write_text('[]')
    if cancel:jobs.update(core,job['id'],status='cancelled')
   return SimpleNamespace(returncode=0)
  with patch.object(jobs,'make_workspace',return_value=self.workspace),patch.object(jobs,'read_preview',return_value='http://127.0.0.1:1234/'),patch.object(jobs,'execute_worker',side_effect=execute) as worker,patch.object(jobs.preview_verifier,'verify',side_effect=reports) as verify:
   jobs.run(core,self.job,None)
  return jobs.get_job(core,self.job['id']),worker,verify
 def test_repair_rechecks_frozen_plan_and_retains_initial_failure(self):
  result,worker,verify=self.run_case([{'status':'failed','summary':'Reset broken','runs':[]},{'status':'passed','summary':'Passed'}])
  self.assertEqual(worker.call_count,2);self.assertEqual(verify.call_args.kwargs['steps_override'],self.steps)
  report=json.loads(result['verification']);self.assertEqual(report['repair']['initialSummary'],'Reset broken');self.assertEqual(report['status'],'passed')
 def test_failed_repair_does_not_loop_or_claim_success(self):
  result,worker,verify=self.run_case([{'status':'failed','summary':'Broken'},{'status':'failed','summary':'Still broken'}])
  self.assertEqual(worker.call_count,2);self.assertEqual(verify.call_count,2);self.assertIn('found problems',result['error'])
 def test_unavailable_browser_does_not_trigger_repair(self):
  result,worker,verify=self.run_case([{'status':'unavailable','summary':'Session closed'}])
  self.assertEqual(worker.call_count,1);self.assertIn('could not run',result['error'])
 def test_cancellation_during_repair_is_preserved(self):
  result,worker,verify=self.run_case([{'status':'failed','summary':'Broken'}],cancel=True)
  self.assertEqual(result['status'],'cancelled');self.assertEqual(verify.call_count,1)
