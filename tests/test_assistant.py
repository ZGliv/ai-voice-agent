import json, os, sys, tempfile, textwrap, time, unittest
from pathlib import Path
from unittest.mock import patch
import companion as c
import companion_tools as tools
import codex_jobs as jobs
import assistant_jobs

FAKE_CLAUDE=textwrap.dedent('''\
 #!{python}
 import json,sys
 args=sys.argv[1:];prompt=sys.stdin.read()
 open({log!r},'a').write(json.dumps({{'args':args,'prompt':prompt}})+'\\n')
 def emit(e):print(json.dumps(e),flush=True)
 tools=['WebSearch','Bash','mcp__claude_ai_Gmail__search_threads','mcp__claude_ai_Gmail__send_message','mcp__claude_ai_Google_Calendar__list_events']
 emit({{'type':'system','subtype':'init','session_id':'sess-1','tools':tools}})
 if '--resume' in args:
  allowed=args[args.index('--allowedTools')+1].split(',')
  ok='mcp__claude_ai_Gmail__send_message' in allowed
  emit({{'type':'result','subtype':'success','is_error':False,'result':'Sent the email to Sarah.' if ok else 'Still blocked.','permission_denials':[]}})
 else:
  emit({{'type':'assistant','message':{{'content':[{{'type':'tool_use','name':'mcp__claude_ai_Gmail__send_message','input':{{}}}}]}}}})
  emit({{'type':'result','subtype':'success','is_error':False,'result':'I drafted a note to Sarah saying you are ten minutes late.\\n\\nDetails follow.',
   'permission_denials':[{{'tool_name':'mcp__claude_ai_Gmail__send_message','tool_use_id':'t1','tool_input':{{'to':'sarah@example.com','body':'Running ten minutes late.'}}}}]}})
''')

def wait_for(predicate,seconds=10):
 deadline=time.time()+seconds
 while time.time()<deadline:
  value=predicate()
  if value:return value
  time.sleep(.05)
 raise AssertionError('timed out')

class AssistantTests(unittest.TestCase):
 def setUp(self):
  catalog=patch('project_memory.catalog',return_value=[]);catalog.start();self.addCleanup(catalog.stop)
  sent=patch('notify.send',return_value=True);self.sent=sent.start();self.addCleanup(sent.stop)
  self.temp=tempfile.TemporaryDirectory();self.old=c.DATA;c.DATA=Path(self.temp.name);c.CURRENT=None;c.STOP.clear();c.initialize()
  self.log=Path(self.temp.name)/'claude-calls.jsonl'
  fake=Path(self.temp.name)/'claude';fake.write_text(FAKE_CLAUDE.format(python=sys.executable,log=str(self.log)));fake.chmod(0o755)
  binary=patch.object(assistant_jobs,'claude',return_value=str(fake));binary.start();self.addCleanup(binary.stop)
  (c.DATA/'assistant-tools.json').write_text(json.dumps(['WebSearch','Bash','mcp__claude_ai_Gmail__search_threads','mcp__claude_ai_Gmail__send_message']))
  with c.connect() as db:db.execute('INSERT INTO conversations VALUES(?,?,?,?)',('a'*32,'Test',time.time(),time.time()))
 def tearDown(self):c.DATA=self.old;self.temp.cleanup()
 def turn(self,text):
  with patch.object(c,'launch'):return c.create_turn('a'*32,text=text)

 def test_readonly_classification(self):
  allowed=assistant_jobs.readonly(['WebSearch','Bash','Write','mcp__claude_ai_Gmail__search_threads','mcp__claude_ai_Gmail__send_message',
   'mcp__claude_ai_Gmail__get_thread','mcp__x__get_or_create_drive','mcp__computer-use__app_screenshot','mcp__claude-in-chrome__read_page',
   'mcp__claude_ai_Notion__notion-fetch','mcp__claude_ai_Gmail__trash_thread','mcp__claude_ai_Google_Calendar__list_events'])
  self.assertEqual(set(allowed),{'WebSearch','mcp__claude_ai_Gmail__search_threads','mcp__claude_ai_Gmail__get_thread','mcp__claude_ai_Google_Calendar__list_events','mcp__claude_ai_Notion__notion-fetch'})
  notion=assistant_jobs.readonly(['mcp__claude_ai_Notion__notion-calendar-list-events','mcp__claude_ai_Notion__notion-calendar-create-events','mcp__claude_ai_Notion__notion-update-page','mcp__claude_ai_Notion__notion-search'])
  self.assertEqual(set(notion),{'mcp__claude_ai_Notion__notion-calendar-list-events','mcp__claude_ai_Notion__notion-search'})

 def test_humanize_tool_names(self):
  self.assertEqual(assistant_jobs.humanize('mcp__claude_ai_Gmail__send_message'),'Gmail: send message')
  self.assertEqual(assistant_jobs.humanize('mcp__34b9723b-af4c-4db7-b48a-c38b53cbd84d__create_draft'),'create draft')

 def test_send_waits_for_spoken_approval_then_resumes_only_that_tool(self):
  ask=self.turn('Email Sarah that I am running ten minutes late.')
  started=tools.execute(c,ask,'delegate_task',{'task':'Email Sarah that I am running ten minutes late.'})
  jid=started['id']
  job=wait_for(lambda:(j:=jobs.get_job(c,jid))['status']=='awaiting_approval' and j)
  first=json.loads(self.log.read_text().splitlines()[0])
  allowed=first['args'][first['args'].index('--allowedTools')+1].split(',')
  self.assertIn('mcp__claude_ai_Gmail__search_threads',allowed);self.assertNotIn('mcp__claude_ai_Gmail__send_message',allowed);self.assertNotIn('Bash',allowed)
  self.assertIn('dontAsk',first['args']);self.assertIn('Email Sarah',first['prompt'])
  self.assertEqual(json.loads(job['approval'])['actions'][0]['input']['to'],'sarah@example.com')
  self.assertIn('Approval needed',wait_for(lambda:self.sent.call_args)[0][1])

  check=self.turn('What is waiting for me?')
  status=tools.execute(c,check,'job_status',{})
  self.assertEqual(status['jobs'][0]['pending_actions'][0]['action'],'Gmail: send message')
  with self.assertRaises(c.Problem):tools.execute(c,check,'approve_job',{'job_id':jid})

  yes=self.turn('Yes, send it.')
  with self.assertRaises(c.Problem):tools.execute(c,yes,'approve_job',{'job_id':jid})  # must look it up first
  tools.execute(c,yes,'job_status',{})
  tools.execute(c,yes,'approve_job',{'job_id':jid})
  done=wait_for(lambda:(j:=jobs.get_job(c,jid))['status']=='completed' and j)
  self.assertEqual(done['result'],'Sent the email to Sarah.')
  second=json.loads(self.log.read_text().splitlines()[1])
  self.assertIn('--resume',second['args']);self.assertEqual(second['args'][second['args'].index('--resume')+1],'sess-1')
  self.assertIn('sarah@example.com',second['prompt'])

 def test_decline_cancels_without_running(self):
  started=assistant_jobs.delegate(c,'Email Sarah I am late.','src-1')
  wait_for(lambda:jobs.get_job(c,started['id'])['status']=='awaiting_approval')
  wait_for(lambda:self.sent.called)
  self.assertEqual(jobs.cancel_job(c,started['id'])['status'],'cancelled')
  self.assertEqual(len(self.log.read_text().splitlines()),1)

 def test_assistant_lane_runs_beside_codex_job(self):
  with patch.object(jobs,'projects',return_value={'p':'/tmp'}):codex=jobs.draft(c,'p','Long build task','x')
  jobs.update(c,codex['id'],status='running')
  started=assistant_jobs.delegate(c,'What is on my calendar?','src-2')
  self.assertIn(started['status'],{'preparing','running','awaiting_approval'})
  wait_for(lambda:jobs.get_job(c,started['id'])['status']=='awaiting_approval' and self.sent.called)

 def test_spoken_announcement_reads_the_answer(self):
  import job_announcements
  job={'project_id':'__assistant__','status':'completed','result':'You have two meetings tomorrow, sir: standup at nine and lunch at one.\n\n- Standup 09:00'}
  self.assertEqual(job_announcements.message(job),'You have two meetings tomorrow, sir: standup at nine and lunch at one.')
  job={**job,'status':'awaiting_approval','result':'I will email Sarah that you are late.'}
  self.assertIn('approval',job_announcements.message(job))

class HandoffGuardTests(unittest.TestCase):
 def setUp(self):
  catalog=patch('project_memory.catalog',return_value=[]);catalog.start();self.addCleanup(catalog.stop)
  self.temp=tempfile.TemporaryDirectory();self.old=c.DATA;c.DATA=Path(self.temp.name);c.CURRENT=None;c.STOP.clear();c.initialize()
  with c.connect() as db:db.execute('INSERT INTO conversations VALUES(?,?,?,?)',('a'*32,'Test',time.time(),time.time()))
 def tearDown(self):c.DATA=self.old;self.temp.cleanup()
 def test_invented_calendar_answer_is_replaced_by_a_handoff(self):
  with patch.object(c,'launch'):item=c.create_turn('a'*32,text="What's on my calendar tomorrow?")
  invented={'role':'assistant','content':'You have a meeting with Mr. Stark at 10.'}
  with patch('fish_voice.key',return_value=None),patch('brain.chat',return_value=invented),\
       patch('assistant_jobs.delegate',return_value={'id':'j'*32,'task':'x','status':'preparing'}) as delegate,patch.object(c.SPEECH,'call',side_effect=RuntimeError('no speech in tests')):
   c.CURRENT=item['id'];c.work(item['id'])
  done=c.turn(item['id'])
  delegate.assert_called_once()
  self.assertNotIn('Stark',done['output_text']);self.assertIn('checking',done['output_text'])
  self.assertTrue(done['timings']['handoff_guard'])

 def test_handoff_plays_a_prerendered_acknowledgement(self):
  import wave
  clip=c.DATA/'ack.wav'
  with wave.open(str(clip),'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\x10\x10'*4800)
  with patch.object(c,'launch'):item=c.create_turn('a'*32,text="What's on my calendar tomorrow?")
  route={'role':'assistant','content':'','tool_calls':[{'id':'1','function':{'name':'delegate_task','arguments':{'task':'Check the calendar'}}}]}
  replies=iter([{'role':'assistant','content':'TOOLS'},route,{'role':'assistant','content':'','tool_calls':[{'id':'2','function':{'name':'speak_response','arguments':{}}}]}])
  made=[]
  with patch('fish_voice.key',return_value='k'),patch('fish_text_stream.available',return_value=True),\
       patch('fish_text_stream.TextSpeech',side_effect=lambda *a,**k:made.append(1) or type('S',(),{'feed':lambda s,t:None,'finish':lambda s,t:None,'close':lambda s:None,'wait':lambda s:{}})()),\
       patch('brain.chat',side_effect=lambda *a,**k:next(replies)),patch('phone.cached',return_value=clip),\
       patch('assistant_jobs.delegate',return_value={'id':'j'*32,'task':'x','status':'preparing'}):
   c.CURRENT=item['id'];c.work(item['id'])
  done=c.turn(item['id'])
  self.assertEqual(done['status'],'complete');self.assertIn(done['output_text'],c.HANDOFF_ACKS)
  self.assertEqual(done['timings']['speech_detail']['mode'],'cached')
  self.assertTrue((c.DATA/'turns'/item['id']/'reply.wav').is_file())

if __name__=='__main__':unittest.main()
