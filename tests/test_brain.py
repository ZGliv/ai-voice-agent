import json,os,tempfile,threading,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from unittest import mock
import brain

def sse_server(chunks,status=200,seen=None):
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_POST(self):
   body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
   if seen is not None:seen.append({'body':body,'auth':self.headers.get('Authorization')})
   if status!=200:
    payload=json.dumps({'error':{'message':'You have no credits remaining.'}}).encode()
    self.send_response(status);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload);return
   self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
   for chunk in chunks:self.wfile.write(b'data: '+json.dumps(chunk).encode()+b'\n\n');self.wfile.flush()
   self.wfile.write(b'data: [DONE]\n\n')
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 return server

class BrainTests(unittest.TestCase):
 def setUp(self):
  self.dir=tempfile.TemporaryDirectory();self.data=Path(self.dir.name)
  self.env=mock.patch.dict(os.environ,{},clear=False);self.env.start();os.environ.pop('JARVIS_LLM_API_KEY',None)
 def tearDown(self):self.env.stop();self.dir.cleanup()
 def configure(self,server):
  brain.save(self.data,f'http://127.0.0.1:{server.server_port}/v1','test-model','secret-key')

 def test_without_key_there_is_no_cloud_config(self):
  self.assertIsNone(brain.config(self.data))
  self.assertIn('local',brain.label(self.data))

 def test_saved_files_are_owner_only(self):
  brain.save(self.data,'https://example.test/v1/','m','k')
  self.assertEqual(oct((self.data/'brain-api-key').stat().st_mode)[-3:],'600')
  self.assertEqual(brain.config(self.data)['base_url'],'https://example.test/v1')

 def test_history_conversion_pairs_tool_results_with_call_ids(self):
  converted=brain.to_openai([
   {'role':'system','content':'S'},{'role':'user','content':'U'},
   {'role':'assistant','content':'','tool_calls':[{'id':'a','function':{'name':'job_status','arguments':{}}},{'function':{'name':'save_memory','arguments':{'kind':'decision'}}}]},
   {'role':'tool','tool_name':'job_status','content':'{"jobs":[]}'},
   {'role':'system','content':'route'}])
  call_ids=[c['id'] for c in converted[2]['tool_calls']]
  self.assertEqual(converted[2]['tool_calls'][1]['function']['arguments'],'{"kind": "decision"}')
  self.assertEqual([m.get('tool_call_id') for m in converted[3:5]],call_ids)
  self.assertIn('Not run',converted[4]['content'],'unexecuted calls get an explicit result')
  self.assertEqual(converted[5],{'role':'system','content':'route'})

 def test_streams_text_and_tool_calls_into_ollama_shape(self):
  seen=[]
  server=sse_server([
   {'choices':[{'delta':{'tool_calls':[{'index':0,'id':'call_1','function':{'name':'save_','arguments':'{"kind":'}}]}}]},
   {'choices':[{'delta':{'tool_calls':[{'index':0,'function':{'name':'memory','arguments':'"decision","content":"Use cyan"}'}}]}}]},
   {'choices':[],'usage':{'prompt_tokens':120,'completion_tokens':9}}],seen=seen)
  try:
   self.configure(server);meter={}
   result=brain.chat(self.data,{'messages':[{'role':'user','content':'hi'}],'tools':[{'type':'function','function':{'name':'save_memory'}}],'options':{'num_predict':300,'temperature':.4}},threading.Event(),lambda t:None,meter)
  finally:server.shutdown();server.server_close()
  self.assertEqual(result['tool_calls'][0]['function'],{'name':'save_memory','arguments':{'kind':'decision','content':'Use cyan'}})
  self.assertEqual(seen[0]['auth'],'Bearer secret-key')
  self.assertEqual(seen[0]['body']['max_tokens'],300)
  self.assertEqual(meter['model'],'test-model');self.assertEqual(meter['calls'][0]['input_tokens'],120)

 def test_streams_spoken_text_progressively(self):
  server=sse_server([{'choices':[{'delta':{'content':'SAY\nGood '}}]},{'choices':[{'delta':{'content':'evening.'}}]}])
  partials=[]
  try:
   self.configure(server)
   result=brain.chat(self.data,{'messages':[{'role':'user','content':'hello'}]},threading.Event(),partials.append)
  finally:server.shutdown();server.server_close()
  self.assertEqual(result,{'role':'assistant','content':'SAY\nGood evening.'})
  self.assertTrue(partials)

 def test_cloud_failure_before_speech_falls_back_to_local(self):
  server=sse_server([],status=429)
  try:
   self.configure(server);meter={}
   with mock.patch('local_runtime.chat',return_value={'role':'assistant','content':'local'}) as local:
    result=brain.chat(self.data,{'messages':[{'role':'user','content':'hi'}],'options':{'num_predict':300}},threading.Event(),lambda t:None,meter)
  finally:server.shutdown();server.server_close()
  self.assertEqual(result['content'],'local')
  self.assertIn('429',meter['fallback']);self.assertTrue(meter['local'])
  payload=local.call_args[0][1]
  self.assertEqual(payload['model'],brain.LOCAL_MODEL);self.assertEqual(payload['options']['num_ctx'],8192)

 def test_no_cloud_config_uses_local_model(self):
  with mock.patch('local_runtime.chat',return_value={'role':'assistant','content':'local'}) as local:
   brain.chat(self.data,{'messages':[]},threading.Event(),lambda t:None)
  self.assertEqual(local.call_args[0][0],brain.OLLAMA+'/api/chat')

if __name__=='__main__':unittest.main()
