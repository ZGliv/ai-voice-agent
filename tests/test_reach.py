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

def ws_connect(port,path='/twilio/media'):
 import base64,os,socket as net
 sock=net.create_connection(('127.0.0.1',port),timeout=5)
 key=base64.b64encode(os.urandom(16)).decode()
 sock.sendall(f'GET {path} HTTP/1.1\r\nHost: x\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'.encode())
 reader=sock.makefile('rb');status=reader.readline()
 while reader.readline() not in (b'\r\n',b''):pass
 return sock,reader,status

def ws_send(sock,value):
 import os,struct
 data=json.dumps(value).encode();mask=os.urandom(4)
 header=struct.pack('!BB',0x81,0x80|len(data)) if len(data)<126 else struct.pack('!BBH',0x81,0x80|126,len(data))
 sock.sendall(header+mask+bytes(b^mask[i%4] for i,b in enumerate(data)))

class PhoneTests(unittest.TestCase):
 def setUp(self):
  catalog=patch('project_memory.catalog',return_value=[]);catalog.start();self.addCleanup(catalog.stop)
  self.temp=tempfile.TemporaryDirectory();self.old=c.DATA;c.DATA=Path(self.temp.name);c.CURRENT=None;c.STOP.clear();c.initialize()
  self.base='https://jarvis.example.ts.net:10000'
  (c.DATA/'twilio.json').write_text(json.dumps({'account_sid':'AC1','auth_token':'tok','from_number':'+15550001111','my_number':'+1 (555) 222-3333','public_url':self.base}))
  voice=patch('fish_voice.key',return_value=None);voice.start();self.addCleanup(voice.stop)
  with patch.object(phone,'PORT',0):self.server=phone.start(c)
  self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
 def tearDown(self):
  phone.LIVE.clear();phone.PENDING.clear();c.DATA=self.old;self.temp.cleanup()
 def post(self,path,params,sign=True,url=None):
  conn=HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
  headers={'Content-Type':'application/x-www-form-urlencoded'}
  if sign:headers['X-Twilio-Signature']=phone.signature('tok',url or self.base+path,params)
  conn.request('POST',path,urlencode(params),headers);response=conn.getresponse()
  try:return response.status,response.read().decode()
  finally:conn.close()
 def token(self,body):
  return body.split('name="token" value="')[1].split('"')[0]

 def test_unsigned_requests_are_refused(self):
  self.assertEqual(self.post('/twilio/voice',{'CallSid':'CA1','From':'+15552223333'},sign=False)[0],403)

 def test_strangers_are_rejected(self):
  self.assertIn('<Reject',self.post('/twilio/voice',{'CallSid':'CA1','From':'+15559999999'})[1])

 def test_inbound_call_connects_a_media_stream(self):
  status,body=self.post('/twilio/voice',{'CallSid':'CA2','From':'+15552223333'})
  self.assertEqual(status,200)
  self.assertIn('<Connect><Stream url="wss://jarvis.example.ts.net:10000/twilio/media">',body)
  self.assertIn(self.token(body),phone.PENDING)

 def test_signature_signed_without_port_is_accepted(self):
  status,body=self.post('/twilio/voice',{'CallSid':'CA4','From':'+15552223333'},url='https://jarvis.example.ts.net/twilio/voice')
  self.assertIn('<Connect>',body)
  self.assertFalse(phone.valid('tok',self.base+'/twilio/voice',{'CallSid':'CA4'},'forged'))

 def test_stream_without_a_valid_token_is_closed(self):
  sock,reader,status=ws_connect(self.server.server_port)
  self.assertIn(b'101',status)
  ws_send(sock,{'event':'start','streamSid':'MZ1','start':{'streamSid':'MZ1','customParameters':{'token':'nope'}}})
  from phone_media import Socket,Closed
  with self.assertRaises(Closed):Socket(reader,sock.makefile('wb')).receive()
  self.assertFalse(phone.LIVE);sock.close()

 def test_spoken_turn_streams_reply_audio_back(self):
  import subprocess,threading
  from phone_media import Socket,Closed,ENCODE
  body=self.post('/twilio/voice',{'CallSid':'CA5','From':'+15552223333'})[1]
  heard=[]
  class Ear:
   def call(self,job,stop,timeout):
    heard.append(job['session'])
    return {'text':'What is on my calendar?','end':len(heard)==3}
  reply_id='b'*32
  def fake_create(conversation,text):
   folder=c.DATA/'turns'/reply_id;folder.mkdir(parents=True,exist_ok=True)
   subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','sine=frequency=440:duration=0.5','-ar','24000','-ac','1',str(folder/'reply.wav')],check=True)
   created.append(text);return {'id':reply_id}
  created=[]
  with patch.object(c.STREAMING,'worker',Ear()),patch.object(c,'create_turn',side_effect=fake_create),\
       patch.object(c,'turn',return_value={'status':'complete','has_audio':True}):
   sock,reader,status=ws_connect(self.server.server_port)
   ws_send(sock,{'event':'start','streamSid':'MZ5','start':{'streamSid':'MZ5','customParameters':{'token':self.token(body)}}})
   silence=__import__('base64').b64encode(bytes([ENCODE[0]])*160).decode()
   for _ in range(40):ws_send(sock,{'event':'media','streamSid':'MZ5','media':{'payload':silence}})
   incoming=Socket(reader,sock.makefile('wb'));audio=0;marks=[]
   deadline=time.time()+10
   while time.time()<deadline and not marks:
    message=incoming.receive()
    if message['event']=='media':audio+=len(__import__('base64').b64decode(message['media']['payload']))
    if message['event']=='mark':marks.append(message['mark']['name'])
   self.assertEqual(created,['What is on my calendar?'])
   self.assertGreaterEqual(audio,3900)   # ~0.5 s of 8 kHz mu-law
   self.assertTrue(phone.LIVE)
   ws_send(sock,{'event':'stop','streamSid':'MZ5'});sock.close()

 def test_finished_task_rings_back_when_no_call_is_live(self):
  import assistant_jobs
  conversation=phone.new_conversation(c,'Phone call')
  with c.connect() as db:db.execute("INSERT INTO turns(id,conversation_id,source,status,input_text,created,updated) VALUES(?,?,?,?,?,?,?)",('t'*32,conversation,'text','complete','How many jobs did I apply to?',time.time(),time.time()))
  job={'project_id':'__assistant__','status':'completed','result':'You applied to three jobs today, sir.','source_turn_id':'t'*32,'task':'x'}
  with patch('phone.call') as ring,patch('notify.send',return_value=True):assistant_jobs.notify_done(c,job)
  ring.assert_called_once();self.assertEqual(ring.call_args[0][1],'You applied to three jobs today, sir.');self.assertEqual(ring.call_args[0][2],conversation)
  live=type('Live',(),{'announce':lambda self,text:spoken.append(text)})();spoken=[]
  phone.LIVE[conversation]=live
  with patch('phone.call') as ring,patch('notify.send',return_value=True):assistant_jobs.notify_done(c,job)
  ring.assert_not_called();self.assertEqual(spoken,['You applied to three jobs today, sir.'])

 def test_goodbye_detection(self):
  for text in ['Goodbye.','Okay, bye now.','Thanks, bye Jarvis.']:self.assertTrue(phone.GOODBYE.fullmatch(text))
  self.assertFalse(phone.GOODBYE.fullmatch('Bye the way, check my email.'))

 def test_signature_matches_twilio_reference_example(self):
  # Example from Twilio's request-validation documentation.
  params={'CallSid':'CA1234567890ABCDE','Caller':'+12349013030','Digits':'1234','From':'+12349013030','To':'+18005551212'}
  self.assertEqual(phone.signature('12345','https://mycompany.com/myapp.php?foo=1&bar=2',params),'0/KCTR6DLpKmkAf8muzZqo1nDgQ=')

if __name__=='__main__':unittest.main()
