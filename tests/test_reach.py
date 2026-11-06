import json, tempfile, threading, time, unittest
from datetime import datetime, timedelta
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode
import companion as c
import companion_tools as tools
import scheduler, phone

class SchedulerTests(unittest.TestCase):
 def setUp(self):
  catalog=patch('project_memory.catalog',return_value=[]);catalog.start();self.addCleanup(catalog.stop)
  self.temp=tempfile.TemporaryDirectory();self.old=c.DATA;c.DATA=Path(self.temp.name);c.CURRENT=None;c.initialize()
  with c.connect() as db:db.execute('INSERT INTO conversations VALUES(?,?,?,?)',('a'*32,'Test',time.time(),time.time()))
 def tearDown(self):c.DATA=self.old;self.temp.cleanup()

 def test_defaults_are_seeded_once(self):
  c.initialize()
  ids=[s['id'] for s in scheduler.listing(c)]
  self.assertEqual(sorted(ids),['inbox-watch','morning-briefing'])

 def test_next_run_rules(self):
  base=datetime(2026,11,5,8,15).astimezone().timestamp()
  daily=datetime.fromtimestamp(scheduler.next_run({'repeat':'daily','at':'07:30'},base))
  self.assertEqual((daily.day,daily.hour,daily.minute),(6,7,30))
  hourly=datetime.fromtimestamp(scheduler.next_run({'repeat':'hourly','window':'09:00-21:00'},base))
  self.assertEqual((hourly.day,hourly.hour),(5,9))
  late=datetime(2026,11,5,21,30).astimezone().timestamp()
  self.assertEqual(datetime.fromtimestamp(scheduler.next_run({'repeat':'hourly','window':'09:00-21:00'},late)).hour,9)

 def test_voice_reminder_delivers_once(self):
  with patch.object(c,'launch'):item=c.create_turn('a'*32,text='Remind me in a minute to stretch.')
  when=(datetime.now()+timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M')
  made=tools.execute(c,item,'schedule_task',{'kind':'reminder','label':'Stretch','task':'Time to stretch, sir.','repeat':'once','at':when,'deliver':'telegram'})
  with patch('notify.send',return_value=True) as sent:
   scheduler.tick(c,time.time()+120);scheduler.tick(c,time.time()+240)
  self.assertEqual(sent.call_count,1);self.assertIn('Time to stretch',sent.call_args[0][1])
  self.assertFalse([s for s in scheduler.listing(c) if s['id']==made['id']][0]['enabled'])

 def test_past_time_is_rejected(self):
  with self.assertRaises(c.Problem):scheduler.create(c,'reminder','Old','Too late','once','2020-01-01T09:00')

 def test_watch_is_silent_when_nothing_and_calls_when_urgent(self):
  job={'source_turn_id':'schedule:inbox-watch:1','status':'completed','result':'NOTHING'}
  with patch('notify.send',return_value=True) as sent,patch('phone.ready',return_value=True),patch('phone.call') as call:
   scheduler.job_done(c,job);sent.assert_not_called();call.assert_not_called()
   scheduler.job_done(c,{**job,'result':'URGENT: Your 3pm with Dana moved to 2pm.'})
  call.assert_called_once();self.assertNotIn('URGENT:',call.call_args[0][1])
  self.assertIn('URGENT',sent.call_args[0][1])

 def test_scheduled_task_waits_while_assistant_busy(self):
  with c.connect() as db:db.execute('UPDATE schedules SET next_run=? WHERE id=?',(time.time()-5,'morning-briefing'))
  with patch('assistant_jobs.delegate',side_effect=c.Problem('busy',409)):scheduler.tick(c)
  row=[s for s in scheduler.listing(c) if s['id']=='morning-briefing'][0]
  with c.connect() as db:self.assertLess(db.execute("SELECT next_run FROM schedules WHERE id='morning-briefing'").fetchone()[0],time.time())

 def test_change_schedule_requires_listing(self):
  with patch.object(c,'launch'):item=c.create_turn('a'*32,text='Call me with my morning briefing.')
  with self.assertRaises(c.Problem):tools.execute(c,item,'change_schedule',{'schedule_id':'morning-briefing','action':'update','deliver':'call'})
  tools.execute(c,item,'list_schedules',{})
  self.assertEqual(tools.execute(c,item,'change_schedule',{'schedule_id':'morning-briefing','action':'update','deliver':'call'})['deliver'],'call')

class PhoneTests(unittest.TestCase):
 def setUp(self):
  catalog=patch('project_memory.catalog',return_value=[]);catalog.start();self.addCleanup(catalog.stop)
  self.temp=tempfile.TemporaryDirectory();self.old=c.DATA;c.DATA=Path(self.temp.name);c.CURRENT=None;c.initialize()
  self.base='https://jarvis.example.ts.net:10000'
  (c.DATA/'twilio.json').write_text(json.dumps({'account_sid':'AC1','auth_token':'tok','from_number':'+15550001111','my_number':'+1 (555) 222-3333','public_url':self.base}))
  voice=patch('fish_voice.key',return_value=None);voice.start();self.addCleanup(voice.stop)
  with patch.object(phone,'PORT',0):self.server=phone.start(c)
  self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
 def tearDown(self):c.DATA=self.old;self.temp.cleanup()
 def post(self,path,params,sign=True):
  conn=HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
  headers={'Content-Type':'application/x-www-form-urlencoded'}
  if sign:headers['X-Twilio-Signature']=phone.signature('tok',self.base+path,params)
  conn.request('POST',path,urlencode(params),headers);response=conn.getresponse()
  return response.status,response.read().decode()

 def test_unsigned_requests_are_refused(self):
  self.assertEqual(self.post('/twilio/voice',{'CallSid':'CA1','From':'+15552223333'},sign=False)[0],403)

 def test_strangers_are_rejected(self):
  self.assertIn('<Reject',self.post('/twilio/voice',{'CallSid':'CA1','From':'+15559999999','Direction':'inbound'})[1])

 def test_full_spoken_turn_over_the_phone(self):
  status,body=self.post('/twilio/voice',{'CallSid':'CA2','From':'+15552223333','Direction':'inbound'})
  self.assertEqual(status,200);self.assertIn('<Gather input="speech"',body);self.assertIn(self.base+'/twilio/heard',body)
  created=[]
  def fake_create(conversation,text):
   created.append(text);return {'id':'b'*32}
  with patch.object(c,'create_turn',side_effect=fake_create):
   body=self.post('/twilio/heard',{'CallSid':'CA2','SpeechResult':'What is on my calendar?'})[1]
  self.assertEqual(created,['What is on my calendar?']);self.assertIn('/twilio/wait?turn='+'b'*32,body)
  conversation=phone.CALLS['CA2']['conversation']
  pending={'conversation_id':conversation,'status':'thinking','has_audio':False}
  with patch.object(c,'turn',return_value=pending):
   self.assertIn('<Redirect',self.post('/twilio/wait?turn='+'b'*32+'&n=0',{'CallSid':'CA2'})[1])
  reply=c.DATA/'turns'/('b'*32);reply.mkdir(parents=True)
  import subprocess
  subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=0.3','-ar','24000',str(reply/'reply.wav')],check=True)
  with patch.object(c,'turn',return_value={**pending,'status':'complete','has_audio':True}):
   body=self.post('/twilio/wait?turn='+'b'*32+'&n=1',{'CallSid':'CA2'})[1]
  self.assertIn('<Play>'+self.base+'/twilio/audio/',body)
  token=body.split('/twilio/audio/')[1].split('.wav')[0]
  conn=HTTPConnection('127.0.0.1',self.server.server_port,timeout=5);conn.request('GET','/twilio/audio/'+token+'.wav')
  audio=conn.getresponse();self.assertEqual(audio.status,200);self.assertEqual(audio.read()[:4],b'RIFF')

 def test_goodbye_hangs_up(self):
  self.post('/twilio/voice',{'CallSid':'CA3','From':'+15552223333','Direction':'inbound'})
  self.assertIn('<Hangup/>',self.post('/twilio/heard',{'CallSid':'CA3','SpeechResult':'Goodbye.'})[1])

 def test_signature_matches_twilio_reference_example(self):
  # Example from Twilio's request-validation documentation.
  params={'CallSid':'CA1234567890ABCDE','Caller':'+12349013030','Digits':'1234','From':'+12349013030','To':'+18005551212'}
  self.assertEqual(phone.signature('12345','https://mycompany.com/myapp.php?foo=1&bar=2',params),'0/KCTR6DLpKmkAf8muzZqo1nDgQ=')

if __name__=='__main__':unittest.main()
