import json,tempfile,unittest,urllib.request,urllib.error
from pathlib import Path
import site_preview
class PreviewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'index.html').write_text('<h1>Actual preview</h1>');(self.root/'.env').write_text('private')
 def tearDown(self):site_preview.shutdown();self.tmp.cleanup()
 def test_preview_is_served_on_separate_origin(self):
  url=site_preview.start('test',self.root)
  with urllib.request.urlopen(url) as r:
   self.assertIn(b'Actual preview',r.read());self.assertIn("connect-src 'none'",r.headers['Content-Security-Policy'])
 def test_private_and_traversal_paths_rejected(self):
  for path in ['/.env','/../secret.json','/%2e%2e/secret.json','/.git/config']:
   self.assertIsNone(site_preview.resolve_file(self.root,path))
 def test_symlink_escape_rejected(self):
  with tempfile.TemporaryDirectory() as outside:
   p=Path(outside)/'secret.html';p.write_text('secret');(self.root/'escape.html').symlink_to(p)
   self.assertIsNone(site_preview.resolve_file(self.root,'/escape.html'))
 def test_host_rebinding_rejected(self):
  url=site_preview.start('test',self.root)
  with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(urllib.request.Request(url,headers={'Host':'untrusted.example'}))
  self.assertEqual(error.exception.code,403);error.exception.close()
 def test_private_proxy_serves_selected_root_and_blocks_api(self):
  port=site_preview.configure_remote('https://preview.example:8443',port=0)
  self.assertEqual(site_preview.select_remote(self.root),'https://preview.example:8443/')
  def request(path):return urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{port}'+path,headers={'Host':'preview.example:8443'}))
  with request('/') as response:self.assertIn(b'Actual preview',response.read())
  for path in ['/api/jobs','/.env','/../secret.json']:
   with self.assertRaises(urllib.error.HTTPError) as error:request(path)
   self.assertEqual(error.exception.code,404);error.exception.close()
 def test_private_proxy_requires_explicit_root_and_origin(self):
  with self.assertRaises(ValueError):site_preview.configure_remote('http://insecure.example',port=0)
  port=site_preview.configure_remote('https://preview.example:8443',port=0)
  with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(f'http://127.0.0.1:{port}/')
  self.assertEqual(error.exception.code,503);error.exception.close()
