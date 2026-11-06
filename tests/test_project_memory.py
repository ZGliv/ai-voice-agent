import unittest, tempfile, json, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import companion as c
import project_memory as m

class Handler:
    def __init__(self,data=None): self.data=data or {};self.result=None
    def body(self): return json.dumps(self.data).encode()
    def send(self,status,data): self.result=(status,data)

class ProjectMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.original=c.DATA;c.DATA=Path(self.tmp.name)/'data';c.initialize()
        self.patcher=patch.object(m,'catalog',return_value=[{'id':'one','name':'One'},{'id':'two','name':'Two'}]);self.patcher.start()
        with c.connect() as db:
            for cid in ['a'*32,'b'*32]:db.execute('INSERT INTO conversations VALUES(?,?,?,?)',(cid,'Test',1,1))
    def tearDown(self): self.patcher.stop();c.DATA=self.original;self.tmp.cleanup()
    def call(self,method,path,data=None):
        h=Handler(data);self.assertTrue(m.dispatch(h,method,path,c));return h.result[1]
    def test_project_memory_isolated_and_survives_new_conversation(self):
        self.call('POST','/api/projects/one/memory',{'kind':'decision','content':'Use a calm coach'})
        for cid in ['a'*32,'b'*32]:self.call('POST',f'/api/conversations/{cid}/project',{'project_id':'one'})
        with c.connect() as db:
            self.assertIn('Use a calm coach',m.context(db,'b'*32))
            self.assertEqual(m.memories(db,'two'),[])
        c.initialize()
        self.assertEqual(len(self.call('GET','/api/projects/one/memory')['memories']),1)
    def test_source_requires_matching_project_and_survives_conversation_delete(self):
        self.call('POST',f'/api/conversations/{"a"*32}/project',{'project_id':'one'})
        with c.connect() as db:db.execute('INSERT INTO turns(id,conversation_id,source,status,input_text,created,updated) VALUES(?,?,?,?,?,?,?)',('c'*32,'a'*32,'text','complete','Actual thought',1,1))
        with self.assertRaises(c.Problem):self.call('POST','/api/projects/two/memory',{'kind':'decision','content':'Wrong project','source_turn_id':'c'*32})
        self.call('POST','/api/projects/one/memory',{'kind':'decision','content':'Approved takeaway','source_turn_id':'c'*32})
        with c.connect() as db:db.execute('DELETE FROM conversations WHERE id=?',('a'*32,))
        note=self.call('GET','/api/projects/one/memory')['memories'][0]
        self.assertIsNone(note['source_turn_id']);self.assertEqual(note['source_text'],'Actual thought')
    def test_edit_complete_and_remove(self):
        note=self.call('POST','/api/projects/one/memory',{'kind':'next_step','content':'Test microphone'})
        self.call('POST',f'/api/memories/{note["id"]}',{'content':'Test the physical microphone','status':'done'})
        note=self.call('GET','/api/projects/one/memory')['memories'][0]
        self.assertEqual(note['status'],'done');self.assertEqual(note['content'],'Test the physical microphone')
        self.call('DELETE',f'/api/memories/{note["id"]}')
        self.assertEqual(self.call('GET','/api/projects/one/memory')['memories'],[])
    def test_cannot_relabel_existing_conversation(self):
        self.call('POST',f'/api/conversations/{"a"*32}/project',{'project_id':'one'})
        with c.connect() as db:db.execute('INSERT INTO turns(id,conversation_id,source,status,created,updated) VALUES(?,?,?,?,?,?)',('c'*32,'a'*32,'text','complete',1,1))
        with self.assertRaises(c.Problem):self.call('POST',f'/api/conversations/{"a"*32}/project',{'project_id':'two'})
    def test_unscoped_chat_can_choose_project_after_greeting(self):
        with c.connect() as db:
            db.execute('DELETE FROM conversation_projects WHERE conversation_id=?',('a'*32,))
            db.execute('INSERT INTO turns(id,conversation_id,source,status,created,updated) VALUES(?,?,?,?,?,?)',('c'*32,'a'*32,'text','complete',1,1))
        self.call('POST',f'/api/conversations/{"a"*32}/project',{'project_id':'one'})
        self.call('POST',f'/api/conversations/{"a"*32}/project',{'project_id':'one'})
        with self.assertRaises(c.Problem):self.call('POST',f'/api/conversations/{"a"*32}/project',{'project_id':'two'})
        with self.assertRaises(c.Problem):self.call('POST',f'/api/conversations/{"a"*32}/project',{'project_id':None})

    def test_reject_invalid_content_and_kind(self):
        for content,kind in [('', 'decision'),('x'*2001,'decision'),('hello','shell_command')]:
            with self.assertRaises(c.Problem):self.call('POST','/api/projects/one/memory',{'kind':kind,'content':content})
if __name__=='__main__':unittest.main()

class OriginTests(unittest.TestCase):
    def guard(self,host,origin=None,site='same-origin'):
        h=object.__new__(c.Handler);h.path='/api/projects';h.command='GET';h.headers={'Host':host,'X-Voice-Client':'1','Sec-Fetch-Site':site}
        if origin:h.headers['Origin']=origin
        h.guard()
    def test_exact_private_origin_only(self):
        with patch.object(c,'ALLOWED_HOSTS',{'127.0.0.1:4321','my-mac.example.ts.net'}),patch.object(c,'ALLOWED_ORIGINS',{'http://127.0.0.1:4321','https://my-mac.example.ts.net'}):
            self.guard('my-mac.example.ts.net','https://my-mac.example.ts.net')
            for host,origin,site in [('evil.example','https://evil.example','same-origin'),('my-mac.example.ts.net','https://evil.example','same-origin'),('my-mac.example.ts.net','https://my-mac.example.ts.net','cross-site')]:
                with self.assertRaises(c.Problem):self.guard(host,origin,site)

class CheckinRoutingTests(unittest.TestCase):
 def test_named_status_reads_only_matching_project_and_excludes_action_requests(self):
  from unittest.mock import patch
  project={'id':'parlay','name':'Parlay','updated_at':'2026-10-20','current_state':'Prototype','next_action':'Test it'}
  with patch.object(m,'catalog',return_value=[project]),patch.object(m,'memories',return_value=[]) as notes:
   result=m.checkin_reference(None,"I'm wondering how my projects are doing. How's Parlay doing?")
   self.assertIn('Prototype',result);notes.assert_called_once_with(None,'parlay')
   self.assertIsNone(m.checkin_reference(None,'How is Parlay doing? Build it now.'))
   self.assertIsNone(m.checkin_reference(None,'Save the status of Parlay'))

   self.assertIsNone(m.checkin_reference(None,"How is it going?"))
   with patch.object(m,'catalog',return_value=[]):
    self.assertFalse(json.loads(m.checkin_reference(None,"How's Parlay doing?"))['available'])
