"""Install/manage the companion as a per-user macOS LaunchAgent (no sudo)."""
import argparse,json,os,plistlib,shutil,subprocess,sys
from pathlib import Path
LABEL='com.projectroom.jarvis'
ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('VOICE_DATA_DIR',Path.home()/'.local/share/ai-voice-agent')).expanduser().resolve()
PLIST=Path.home()/'Library/LaunchAgents'/f'{LABEL}.plist'
TARGET=f'gui/{os.getuid()}/{LABEL}'

def loaded():
    return subprocess.run(['launchctl','print',TARGET],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0

def refresh_catalog():
    source=Path(os.environ.get('VOICE_PROJECT_ROOM',Path.home()/'Documents/Project Room'))/'app/projects/archive-catalog.json'
    rows=json.loads(source.read_text())
    if not isinstance(rows,list) or not all(isinstance(p,dict) and 'id' in p and 'name' in p for p in rows):raise SystemExit('Project catalog is invalid.')
    DATA.mkdir(parents=True,exist_ok=True,mode=0o700)
    target=DATA/'project-catalog.json';temporary=target.with_suffix('.pending')
    temporary.write_text(json.dumps(rows,ensure_ascii=False));temporary.chmod(0o600);temporary.replace(target)
    print('Refreshed the private Project Room catalog snapshot.')

def install():
    refresh_catalog()
    if loaded():print('Jarvis background service is already loaded.');return
    import socket
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1',4321))==0:raise SystemExit('Port 4321 is already in use. Stop the existing companion safely before installing.')
    python=str(ROOT/'.venv/bin/python') if (ROOT/'.venv/bin/python').is_file() else shutil.which('python3')
    if not python or not (ROOT/'dist/index.html').is_file():raise SystemExit('Python and the built frontend are required.')
    codex=shutil.which('codex')
    service_path=':'.join(dict.fromkeys(([str(Path(codex).parent)] if codex else [])+['/opt/homebrew/bin','/usr/local/bin','/usr/bin','/bin','/usr/sbin','/sbin']))
    logs=DATA/'logs';logs.mkdir(parents=True,exist_ok=True,mode=0o700)
    for name in ['server.log','server-error.log']:
        file=logs/name;file.touch(mode=0o600,exist_ok=True);file.chmod(0o600)
    config={'Label':LABEL,'ProgramArguments':[python,str(ROOT/'companion.py')],'WorkingDirectory':str(ROOT),
      'ProcessType':'Interactive','RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':10,'ExitTimeOut':15,
      'EnvironmentVariables':{'PATH':service_path,'VOICE_DATA_DIR':str(DATA),'VOICE_PROJECT_CATALOG':str(DATA/'project-catalog.json')},
      'StandardOutPath':str(logs/'server.log'),'StandardErrorPath':str(logs/'server-error.log')}
    PLIST.parent.mkdir(parents=True,exist_ok=True)
    temporary=PLIST.with_suffix('.pending');temporary.write_bytes(plistlib.dumps(config));temporary.chmod(0o600);temporary.replace(PLIST)
    subprocess.run(['launchctl','bootstrap',f'gui/{os.getuid()}',str(PLIST)],check=True)
    print('Jarvis is installed as a login service with automatic restart.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['install','status','refresh-catalog','uninstall']);args=parser.parse_args()
    if sys.platform!='darwin':raise SystemExit('This helper requires macOS.')
    if args.action=='install':install()
    elif args.action=='refresh-catalog':refresh_catalog()
    elif args.action=='status':raise SystemExit(subprocess.run(['launchctl','print',TARGET]).returncode)
    else:
        if loaded():subprocess.run(['launchctl','bootout',TARGET],check=True)
        PLIST.unlink(missing_ok=True)
        print('Background service removed. Conversation data and jobs were preserved.')
