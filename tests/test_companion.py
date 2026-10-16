import tempfile, unittest, json, time, threading, sys, io, wave
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import companion as c

class CompanionTests(unittest.TestCase):
    def setUp(self):
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
    def test_busy_prevents_second_turn(self):
        c.CURRENT='busy'
        with self.assertRaises(c.Problem) as raised:self.make(text='Second')
        self.assertEqual(raised.exception.status,409)
    def test_model_failure_is_not_success(self):
        t=self.make(text='A failed thought')
        with patch.object(c,'run_process',side_effect=c.Problem('Ollama unavailable',503)):c.work(t['id'])
        saved=c.turn(t['id']);self.assertEqual(saved['status'],'failed');self.assertFalse(saved['output_text']);self.assertFalse(saved['has_audio'])
    def test_cancel_terminates_real_child(self):
        timer=threading.Timer(.25,c.STOP.set);timer.start();started=time.monotonic()
        with self.assertRaises(c.Cancelled):c.run_process([sys.executable,'-c','import time; time.sleep(20)'])
        timer.join();self.assertLess(time.monotonic()-started,3);self.assertIsNone(c.PROCESS)
    def test_cancel_does_not_publish_audio(self):
        t=self.make(text='A cancelled thought')
        with patch.object(c,'run_process',side_effect=c.Cancelled()):c.work(t['id'])
        self.assertEqual(c.turn(t['id'])['status'],'cancelled');self.assertFalse(c.turn(t['id'])['has_audio'])
    def test_retry_preserves_completed_language_step(self):
        t=self.make(text='Question');c.update(t['id'],output_text='A previously saved answer',status='failed')
        calls=[]
        def synth(args,timeout):
            calls.append(args)
            with wave.open(args[-1],'wb') as wav:wav.setparams((1,2,16000,0,'NONE','not compressed'));wav.writeframes(b'\x01\x01'*8000)
        with patch.object(c,'run_process',side_effect=synth),patch.object(c.Path,'is_file',return_value=True):c.work(t['id'])
        self.assertEqual(len(calls),1);self.assertIn('synthesize.py',calls[0][1]);self.assertEqual(c.turn(t['id'])['status'],'complete')
    def test_failed_upload_keeps_source_for_retry(self):
        t=self.make(audio=b'invalid audio')
        with patch.object(c,'run_process',side_effect=c.Problem('Invalid recording')):c.work(t['id'])
        self.assertEqual(c.turn(t['id'])['status'],'failed');self.assertEqual((c.DATA/'turns'/t['id']/'input.audio').read_bytes(),b'invalid audio')
if __name__=='__main__':unittest.main()
