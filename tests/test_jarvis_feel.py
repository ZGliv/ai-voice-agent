"""Briefing (instant answers + call opener), personal memory, and pre-drafted replies."""
import json, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch
import companion as c
import briefing, personal_memory, scheduler, phone

KNOWN={'headline':'Veeva assessment due Tuesday','applications_today':25,'application_companies':['Veeva','BlueCat','Jamf'],
  'waiting_on_you':['Veeva assessment by Tuesday'],'next_events':[],'parl_ai':None,
  'opener':"Evening. Twenty-five applications today, and Veeva's assessment is due Tuesday. What can I do for you?"}

class Base(unittest.TestCase):
    def setUp(self):
        catalog=patch('project_memory.catalog',return_value=[]);catalog.start();self.addCleanup(catalog.stop)
        self.temp=tempfile.TemporaryDirectory();self.old=c.DATA;c.DATA=Path(self.temp.name);c.CURRENT=None;c.STOP.clear();c.initialize()
    def tearDown(self):c.DATA=self.old;self.temp.cleanup()

class BriefingTests(Base):
    def test_watch_answer_is_split_from_its_briefing_line(self):
        text,known=briefing.split('NOTHING\nBRIEFING: '+json.dumps({**KNOWN,'evil':'x'}))
        self.assertEqual(text,'NOTHING');self.assertEqual(known['applications_today'],25);self.assertNotIn('evil',known)
        self.assertEqual(briefing.split('NOTHING'),('NOTHING',None))
        self.assertEqual(briefing.split('NOTHING\nBRIEFING: {broken'),('NOTHING',None))

    def test_watch_saves_the_briefing_and_still_stays_quiet(self):
        job={'source_turn_id':'schedule:inbox-watch:1','status':'completed','result':'NOTHING\nBRIEFING: '+json.dumps(KNOWN)}
        with patch('notify.send') as sent,patch('phone.ready',return_value=False):scheduler.job_done(c,job)
        sent.assert_not_called()
        self.assertEqual(briefing.fresh(c.DATA)['data']['applications_today'],25)
        self.assertIn('as of',briefing.context(c.DATA))

    def test_stale_briefing_is_ignored(self):
        briefing.save(c.DATA,KNOWN,now=time.time()-briefing.FRESH-5)
        self.assertIsNone(briefing.fresh(c.DATA));self.assertEqual(briefing.context(c.DATA),'')

    def test_opener_is_used_once(self):
        briefing.save(c.DATA,KNOWN)
        self.assertEqual(briefing.take_opener(c.DATA),KNOWN['opener'])
        self.assertIsNone(briefing.take_opener(c.DATA))

    def test_quick_question_is_answered_from_the_briefing_without_a_lookup(self):
        briefing.save(c.DATA,KNOWN)
        with patch.object(c,'launch'):item=c.create_turn(self.conversation(),text='How many jobs did I apply to today?')
        seen=[]
        def answer(data,payload,stop,on_text,meter=None):
            seen.append(payload['messages'])
            on_text('SAY\nAs of now, twenty-five, sir.');return {'role':'assistant','content':'SAY\nAs of now, twenty-five, sir.'}
        speech=type('S',(),{'feed':lambda s,t:None,'finish':lambda s,t:None,'close':lambda s:None,'wait':lambda s:{}})
        with patch('brain.chat',side_effect=answer),patch('fish_voice.key',return_value='k'),patch('fish_text_stream.available',return_value=True),\
             patch('fish_text_stream.TextSpeech',side_effect=lambda *a,**k:speech()),patch('assistant_jobs.delegate') as delegate:
            c.CURRENT=item['id'];c.work(item['id'])
        delegate.assert_not_called()
        self.assertEqual(c.turn(item['id'])['output_text'],'As of now, twenty-five, sir.')
        self.assertTrue(any('Already known' in m['content'] for m in seen[0] if m['role']=='system'))

    def conversation(self):
        cid='b'*32
        with c.connect() as db:db.execute('INSERT INTO conversations VALUES(?,?,?,?)',(cid,'Test',time.time(),time.time()))
        return cid

class OpenerTests(Base):
    def test_inbound_call_opens_with_the_news_once_its_audio_is_ready(self):
        briefing.save(c.DATA,KNOWN)
        with patch('phone.cached',return_value=None):self.assertIsNone(phone.greeting(c))   # audio not rendered yet
        with patch('phone.cached',return_value=Path('clip.wav')):
            self.assertEqual(phone.greeting(c),KNOWN['opener'])
            self.assertIsNone(phone.greeting(c))   # the same news is not repeated on the next call

class MemoryTests(Base):
    def test_remember_tool_keeps_facts_for_every_turn(self):
        cid='c'*32
        with c.connect() as db:db.execute('INSERT INTO conversations VALUES(?,?,?,?)',(cid,'Test',time.time(),time.time()))
        item={'id':'t'*32,'conversation_id':cid,'input_text':'remember I prefer morning interviews'}
        c.companion_tools.execute(c,item,'remember',{'fact':'Zack prefers morning interviews.'})
        again=c.companion_tools.execute(c,item,'remember',{'fact':'zack prefers morning interviews.'})
        self.assertTrue(again['duplicate'])
        self.assertIn('morning interviews',personal_memory.context(c))

    def test_call_review_keeps_lasting_facts_only_when_there_was_a_conversation(self):
        cid=phone.new_conversation(c,'Phone call')
        def add(i,o):
            with c.connect() as db:db.execute("INSERT INTO turns(id,conversation_id,source,status,input_text,output_text,created,updated) VALUES(?,?,'text','complete',?,?,?,?)",(str(time.time_ns()),cid,i,o,time.time(),time.time()))
        add('Sarah from Veeva is my recruiter','Noted.')
        with patch('brain.chat') as chat:self.assertEqual(personal_memory.review_call(c,cid),[]);chat.assert_not_called()
        add('I am waiting to hear back from BlueCat','I shall keep an ear out.')
        reply={'role':'assistant','content':'["Sarah at Veeva is Zack\'s recruiter.","Zack is waiting to hear back from BlueCat."]'}
        with patch('brain.chat',return_value=reply):kept=personal_memory.review_call(c,cid)
        self.assertEqual(len(kept),2);self.assertIn('BlueCat',personal_memory.context(c))

class DraftTests(unittest.TestCase):
    def test_watch_drafts_replies_but_never_sends(self):
        task=scheduler.DEFAULTS[1]['task']
        self.assertIn('save a short draft reply',task);self.assertIn('never send',task);self.assertIn('BRIEFING:',task)

if __name__=='__main__':unittest.main()
