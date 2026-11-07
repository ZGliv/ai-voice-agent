"""Deepgram phone hearing, Stripe sale calls, progress lines, parallel lookups, the 30-minute watch."""
import base64, hashlib, hmac, json, queue, socket, tempfile, threading, time, unittest, uuid
from datetime import datetime
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
import companion as c
import codex_jobs, assistant_jobs, scheduler, phone, phone_media

def stripe_header(secret,body,stamp=None):
 stamp=str(int(stamp or time.time()))
 return f't={stamp},v1='+hmac.new(secret.encode(),stamp.encode()+b'.'+body,hashlib.sha256).hexdigest()

class FakeDeepgram(BaseHTTPRequestHandler):
 """Accepts one stream, records audio frames, and ends a turn after enough audio."""
 protocol_version='HTTP/1.1'
 frames=[];auth=[];paths=[]
 def log_message(self,*a):pass
 def do_GET(self):
  FakeDeepgram.auth.append(self.headers.get('Authorization'));FakeDeepgram.paths.append(self.path)
  self.send_response(101);self.send_header('Upgrade','websocket');self.send_header('Connection','Upgrade')
  self.send_header('Sec-WebSocket-Accept',phone_media.accept_key(self.headers['Sec-WebSocket-Key']));self.end_headers()
  self.close_connection=True
  ws=phone_media.Socket(self.rfile,self.wfile)
  ws.send({'type':'Connected'})
  # Read raw frames (binary audio is not JSON, so read frame headers directly).
  try:
   while True:
    first,second=ws._read(2);size=second&0x7F
    if size==126:size=int.from_bytes(ws._read(2),'big')
    mask=ws._read(4);data=bytes(b^mask[i%4] for i,b in enumerate(ws._read(size)))
    if first&0x0F==2:
     FakeDeepgram.frames.append(data)
     if len(FakeDeepgram.frames)==2:ws.send({'type':'TurnInfo','event':'Update','transcript':'what is'})
     if len(FakeDeepgram.frames)==4:ws.send({'type':'TurnInfo','event':'EndOfTurn','transcript':'What is on my calendar?','trigger':'model'})
    elif first&0x0F==1 and b'CloseStream' in data:break
    elif first&0x0F==8:break
  except phone_media.Closed:pass
  ws.close()

class FakeSocket:
 def send(self,value):pass

class Core:
 DATA=None

class HearingTests(unittest.TestCase):
 def setUp(self):
  FakeDeepgram.frames=[];FakeDeepgram.auth=[];FakeDeepgram.paths=[]
  self.server=ThreadingHTTPServer(('127.0.0.1',0),FakeDeepgram)
  threading.Thread(target=self.server.serve_forever,daemon=True).start()
  self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  Core.DATA=Path(self.temp.name)

 def test_flux_hears_a_turn_from_raw_phone_audio(self):
  call=phone.Call(Core,FakeSocket(),'MZ1','conv')
  for _ in range(4):call.audio.put(bytes([0xFF])*phone.FLUX_CHUNK)
  with patch.object(phone,'FLUX',f'ws://127.0.0.1:{self.server.server_port}/v2/listen'):
   worker=threading.Thread(target=call.listen_flux,args=('dg-key',),daemon=True);worker.start()
   kind,text=call.pending.get(timeout=5)
   call.done.set();worker.join(5)
  self.assertEqual((kind,text),('answer','What is on my calendar?'))
  self.assertEqual(FakeDeepgram.auth,['Token dg-key'])
  self.assertTrue(all(len(f)==phone.FLUX_CHUNK for f in FakeDeepgram.frames[:4]))
  self.assertIn('keyterm=Jarvis',FakeDeepgram.paths[0])   # so Jarvis is not heard as Travis

 def test_unreachable_deepgram_falls_back_to_local_recognition(self):
  (Core.DATA/'deepgram-api-key').write_text('dg-key')
  call=phone.Call(Core,FakeSocket(),'MZ1','conv')
  used=[]
  with patch.object(phone,'FLUX','ws://127.0.0.1:9/v2/listen'),patch.object(phone.Call,'listen_local',lambda self:used.append('local')):
   call.listen()
  self.assertEqual(used,['local'])

class ProgressTests(unittest.TestCase):
 def setUp(self):
  self.call=phone.Call(Core,FakeSocket(),'MZ1','conv');phone.LIVE['conv']=self.call
  self.addCleanup(phone.LIVE.clear)
 def test_progress_line_waits_for_a_quiet_moment_and_never_repeats(self):
  self.call.last_spoke=time.monotonic()
  phone.progress(Core,'conv','mcp__claude_ai_Gmail__search_threads')
  self.assertTrue(self.call.lines.empty())   # Jarvis just spoke: stay quiet
  self.call.last_spoke-=10
  phone.progress(Core,'conv','mcp__claude_ai_Gmail__search_threads')
  self.assertEqual(self.call.lines.get_nowait(),'Going through your inbox now.')
  phone.progress(Core,'conv','mcp__claude_ai_Gmail__get_thread')
  self.assertTrue(self.call.lines.empty())   # same line twice in one answer is noise
  phone.progress(Core,'conv','mcp__claude_ai_Notion__notion-search')
  self.assertEqual(self.call.lines.get_nowait(),'Checking your Notion.')
 def test_unknown_tools_and_other_calls_say_nothing(self):
  self.call.last_spoke-=10
  phone.progress(Core,'conv','TodoWrite')
  phone.progress(Core,'other','mcp__claude_ai_Gmail__search_threads')
  self.assertTrue(self.call.lines.empty())

class ConversationTests(unittest.TestCase):
 def setUp(self):
  self.call=phone.Call(Core,FakeSocket(),'MZ1','conv')
 def test_fragments_heard_while_busy_become_one_question(self):
  heard=[]
  self.call.answer=lambda text:(heard.append(text),self.call.done.set())
  self.call.pending.put(('answer','What are'));self.call.pending.put(('answer','you doing right now?'))
  self.call.worker()
  self.assertEqual(heard,['What are you doing right now?'])
 def test_a_quick_thanks_does_not_cut_jarvis_off_but_stop_does(self):
  stopped=[]
  self.call.speaking=lambda:True;self.call.interrupt=lambda:stopped.append(True)
  self.call.heard_words('Thanks Jarvis','');self.assertEqual(stopped,[True])   # his name means he wants in
  stopped.clear();self.call.heard_words('Okay thanks','');self.assertEqual(stopped,[])
  self.call.heard_words('Wait','');self.assertEqual(stopped,[True])
  stopped.clear();self.call.heard_words('actually make it Tuesday','');self.assertEqual(stopped,[True])
 def test_jarvis_hangs_up_after_saying_goodbye(self):
  class Turns:
   CURRENT=None;STOP=threading.Event();DATA=None
   reply=''
   @classmethod
   def create_turn(cls,conversation,text):return {'id':'t1'}
   @classmethod
   def turn(cls,tid):return {'status':'complete','output_text':cls.reply}
  self.call.core=Turns;self.call.follow=lambda tid,generation:None
  ended=[];self.call.hang_up=lambda after_playback=False:ended.append(after_playback)
  Turns.reply='Shall I draft a reply to them, or is that goodbye for now?'
  self.call.answer('is that all?');self.assertEqual(ended,[])   # "goodbye" mid-question is not a sign-off
  Turns.reply='Very good, sir. Goodbye.'
  self.call.answer("no, that's good");self.assertEqual(ended,[True])
 def test_phone_turns_get_the_phone_rules(self):
  self.assertIn('Travis',c.companion_tools.PHONE)
  source=Path(c.__file__).read_text()
  self.assertIn("messages.insert(1,{'role':'system','content':companion_tools.PHONE})",source)

class LookupAnswerTests(unittest.TestCase):
 def test_only_two_short_sentences_are_spoken(self):
  import job_announcements
  result='You applied to 25 jobs today. Veeva, BlueCat and Jamf were among them. I counted from midnight Eastern and left out three.\n\n- Source: Gmail'
  self.assertEqual(job_announcements.spoken_answer(result),'You applied to 25 jobs today. Veeva, BlueCat and Jamf were among them.')
 def test_a_second_ask_while_the_lookup_runs_does_not_start_another(self):
  catalog=patch('project_memory.catalog',return_value=[]);catalog.start();self.addCleanup(catalog.stop)
  with tempfile.TemporaryDirectory() as folder:
   old=c.DATA;c.DATA=Path(folder)
   try:
    c.initialize()
    cid=phone.new_conversation(c,'Phone call')
    with patch.object(assistant_jobs,'run',lambda core,job,approved=None:None):
     def turn(text):
      tid=uuid.uuid4().hex
      with c.connect() as db:db.execute("INSERT INTO turns(id,conversation_id,source,status,input_text,created,updated) VALUES(?,?,'text','thinking',?,?,?)",(tid,cid,text,time.time(),time.time()))
      return {'id':tid,'conversation_id':cid,'input_text':text}
     first=turn('how many jobs did I apply to today')
     c.companion_tools.execute(c,first,'delegate_task',{'task':'Count job applications today'})
     second=turn('sounds good')
     again=c.companion_tools.execute(c,second,'delegate_task',{'task':'Count job applications today'})
    self.assertEqual(again['status'],'already_running')
    with c.connect() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM codex_jobs").fetchone()[0],1)
   finally:c.DATA=old

class StripeTests(unittest.TestCase):
 def setUp(self):
  catalog=patch('project_memory.catalog',return_value=[]);catalog.start();self.addCleanup(catalog.stop)
  self.temp=tempfile.TemporaryDirectory();self.old=c.DATA;c.DATA=Path(self.temp.name);c.initialize()
  (c.DATA/'twilio.json').write_text(json.dumps({'account_sid':'AC1','auth_token':'tok','from_number':'+15550001111','my_number':'+15552223333','public_url':'https://j.example.ts.net:10000'}))
  (c.DATA/'stripe-webhook-secret').write_text('whsec_test')
  voice=patch('fish_voice.key',return_value=None);voice.start();self.addCleanup(voice.stop)
  with patch.object(phone,'PORT',0):self.server=phone.start(c)
  self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
  phone.SEEN_EVENTS.clear()
 def tearDown(self):c.DATA=self.old;self.temp.cleanup()
 def post(self,event,header=None):
  body=json.dumps(event).encode()
  conn=HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
  conn.request('POST','/stripe/webhook',body,{'Content-Type':'application/json','Stripe-Signature':header or stripe_header('whsec_test',body)})
  response=conn.getresponse();response.read();conn.close();return response.status

 def test_signature_rules(self):
  body=b'{"id":"evt"}'
  self.assertTrue(phone.stripe_valid('whsec_x',body,stripe_header('whsec_x',body)))
  self.assertFalse(phone.stripe_valid('whsec_x',body,stripe_header('whsec_other',body)))
  self.assertFalse(phone.stripe_valid('whsec_x',body,stripe_header('whsec_x',body,time.time()-900)))
  self.assertFalse(phone.stripe_valid('whsec_x',body,'garbage'))

 def test_new_sale_rings_once_and_forged_events_are_refused(self):
  event={'id':'evt_1','type':'checkout.session.completed','livemode':True,
   'data':{'object':{'payment_status':'paid','mode':'subscription','amount_total':1999,'currency':'usd'}}}
  rang=[]
  with patch.object(phone,'deliver',lambda core,text,conversation=None:rang.append(text)),patch.object(phone,'awake_hours',return_value=True):
   self.assertEqual(self.post(event,header='t=1,v1=forged'),400)
   self.assertEqual(self.post(event),200)
   self.assertEqual(self.post(event),200)   # Stripe retry of the same event
   deadline=time.time()+3
   while not rang and time.time()<deadline:time.sleep(.02)
   time.sleep(.2)
  self.assertEqual(rang,['Good news. A new subscription just came through on Parl.ai, $19.99.'])

 def test_night_sales_and_cancellations_go_to_telegram(self):
  sent=[]
  with patch('notify.send',lambda core,text:sent.append(text)),patch.object(phone,'deliver') as ring,patch.object(phone,'awake_hours',return_value=False):
   phone.stripe_event(c,{'id':'evt_2','type':'checkout.session.completed','livemode':False,'data':{'object':{'payment_status':'paid','mode':'payment','amount_total':500,'currency':'usd'}}})
   phone.stripe_event(c,{'id':'evt_3','type':'customer.subscription.deleted','data':{'object':{}}})
   phone.stripe_event(c,{'id':'evt_4','type':'customer.created','data':{'object':{}}})
  ring.assert_not_called()
  self.assertEqual(sent,['Parl.ai · Test mode: Good news. A payment just came through on Parl.ai, $5.','Parl.ai · A Parl.ai subscription was just cancelled.'])

class LaneTests(unittest.TestCase):
 def setUp(self):
  catalog=patch('project_memory.catalog',return_value=[]);catalog.start();self.addCleanup(catalog.stop)
  self.temp=tempfile.TemporaryDirectory();self.old=c.DATA;c.DATA=Path(self.temp.name);c.initialize()
 def tearDown(self):c.DATA=self.old;self.temp.cleanup()
 def test_three_lookups_run_side_by_side_and_a_fourth_waits(self):
  with patch.object(assistant_jobs,'run',lambda core,job,approved=None:None):
   for n in range(3):
    self.assertEqual(codex_jobs.start_job(c,codex_jobs.draft(c,'__assistant__',f'Look up thing {n}',f'src{n}')['id'])['status'],'preparing')
   with self.assertRaises(c.Problem) as refused:codex_jobs.start_job(c,codex_jobs.draft(c,'__assistant__','Look up thing 4','src4')['id'])
  self.assertEqual(refused.exception.status,409)

 def test_email_drafts_run_without_approval_but_sending_does_not(self):
  allowed=assistant_jobs.readonly(['mcp__claude_ai_Gmail__create_draft','mcp__claude_ai_Gmail__update_draft','mcp__claude_ai_Gmail__send_message','mcp__claude_ai_Gmail__delete_draft'])
  self.assertEqual(allowed,['mcp__claude_ai_Gmail__create_draft','mcp__claude_ai_Gmail__update_draft'])

class WatchTests(unittest.TestCase):
 def test_half_hourly_watch_stays_inside_its_window(self):
  def at(h,m):return datetime.now().replace(hour=h,minute=m,second=0,microsecond=0).timestamp()
  item={'repeat':'30min','window':'08:00-22:00'}
  self.assertEqual(datetime.fromtimestamp(scheduler.next_run(item,at(8,10))).strftime('%H:%M'),'08:30')
  self.assertEqual(datetime.fromtimestamp(scheduler.next_run(item,at(7,0))).strftime('%H:%M'),'08:00')
  late=datetime.fromtimestamp(scheduler.next_run(item,at(22,5)))
  self.assertEqual(late.strftime('%H:%M'),'08:00')

 def test_untouched_old_watch_is_upgraded_but_a_customized_one_is_kept(self):
  with tempfile.TemporaryDirectory() as folder:
   old=c.DATA;c.DATA=Path(folder)
   try:
    with patch('project_memory.catalog',return_value=[]):
     c.initialize()
     with c.connect() as db:db.execute("UPDATE schedules SET task=?,repeat='hourly' WHERE id='inbox-watch'",(scheduler.RETIRED['inbox-watch'][0],))
     c.initialize()
     with c.connect() as db:row=db.execute("SELECT task,repeat FROM schedules WHERE id='inbox-watch'").fetchone()
     self.assertEqual((row[0],row[1]),(scheduler.DEFAULTS[1]['task'],'30min'))
     with c.connect() as db:db.execute("UPDATE schedules SET task='my own watch',repeat='hourly' WHERE id='inbox-watch'")
     c.initialize()
     with c.connect() as db:self.assertEqual(db.execute("SELECT task FROM schedules WHERE id='inbox-watch'").fetchone()[0],'my own watch')
   finally:c.DATA=old

if __name__=='__main__':unittest.main()
