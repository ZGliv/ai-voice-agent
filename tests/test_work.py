"""Claude Code jobs on their own branch, started by voice, and the overnight rundown."""
import json, subprocess, tempfile, time, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import companion as c
import codex_jobs as jobs, rundown, scheduler

def repo(folder):
    subprocess.run(['git','init','-q','-b','main',str(folder)],check=True)
    (folder/'app.py').write_text('print(1)\n')
    git=lambda *a:subprocess.run(['git','-c','user.name=Zack','-c','user.email=z@x',*a],cwd=folder,check=True,capture_output=True)
    git('add','-A');git('commit','-q','-m','Initial app')
    return git

class Base(unittest.TestCase):
    def setUp(self):
        catalog=patch('project_memory.catalog',return_value=[{'id':'parl-ai','name':'Parl.ai'}]);catalog.start();self.addCleanup(catalog.stop)
        self.temp=tempfile.TemporaryDirectory();self.old=c.DATA;c.DATA=Path(self.temp.name);c.initialize()
        self.project=Path(self.temp.name)/'parlai';self.project.mkdir();self.git=repo(self.project)
        (c.DATA/'codex-projects.json').write_text(json.dumps({'parl-ai':str(self.project)}))
    def tearDown(self):c.DATA=self.old;self.temp.cleanup()

class ClaudeJobTests(Base):
    def test_claude_job_works_on_its_own_branch_and_is_committed(self):
        job=jobs.draft(c,'parl-ai','Fix the signup bug',None,engine='claude');jobs.update(c,job['id'],status='preparing')
        seen={}
        def worker(core,job,command,prompt,directory,**extra):
            seen.update(command=command,prompt=prompt,cwd=extra.get('cwd'))
            (extra['cwd']/'app.py').write_text('print(2)\n')
            extra['parse']({'type':'result','result':'Fixed the signup bug and ran the tests.'})
            return SimpleNamespace(returncode=0)
        with patch.object(jobs,'execute_worker',side_effect=worker),patch.object(jobs,'open_on_mac'),patch('assistant_jobs.notify_done') as told:
            jobs.run(c,jobs.get_job(c,job['id']),str(self.project))
        done=jobs.get_job(c,job['id'])
        self.assertEqual(done['status'],'completed',done['error'])
        self.assertTrue(done['branch'].startswith('jarvis/fix-the-signup-bug-'))
        self.assertIn('Committed on branch '+done['branch'],done['result']);self.assertIn('Nothing was pushed',done['result'])
        log=subprocess.run(['git','log','--format=%s',done['branch']],cwd=self.project,capture_output=True,text=True).stdout
        self.assertIn('Jarvis: Fix the signup bug',log)
        self.assertEqual((self.project/'app.py').read_text(),'print(1)\n')   # his own checkout is untouched
        command=seen['command'];self.assertIn('acceptEdits',command)
        self.assertIn('"sandbox": {"enabled": true',command[command.index('--settings')+1])
        self.assertIn('Bash(git push:*)',command[command.index('--disallowedTools')+1])
        told.assert_called_once()

    def test_voice_starts_claude_code_on_a_named_project(self):
        cid='a'*32
        with c.connect() as db:db.execute('INSERT INTO conversations VALUES(?,?,?,?)',(cid,'Phone call',time.time(),time.time()))
        item={'id':'t'*32,'conversation_id':cid,'input_text':'spin up Claude Code on Parl.ai to fix the signup bug'}
        with patch.object(jobs,'start_job',side_effect=lambda core,jid:jobs.get_job(core,jid)),patch('shutil.which',return_value='/bin/claude'):
            result=c.companion_tools.execute(c,item,'start_codex_job',{'task':'Fix the signup bug','project_id':'parl-ai'})
        self.assertEqual((result['project_id'],result['engine']),('parl-ai','claude'))

    def test_unlinked_project_is_refused_clearly(self):
        cid='b'*32
        with c.connect() as db:db.execute('INSERT INTO conversations VALUES(?,?,?,?)',(cid,'Phone call',time.time(),time.time()))
        item={'id':'u'*32,'conversation_id':cid,'input_text':'start work'}
        with self.assertRaises(c.Problem) as refused:c.companion_tools.execute(c,item,'start_codex_job',{'task':'Fix something'})
        self.assertIn('parl-ai',refused.exception.message)

class RundownTests(Base):
    def test_rundown_lists_new_commits_and_finished_coding_jobs(self):
        (self.project/'app.py').write_text('print(3)\n');self.git('commit','-qam','Add the onboarding screen')
        job=jobs.draft(c,'parl-ai','Fix the signup bug',None,engine='claude')
        jobs.update(c,job['id'],status='completed',branch='jarvis/fix-the-signup-bug-abc123')
        lookup=jobs.draft(c,'__assistant__','How many jobs today?',None);jobs.update(c,lookup['id'],status='completed')
        found=rundown.gather(c,hours=2)
        self.assertEqual(found['project_commits']['Parl.ai']['latest'][0],'Add the onboarding screen')
        self.assertEqual([j['by'] for j in found['jobs_finished']],['Claude Code'])   # quick lookups are not "work"
        self.assertEqual(found['jobs_finished'][0]['branch'],'jarvis/fix-the-signup-bug-abc123')

    def test_morning_looks_back_to_six_pm_yesterday(self):
        from datetime import datetime
        morning=datetime.now().replace(hour=7,minute=45).timestamp()
        start=datetime.fromtimestamp(rundown.since_default(morning))
        self.assertEqual((start.hour,start.minute),(18,0));self.assertLess(start.timestamp(),morning)

    def test_morning_briefing_now_also_refreshes_the_briefing(self):
        self.assertIn('BRIEFING:',scheduler.DEFAULTS[0]['task']);self.assertIn('notion_recent',scheduler.DEFAULTS[0]['task'])

if __name__=='__main__':unittest.main()
