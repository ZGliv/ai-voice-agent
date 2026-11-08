"""Speed: instant barge-in, early start on Deepgram's eager end-of-turn, hedged brain, no hidden thinking."""
import json, threading, time, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
import brain, companion as c, companion_tools, fish_text_stream, phone

class FakeSocket:
    def __init__(self):self.sent=[]
    def send(self,value):self.sent.append(value)

class Core:
    DATA=None;CURRENT=None;STOP=threading.Event();SPECULATIVE={};Cancelled=c.Cancelled;Problem=c.Problem

class FluxEventTests(unittest.TestCase):
    def setUp(self):
        Core.STOP.clear();Core.SPECULATIVE.clear()
        self.call=phone.Call(Core,FakeSocket(),'MZ1','conv')

    def test_he_starts_talking_and_jarvis_stops_at_once(self):
        stopped=[]
        self.call.speaking=lambda:True;self.call.interrupt=lambda:stopped.append(True)
        self.call.on_flux({'event':'StartOfTurn','transcript':''},'')
        self.assertEqual(stopped,[True])   # no need to wait for his words

    def test_early_guess_is_confirmed_when_he_really_finished(self):
        self.call.on_flux({'event':'EagerEndOfTurn','transcript':'What is on my calendar?'},'')
        kind,spec=self.call.pending.get_nowait()
        self.assertEqual((kind,spec.text),('eager','What is on my calendar?'))
        self.call.on_flux({'event':'EndOfTurn','transcript':'What is on my calendar'},'')
        self.assertTrue(spec.confirm.is_set());self.assertTrue(self.call.pending.empty())   # not answered twice

    def test_early_guess_is_dropped_when_he_keeps_talking(self):
        self.call.on_flux({'event':'EagerEndOfTurn','transcript':'Spin up Claude Code'},'')
        _,spec=self.call.pending.get_nowait();spec.tid='t1';Core.CURRENT='t1'
        self.call.on_flux({'event':'TurnResumed','transcript':''},'')
        self.assertTrue(spec.cancel.is_set());self.assertTrue(Core.STOP.is_set())
        Core.CURRENT=None
        self.call.on_flux({'event':'EndOfTurn','transcript':'Spin up Claude Code on Parl.ai to fix signups'},'')
        self.assertEqual(self.call.pending.get_nowait(),('answer','Spin up Claude Code on Parl.ai to fix signups'))

    def test_different_final_words_replace_the_guess(self):
        self.call.on_flux({'event':'EagerEndOfTurn','transcript':'Check my email'},'')
        _,spec=self.call.pending.get_nowait()
        self.call.on_flux({'event':'EndOfTurn','transcript':'Check my email from Veeva'},'')
        self.assertTrue(spec.cancel.is_set());self.assertEqual(self.call.pending.get_nowait()[1],'Check my email from Veeva')

    def test_held_reply_plays_nothing_until_confirmed_and_nothing_if_dropped(self):
        spec=phone.Speculation('hello')
        class Turns(Core):
            DATA=__import__('pathlib').Path('/nonexistent')
            @staticmethod
            def turn(tid):return {'status':'complete'}
        self.call.core=Turns
        done=threading.Event()
        threading.Thread(target=lambda:(self.call.follow('t1',self.call.generation,spec),done.set()),daemon=True).start()
        time.sleep(.15);self.assertFalse(done.is_set());self.assertEqual(self.call.socket.sent,[])
        spec.cancel.set();self.assertTrue(done.wait(1));self.assertEqual(self.call.socket.sent,[])

    def test_actions_wait_for_confirmation_and_are_refused_if_dropped(self):
        spec=phone.Speculation('start work');Core.SPECULATIVE['t1']=spec
        item={'id':'t1','conversation_id':'c','input_text':'start work'}
        threading.Timer(.1,spec.cancel.set).start()
        started=time.monotonic()
        with self.assertRaises(c.Cancelled):companion_tools.execute(Core,item,'job_status',{})
        self.assertGreater(time.monotonic()-started,.08)

class SpeechStartTests(unittest.TestCase):
    def test_route_speech_accepts_unmarked_replies(self):
        self.assertEqual(c.route_speech('SAY\nParis.'),'Paris.')
        self.assertEqual(c.route_speech('Very good. Goodbye.'),'Very good. Goodbye.')
        self.assertIsNone(c.route_speech('TOOLS'));self.assertIsNone(c.route_speech('SA'))

    def test_voice_starts_at_the_first_natural_pause(self):
        class T(fish_text_stream.TextSpeech):
            def __init__(s):s.raw='';s.buffer='';s.first_text=None;s.sent=[]
            def _text(s,t):s.first_text=s.first_text or 1;s.sent.append(t)
        t=T();text=''
        for ch in 'As of seven twenty, you have applied to twenty-five jobs.':text+=ch;t.feed(text)
        self.assertEqual(t.sent[0],'As of seven twenty,')

class SlowThenFast(BaseHTTPRequestHandler):
    calls=[]
    def log_message(self,*a):pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        SlowThenFast.calls.append(body)
        if len(SlowThenFast.calls)==1:time.sleep(1.5)
        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
        word='slow' if len(SlowThenFast.calls)==1 else 'fast'
        for chunk in [{'choices':[{'delta':{'content':word}}]},{'choices':[{'delta':{},'finish_reason':'stop'}]}]:
            self.wfile.write(b'data: '+json.dumps(chunk).encode()+b'\n\n')
        self.wfile.write(b'data: [DONE]\n\n')

class BrainTests(unittest.TestCase):
    def test_a_slow_start_is_hedged_and_thinking_is_off(self):
        SlowThenFast.calls=[]
        server=ThreadingHTTPServer(('127.0.0.1',0),SlowThenFast);threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        cloud={'base_url':f'http://127.0.0.1:{server.server_port}','model':'claude-haiku-5-5','key':'k'}
        meter={};started=time.monotonic()
        reply=brain.cloud_chat(cloud,{'messages':[{'role':'user','content':'hi'}]},threading.Event(),lambda t:None,meter)
        self.assertEqual(reply['content'],'fast');self.assertLess(time.monotonic()-started,1.4)
        self.assertEqual(meter['hedged'],1)
        self.assertEqual(SlowThenFast.calls[0]['thinking'],{'type':'disabled'})

if __name__=='__main__':unittest.main()
