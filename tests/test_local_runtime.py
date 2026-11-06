import json,socket,threading,time,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from local_runtime import chat

class CancellationTests(unittest.TestCase):
 def test_cancel_disconnects_an_active_model_stream(self):
  disconnected=threading.Event();started=threading.Event();stop=threading.Event();outcome=[]
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_POST(self):
    self.rfile.read(int(self.headers['Content-Length']))
    self.send_response(200);self.send_header('Content-Type','application/x-ndjson');self.end_headers()
    self.wfile.write((json.dumps({'message':{'content':'Sir'}})+'\n').encode());self.wfile.flush();started.set()
    self.connection.settimeout(3)
    try:
     if self.connection.recv(1)==b'':disconnected.set()
    except OSError:pass
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  threading.Thread(target=server.serve_forever,daemon=True).start()
  def run():
   try:chat(f'http://127.0.0.1:{server.server_port}',{},stop,lambda text:None)
   except InterruptedError:outcome.append('cancelled')
  caller=threading.Thread(target=run);caller.start()
  try:
   self.assertTrue(started.wait(2));stop.set();caller.join(2)
   self.assertFalse(caller.is_alive());self.assertEqual(outcome,['cancelled'])
   self.assertTrue(disconnected.wait(1),'server should observe client close, freeing generation')
  finally:stop.set();server.shutdown();server.server_close()
