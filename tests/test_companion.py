import tempfile, unittest, json, time, threading, sys, io, wave
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import companion as c

class CompanionTests(unittest.TestCase):
    def setUp(self):
        catalog_patch=patch('project_memory.catalog',return_value=[]);catalog_patch.start();self.addCleanup(catalog_patch.stop)
        self.tmp=tempfile.TemporaryDirectory(); self.original=c.DATA;c.DATA=Path(self.tmp.name);c.CURRENT=None;c.STOP.clear();c.initialize()
        with c.connect() as db: db.execute('INSERT INTO conversations VALUES(?,?,?,?)',('a'*32,'New conversation',time.time(),time.time()))
    def tearDown(self):
        c.STOP.set();c.DATA=self.original;self.tmp.cleanup()
    def make(self,**kwargs):
        with patch.object(c,'launch'):return c.create_turn('a'*32,**kwargs)
    def test_persisted_text_and_title(self):
        t=self.make(text='Keep this thought')
        self.assertEqual(c.turn(t['id'])['input_text'],'Keep this thought')
        with c.connect() as db:self.assertEqual(db.execute('SELECT title FROM conversations').fetchone()[0],'Keep this thought')
    def test_restart_marks_pending_interrupted(self):
        t=self.make(text='An interrupted thought');c.initialize()
        self.assertEqual(c.turn(t['id'])['status'],'interrupted')
    def test_lost_acknowledgement_reuses_turn_even_while_busy_or_after_restart(self):
        with patch.object(c,'launch') as launch:
            first=c.create_turn('a'*32,audio=b'voice',request_id='b'*32)
            c.CURRENT=first['id']
            self.assertEqual(c.create_turn('a'*32,audio=b'voice',request_id='b'*32)['id'],first['id'])
            c.CURRENT=None;c.initialize()
            self.assertEqual(c.create_turn('a'*32,audio=b'voice',request_id='b'*32)['id'],first['id'])
            launch.assert_called_once()
        with c.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM turns').fetchone()[0],1)

    def test_request_identity_rejects_different_input(self):
        self.make(text='Original',request_id='b'*32)
        with self.assertRaises(c.Problem):self.make(text='Changed',request_id='b'*32)
        with self.assertRaises(c.Problem):self.make(audio=b'Original',request_id='b'*32)
        with self.assertRaises(c.Problem):self.make(text='Original',request_id='invalid')

    def test_busy_prevents_second_turn(self):
        c.CURRENT='busy'
        with self.assertRaises(c.Problem) as raised:self.make(text='Second')
        self.assertEqual(raised.exception.status,409)
    def test_model_failure_is_not_success(self):
        t=self.make(text='A failed thought')
        with patch.object(c.local_runtime,'chat',side_effect=c.Problem('Ollama unavailable',503)):c.work(t['id'])
        saved=c.turn(t['id']);self.assertEqual(saved['status'],'failed');self.assertFalse(saved['output_text']);self.assertFalse(saved['has_audio'])
    def test_cancel_terminates_real_child(self):
        timer=threading.Timer(.25,c.STOP.set);timer.start();started=time.monotonic()
        with self.assertRaises(c.Cancelled):c.run_process([sys.executable,'-c','import time; time.sleep(20)'])
        timer.join();self.assertLess(time.monotonic()-started,3);self.assertIsNone(c.PROCESS)
    def test_cancel_does_not_publish_audio(self):
        t=self.make(text='A cancelled thought')
        with patch.object(c.local_runtime,'chat',side_effect=c.Cancelled()):c.work(t['id'])
        self.assertEqual(c.turn(t['id'])['status'],'cancelled');self.assertFalse(c.turn(t['id'])['has_audio'])
    def test_speech_cleanup_preserves_history_for_both_providers(self):
        raw='Next step:\n- **Parlay**: Test on a phone.'
        for provider in ['fish','piper']:
            t=self.make(text='Check in');c.update(t['id'],output_text=raw,status='failed');spoken=[]
            def write(text,destination):
                spoken.append(text)
                with wave.open(str(destination),'wb') as wav:
                    wav.setparams((1,2,16000,0,'NONE','not compressed'));wav.writeframes(b'\x01\x01'*8000)
            def fish(text,destination,secret,stop,**kwargs):write(text,destination)
            def piper(job,stop,timeout):write(job['text'],job['destination'])
            with patch.object(c.fish_voice,'key',return_value='test-key' if provider=='fish' else None),patch.object(c.fish_voice,'synthesize',side_effect=fish),patch.object(c.SPEECH,'call',side_effect=piper),patch.object(c.Path,'is_file',return_value=True):c.work(t['id'])
            self.assertEqual(spoken,['Next step:\nParlay: Test on a phone.'])
            self.assertEqual(c.turn(t['id'])['output_text'],raw)
            self.assertEqual(c.turn(t['id'])['status'],'complete')

    def test_retry_preserves_completed_language_step(self):
        t=self.make(text='Question');c.update(t['id'],output_text='A previously saved answer',status='failed')
        calls=[]
        def synth(job,stop,timeout):
            calls.append(job)
            with wave.open(job['destination'],'wb') as wav:wav.setparams((1,2,16000,0,'NONE','not compressed'));wav.writeframes(b'\x01\x01'*8000)
        with patch.object(c.SPEECH,'call',side_effect=synth),patch.object(c.Path,'is_file',return_value=True):c.work(t['id'])
        self.assertEqual(len(calls),1);self.assertEqual(calls[0]['text'],'A previously saved answer');self.assertEqual(c.turn(t['id'])['status'],'complete')
    def test_failed_upload_keeps_source_for_retry(self):
        t=self.make(audio=b'invalid audio')
        with patch.object(c,'run_process',side_effect=c.Problem('Invalid recording')):c.work(t['id'])
        self.assertEqual(c.turn(t['id'])['status'],'failed');self.assertEqual((c.DATA/'turns'/t['id']/'input.audio').read_bytes(),b'invalid audio')
    def test_unheard_audio_never_reaches_reasoning_and_remains_retryable(self):
        t=self.make(audio=b'noise fixture')
        def normalize(*args):
            with wave.open(str(c.DATA/'turns'/t['id']/'input.wav'),'wb') as wav:
                wav.setparams((1,2,16000,0,'NONE','not compressed'));wav.writeframes(b'\x00\x10'*16000)
        with patch.object(c,'run_process',side_effect=normalize),patch.object(c,'transcription_ready',return_value=True),patch.object(c.TRANSCRIBER,'call',return_value={'text':'','segments':[]}),patch.object(c.local_runtime,'chat') as reasoning:
            c.work(t['id'])
        reasoning.assert_not_called();self.assertEqual(c.turn(t['id'])['status'],'unheard')
        detail=c.turn(t['id'])['timings']['transcription_detail']
        self.assertEqual(detail['audio_seconds'],1);self.assertGreaterEqual(detail['audio_preparation'],0);self.assertGreaterEqual(detail['recognition'],0)
        self.assertTrue((c.DATA/'turns'/t['id']/'input.audio').exists());self.assertFalse((c.DATA/'turns'/t['id']/'input.wav').exists())

    def test_action_limit_still_summarizes_final_results_without_more_actions(self):
        t=self.make(text='Save a decision, update a step, and start work')
        calls=[];outcomes=[{'saved':'Use cyan'},{'updated':'Test on phone'},{'status':'running'},{'error':'Requested extra action unavailable'}]
        def chat(url,payload,stop,partial):
            calls.append(payload.copy())
            if len(calls)<=4:return {'role':'assistant','content':'','tool_calls':[{'function':{'name':'fixture_action','arguments':{}}}]}
            return {'role':'assistant','content':'Saved the decision and updated the step. The job is running; the extra action was unavailable.'}
        def synth(job,stop,timeout):
            with wave.open(job['destination'],'wb') as wav:
                wav.setparams((1,2,16000,0,'NONE','not compressed'));wav.writeframes(b'\x01\x01'*8000)
        with patch.object(c.local_runtime,'chat',side_effect=chat),patch.object(c.companion_tools,'execute',side_effect=outcomes) as execute,patch.object(c.fish_voice,'key',return_value=None),patch.object(c.SPEECH,'call',side_effect=synth),patch.object(c.Path,'is_file',return_value=True):
            c.work(t['id'])
        self.assertEqual(execute.call_count,4);self.assertEqual(len(calls),5);self.assertNotIn('tools',calls[-1])
        self.assertEqual([json.loads(m['content']) for m in calls[-1]['messages'] if m['role']=='tool'],outcomes)
        saved=c.turn(t['id']);self.assertEqual(saved['status'],'complete');self.assertIn('extra action was unavailable',saved['output_text']);self.assertTrue(saved['has_audio'])

    def test_incremental_speech_waits_for_tool_results_and_uses_speech_only_pass(self):
        t=self.make(text='Save the cyan decision and explain it')
        events=[];calls=[]
        def chat(url,payload,stop,partial):
            calls.append(payload)
            if len(calls)==1:return {'role':'assistant','content':'Premature claim','tool_calls':[{'function':{'name':'save_memory','arguments':{}}}]}
            if len(calls)==2:return {'role':'assistant','content':'READY'}
            partial('Saved cyan. ');partial('Saved cyan. It keeps the visual identity consistent.')
            return {'role':'assistant','content':'Saved cyan. It keeps the visual identity consistent.'}
        def execute(*args):events.append('tool-confirmed');return {'saved':'cyan'}
        class Speech:
            def __init__(self,directory,*args):self.directory=directory;events.append('speech-start')
            def feed(self,text):events.append(text)
            def finish(self,text):
                with wave.open(str(self.directory/'reply.pending.wav'),'wb') as wav:
                    wav.setparams((1,2,24000,0,'NONE','not compressed'));wav.writeframes(b'\x01\x01'*2400)
            def wait(self):return {'first_audio':.1,'text_complete':.2,'total':.3}
            def close(self):pass
        with patch.object(c.fish_voice,'key',return_value='fake-secret'),patch.object(c.fish_text_stream,'available',return_value=True),patch.object(c.fish_text_stream,'TextSpeech',Speech),patch.object(c.local_runtime,'chat',side_effect=chat),patch.object(c.companion_tools,'execute',side_effect=execute) as action:
            c.work(t['id'])
        self.assertEqual(action.call_count,1);self.assertEqual(events[:2],['tool-confirmed','speech-start'])
        self.assertNotIn('Premature claim',events);self.assertNotIn('tools',calls[-1]);self.assertEqual(c.turn(t['id'])['status'],'complete')

    def test_conversation_stream_never_executes_unexpected_final_tool(self):
        t=self.make(text='Tell me a joke')
        calls=[]
        def chat(url,payload,stop,partial):
            calls.append(payload)
            return {'content':'','tool_calls':[{'function':{'name':'save_memory','arguments':{}}}]}
        from unittest.mock import MagicMock
        speech=MagicMock()
        with patch.object(c.fish_voice,'key',return_value='fake'),patch.object(c.fish_text_stream,'available',return_value=True),patch.object(c.fish_text_stream,'TextSpeech',return_value=speech),patch.object(c.local_runtime,'chat',side_effect=chat),patch.object(c.companion_tools,'execute') as action:
            c.work(t['id'])
        action.assert_not_called();speech.feed.assert_not_called()
        self.assertEqual(len(calls),1);self.assertNotIn('tools',calls[-1])
        self.assertEqual(c.turn(t['id'])['status'],'failed')
        self.assertFalse(c.turn(t['id'])['has_audio'])

    def test_casual_response_streams_in_one_model_call_without_protocol_audio(self):
        t=self.make(text="Jarvis, what's up?");heard=[]
        def chat(url,payload,stop,partial):
            partial('S');partial('SAY  ');partial('SAY  \nHello there. ')
            return {'content':'SAY  \nHello there. How can I help?'}
        class Speech:
            def __init__(self,directory,*args):self.directory=directory
            def feed(self,text):heard.append(text)
            def finish(self,text):
                with wave.open(str(self.directory/'reply.pending.wav'),'wb') as wav:
                    wav.setparams((1,2,24000,0,'NONE','not compressed'));wav.writeframes(b'\x01\x01'*2400)
            def wait(self):return {'first_audio':.1,'total':.2}
            def close(self):pass
        with patch.object(c.fish_voice,'key',return_value='fake'),patch.object(c.fish_text_stream,'available',return_value=True),patch.object(c.fish_text_stream,'TextSpeech',Speech),patch.object(c.local_runtime,'chat',side_effect=chat) as model,patch.object(c.companion_tools,'execute') as action:
            c.work(t['id'])
        model.assert_called_once();action.assert_not_called()
        self.assertEqual(heard,['Sir, Hello there. ','Sir, Hello there. How can I help?'])
        self.assertEqual(c.turn(t['id'])['output_text'],'Sir, Hello there. How can I help?')
        self.assertEqual(c.turn(t['id'])['status'],'complete')

    def test_action_and_memory_requests_bypass_conversational_shortcut(self):
        for text in ['Build me a website','What did we decide on Project Room?','Save this decision','Stop listening','What is my next step?','Open the last site','Check the job','What did we agree?']:
            self.assertTrue(c.needs_tools(text),text)
        for text in ["Jarvis, what's up?",'What is 2+2?','Explain rainbows','Tell me a joke']:
            self.assertFalse(c.needs_tools(text),text)

    def test_adopted_preparation_publishes_only_after_final_turn_and_never_runs_tools(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        t=self.make(audio=b'final audio');directory=c.DATA/'turns'/t['id']
        ready=threading.Event();ready.set()
        draft=SimpleNamespace(text='What is two plus two?',answer='Four.',recognized=ready,done=ready,error=None,timings={'recognition':.4},stop=threading.Event(),thread=Mock())
        with wave.open(str(directory/'reply.pending.wav'),'wb') as wav:
            wav.setparams((1,2,24000,0,'NONE','not compressed'));wav.writeframes(b'\x01\x01'*2400)
        c.DRAFTS.adopted[t['id']]=draft
        with patch.object(c.local_runtime,'chat') as model,patch.object(c.companion_tools,'execute') as tools,patch.object(c.fish_voice,'key',return_value='fake'):
            c.work(t['id'])
        model.assert_not_called();tools.assert_not_called()
        saved=c.turn(t['id']);self.assertEqual(saved['status'],'complete');self.assertEqual(saved['output_text'],'Four.');self.assertTrue(saved['has_audio'])

if __name__=='__main__':unittest.main()

class RoutingRegressionTests(unittest.TestCase):
 def test_explaining_a_pause_does_not_request_action_tools(self):
  self.assertFalse(c.needs_tools('Explain how semantic turn detection distinguishes a pause from the end of a sentence.'))
  self.assertTrue(c.needs_tools('Pause'))
  self.assertTrue(c.needs_tools('Please pause listening'))
  self.assertTrue(c.needs_tools('Pause the conversation'))

 def test_spoken_address_is_present_and_stream_prefix_is_stable(self):
  self.assertEqual(c.addressed_reply('S'),'')
  self.assertEqual(c.addressed_reply('Sir,'),'')
  self.assertEqual(c.addressed_reply('Sir, hello'),'Sir, hello')
  self.assertEqual(c.addressed_reply('Hello'),'Sir, Hello')
  self.assertTrue(c.addressed_reply('Hello there').startswith(c.addressed_reply('Hello')))
