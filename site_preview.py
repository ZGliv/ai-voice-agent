"""Serve generated static sites on a separate loopback origin, never the control API."""
import mimetypes, threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,unquote
ALLOWED={'.html','.htm','.css','.js','.mjs','.json','.png','.jpg','.jpeg','.gif','.webp','.svg','.ico','.woff','.woff2','.ttf','.mp4','.webm','.mp3','.wav','.pdf'}
SERVERS={}
REMOTE=None
REMOTE_ROOT=None
REMOTE_ORIGIN=''
CSP="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"

def resolve_file(root, request):
    relative=unquote(urlparse(request).path).lstrip('/') or 'index.html'
    if any(part.startswith('.') for part in Path(relative).parts):return None
    file=(root/relative).resolve()
    if not file.is_relative_to(root) or file.suffix.lower() not in ALLOWED or not file.is_file():return None
    return file

def handler_for(get_root,extra_hosts):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            allowed={f'127.0.0.1:{self.server.server_port}',*extra_hosts}
            if self.headers.get('Host') not in allowed:self.send_error(403);return
            root=get_root()
            if root is None:self.send_error(503,'Choose a finished preview in Jarvis first.');return
            file=resolve_file(root,self.path)
            if not file:self.send_error(404);return
            content=file.read_bytes()
            self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
            self.send_header('Content-Length',str(len(content)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',CSP)
            self.end_headers()
            try:self.wfile.write(content)
            except (BrokenPipeError,ConnectionResetError):pass
    return Handler

def configure_remote(origin,port=4323):
    global REMOTE,REMOTE_ORIGIN
    parsed=urlparse(origin)
    if parsed.scheme!='https' or not parsed.hostname or parsed.path not in {'','/'} or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Preview origin must be an explicit HTTPS origin.')
    if REMOTE:raise ValueError('Preview server is already configured.')
    REMOTE_ORIGIN=origin.rstrip('/')
    REMOTE=ThreadingHTTPServer(('127.0.0.1',port),handler_for(lambda:REMOTE_ROOT,{parsed.netloc}))
    threading.Thread(target=REMOTE.serve_forever,daemon=True).start()
    return REMOTE.server_port

def select_remote(root):
    global REMOTE_ROOT
    root=Path(root).resolve()
    if not REMOTE:raise ValueError('Private phone previews are not configured.')
    if not resolve_file(root,'/index.html'):raise ValueError('No preview index.html.')
    REMOTE_ROOT=root
    return REMOTE_ORIGIN+'/'

def start(jid,root):
    root=Path(root).resolve()
    if not resolve_file(root,'/index.html'):raise ValueError('No built index.html in preview folder')
    if jid in SERVERS:return SERVERS[jid][1]
    Handler=handler_for(lambda:root,{})
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);url=f'http://127.0.0.1:{server.server_port}/'
    SERVERS[jid]=(server,url);threading.Thread(target=server.serve_forever,daemon=True).start()
    return url

def shutdown():
    global REMOTE,REMOTE_ROOT,REMOTE_ORIGIN
    if REMOTE:REMOTE.shutdown();REMOTE.server_close()
    REMOTE=None;REMOTE_ROOT=None;REMOTE_ORIGIN=''
    for server,_ in list(SERVERS.values()):server.shutdown();server.server_close()
    SERVERS.clear()
