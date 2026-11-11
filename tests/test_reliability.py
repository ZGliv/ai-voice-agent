"""Reliability: tool list never shrinks, mistaken denials retry, failed watches keep the briefing, voicemail."""
import json, tempfile, threading, time, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import companion as c
import assistant_jobs, briefing, codex_jobs, phone, scheduler

GMAIL='mcp__claude_ai_Gmail__search_threads'
KNOWN={'headline':'Quiet day','applications_today':3,'application_companies':['Veeva'],'waiting_on_you':[],'next_events':[],'parl_ai':None,'opener':'Evening. Three applications today. What can I do?'}

class Base(unittest.TestCase):
    def setUp(self):
        catalog=patch('project_memory.catalog',return_value=[]);catalog.start();self.addCleanup(catalog.stop)
        self.temp=tempfile.TemporaryDirectory();self.old=c.DATA;c.DATA=Path(self.temp.name);c.initialize()
    def tearDown(self):c.DATA=self.old;self.temp.cleanup()

class ToolListTests(Base):
    def test_a_partial_tool_list_never_removes_known_connectors(self):
        assistant_jobs.remember_tools(c,['Read',GMAIL,'mcp__claude_ai_Notion__notion-search'])
        assistant_jobs.remember_tools(c,['Read','Glob'])   # a run that started before Gmail connected
        self.assertIn(GMAIL,assistant_jobs.known_tools(c))
        self.assertIn(GMAIL,assistant_jobs.readonly(assistant_jobs.known_tools(c)))

    def test_old_list_format_is_still_read_and_stale_names_expire(self):
        (c.DATA/'assistant-tools.json').write_text(json.dumps(['Read',GMAIL]))
        self.assertIn(GMAIL,assistant_jobs.known_tools(c))
        (c.DATA/'assistant-tools.json').write_text(json.dumps({'seen':{GMAIL:time.time()-assistant_jobs.TOOL_MEMORY-5,'Read':time.time()}}))
        self.assertEqual(assistant_jobs.known_tools(c),['Read'])

    def test_a_read_only_tool_blocked_by_mistake_is_learned_and_the_lookup_retried(self):
        assistant_jobs.remember_tools(c,['Read','mcp__claude_ai_Notion__notion-search'])
        job=codex_jobs.draft(c,'__assistant__','Any new email?','src1');codex_jobs.update(c,job['id'],status='preparing')
        allowed_each=[]
        def worker(core,job,command,prompt,directory,**extra):
            allowed=command[command.index('--allowedTools')+1].split(',');allowed_each.append(GMAIL in allowed)
            if GMAIL in allowed:extra['parse']({'type':'result','result':'You have two new emails.'})
            else:extra['parse']({'type':'result','result':'I could not check.','permission_denials':[{'tool_name':GMAIL,'tool_input':{}}]})
            return SimpleNamespace(returncode=0)
        with patch.object(codex_jobs,'execute_worker',side_effect=worker),patch.object(assistant_jobs,'take',return_value=None),patch.object(assistant_jobs,'notify_done'):
            assistant_jobs.run(c,codex_jobs.get_job(c,job['id']))
        done=codex_jobs.get_job(c,job['id'])
        self.assertEqual(allowed_each,[False,True])
        self.assertEqual((done['status'],done['result']),('completed','You have two new emails.'))

    def test_a_blocked_send_is_never_retried_or_learned(self):
        send='mcp__claude_ai_Gmail__send_message'
        assistant_jobs.remember_tools(c,['Read',GMAIL])
        job=codex_jobs.draft(c,'__assistant__','Email Sam that I am late','src2');codex_jobs.update(c,job['id'],status='preparing')
        runs=[]
        def worker(core,job,command,prompt,directory,**extra):
            runs.append(1);extra['parse']({'type':'result','result':'I will email Sam.','permission_denials':[{'tool_name':send,'tool_input':{'to':'sam'}}]})
            return SimpleNamespace(returncode=0)
        with patch.object(codex_jobs,'execute_worker',side_effect=worker),patch.object(assistant_jobs,'take',return_value=None),patch.object(assistant_jobs,'notify_done'):
            assistant_jobs.run(c,codex_jobs.get_job(c,job['id']))
        self.assertEqual(len(runs),1);self.assertEqual(codex_jobs.get_job(c,job['id'])['status'],'awaiting_approval')
        self.assertNotIn(send,assistant_jobs.readonly(assistant_jobs.known_tools(c)))

    def test_hung_connector_calls_time_out_quickly(self):
        self.assertEqual(assistant_jobs.clean_env()['CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT'],'30000')

class FailedWatchTests(Base):
    def watch(self,result,status='completed'):
        job={'source_turn_id':'schedule:inbox-watch:1','status':status,'result':result,'error':''}
        scheduler.job_done(c,job)

    def test_failed_checks_keep_the_briefing_retry_soon_and_alert_once(self):
        briefing.save(c.DATA,KNOWN)
        sent=[]
        with patch('notify.send',lambda core,text:sent.append(text)),patch('phone.ready',return_value=False):
            before=time.time()
            self.watch('UNAVAILABLE: Gmail and Notion reads were blocked in this session.')
            with c.connect() as db:soon=db.execute("SELECT next_run FROM schedules WHERE id='inbox-watch'").fetchone()[0]
            self.assertLessEqual(soon,before+scheduler.RETRY_AFTER+5)   # tried again in five minutes
            self.assertEqual(sent,[])                                   # one failure is not worth a message
            self.watch("I couldn't check your email or calendar just now, because both were blocked.\nBRIEFING: "+json.dumps({**KNOWN,'applications_today':0,'opener':"Evening. I couldn't reach your email."}))
            self.watch('UNAVAILABLE: still blocked.')
            self.watch('UNAVAILABLE: still blocked.')
            self.assertEqual(len(sent),1);self.assertIn('not been able to read your email',sent[0])   # told once, not every half hour
            self.assertEqual(briefing.load(c.DATA)['data']['applications_today'],3)                   # last good briefing kept
            self.watch('NOTHING\nBRIEFING: '+json.dumps({**KNOWN,'applications_today':4}))
            self.assertIn('read your email again',sent[-1]);self.assertEqual(briefing.load(c.DATA)['data']['applications_today'],4)

    def test_watch_task_asks_for_an_explicit_unavailable_answer(self):
        self.assertIn('UNAVAILABLE:',scheduler.DEFAULTS[1]['task'])

class FakeSocket:
    def __init__(self):self.sent=[];self.closed=False
    def send(self,value):self.sent.append(value)
    def close(self):self.closed=True

class VoicemailTests(unittest.TestCase):
    GREETING="Your call has been forwarded to voice mail. The person you're trying to reach is not available. At the tone, please record your message."
    def call(self,outbound):
        core=SimpleNamespace(DATA=Path('/nonexistent'),CURRENT=None,STOP=threading.Event(),SPECULATIVE={},Problem=c.Problem,
          create_turn=lambda *a,**k:self.turns.append(k.get('text')) or (_ for _ in ()).throw(c.Problem('stop here')))
        call=phone.Call(core,FakeSocket(),'MZ1','conv');call.outbound=outbound;call.opening=Path('news.wav')
        call.play_wav=lambda path,generation=None:self.said.append(str(path));call.say_line=lambda text,generation=None:self.said.append(text)
        return call
    def setUp(self):self.turns=[];self.said=[]

    def test_jarvis_leaves_the_news_on_voicemail_and_hangs_up(self):
        call=self.call(outbound=True)
        with patch('time.sleep'):call.answer(self.GREETING)
        self.assertEqual(self.said,['news.wav','I have sent you the details by text.'])
        self.assertTrue(call.done.is_set());self.assertEqual(self.turns,[])   # the greeting is never treated as Zack

    def test_incoming_calls_and_real_replies_are_never_mistaken_for_voicemail(self):
        call=self.call(outbound=False);call.answer(self.GREETING)
        self.assertEqual(self.turns,[self.GREETING])
        call=self.call(outbound=True);call.answer('Yes, go ahead and draft it.')
        self.assertFalse(call.done.is_set());self.assertNotIn('news.wav',self.said)

if __name__=='__main__':unittest.main()
