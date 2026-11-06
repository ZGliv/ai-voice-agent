#!/usr/bin/env python3
"""Connect Jarvis's brain, Telegram and phone. Secrets are typed at a hidden prompt and
saved owner-only in the private data directory; nothing is written to the repository.

  python3 jarvis_setup.py status
  python3 jarvis_setup.py brain [openai|groq|anthropic|openrouter] [--model NAME]
  python3 jarvis_setup.py bench
  python3 jarvis_setup.py telegram-test
  python3 jarvis_setup.py twilio
  python3 jarvis_setup.py call-test
  python3 jarvis_setup.py restart
"""
import argparse, base64, getpass, json, os, subprocess, sys, threading, time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
sys.path.insert(0,str(Path(__file__).resolve().parent))
import brain, notify, phone, assistant_jobs

DATA=Path(os.environ.get('VOICE_DATA_DIR',Path.home()/'.local/share/ai-voice-agent')).expanduser()
LABEL='com.projectroom.jarvis'

class Core:
    """Just enough of the companion for notify/phone helpers."""
    DATA=DATA
    class Problem(Exception):
        def __init__(self,message,status=400):super().__init__(message);self.message,self.status=message,status

def ok(flag):return '✅' if flag else '⬜️'

def tailscale_host():
    try:
        status=json.loads(subprocess.run(['tailscale','status','--json'],capture_output=True,text=True,timeout=10).stdout)
        return status['Self']['DNSName'].rstrip('.')
    except Exception:return ''

def status(_):
    cloud=brain.config(DATA)
    print(f"{ok(cloud)} Brain: {brain.label(DATA)}"+('' if cloud else '  → run: python3 jarvis_setup.py brain openai'))
    if cloud:print(f"   reachable: {ok(brain.cloud_ready(DATA))}")
    tools=assistant_jobs.known_tools(Core)
    print(f"{ok(assistant_jobs.available())} Hands (Claude Code): {len(assistant_jobs.readonly(tools))} read-only tools auto-allowed of {len(tools)} known")
    print(f"{ok(notify.ready(DATA))} Telegram: {'reusing Claude Code Telegram bot' if notify.ready(DATA) and not (DATA/'telegram.json').exists() else 'configured' if notify.ready(DATA) else 'not configured'}")
    settings=phone.config(DATA)
    print(f"{ok(settings)} Phone: "+(f"{settings['from_number']} → {settings['my_number']} via {settings['public_url']}" if settings else 'not configured → run: python3 jarvis_setup.py twilio'))
    import sqlite3
    try:
        db=sqlite3.connect(DATA/'history.sqlite3')
        for row in db.execute('SELECT label,repeat,at,window,deliver,enabled FROM schedules ORDER BY enabled DESC'):
            print(f"   {ok(row[5])} schedule: {row[0]} · {row[1]} {row[2] or row[3]} · {row[4]}")
    except sqlite3.Error:print('   (schedules appear after the companion restarts)')

def ask_secret(prompt,env=None):
    if env and os.environ.get(env):
        use=input(f'{prompt}: use the {env} already in your shell? [Y/n] ').strip().lower()
        if use in {'','y','yes'}:return os.environ[env].strip()
    return getpass.getpass(prompt+' (hidden): ').strip()

def try_model(base_url,model,secret,body=None):
    cloud={'base_url':base_url,'model':model,'key':secret,'body':body or {}}
    meter={};start=time.monotonic()
    reply=brain.cloud_chat(cloud,{'messages':[{'role':'user','content':'Say: Good evening, sir.'}],'options':{'num_predict':20}},threading.Event(),lambda t:None,meter)
    return reply.get('content','').strip(),meter['calls'][0]['first_token'],time.monotonic()-start

def setup_brain(args):
    preset=brain.PRESETS[args.provider]
    model=args.model or preset['model']
    secret=ask_secret(f'{args.provider} API key','OPENAI_API_KEY' if args.provider=='openai' else None)
    if not secret:raise SystemExit('No key entered.')
    print(f'Testing {model}…')
    try:text,first,total=try_model(preset['base_url'],model,secret)
    except brain.CloudError as error:raise SystemExit(f'❌ The provider refused the test call: {error}\nNothing was saved. (For OpenAI "no credits": add a few dollars at platform.openai.com → Billing.)')
    print(f'✅ "{text}"  first token {first:.2f}s, total {total:.2f}s')
    brain.save(DATA,preset['base_url'],model,secret)
    print('Saved. Jarvis uses it on the next turn (no restart needed).')

def bench(_):
    cloud=brain.config(DATA)
    if not cloud:raise SystemExit('Configure a brain first.')
    import companion_tools
    candidates={'api.openai.com':['gpt-4.1-mini','gpt-5.4-mini','gpt-5.4-nano'],'api.groq.com':['openai/gpt-oss-120b','openai/gpt-oss-20b','llama-3.3-70b-versatile'],
      'api.anthropic.com':['claude-haiku-5-5','claude-sonnet-5-5']}
    host=cloud['base_url'].split('//')[-1].split('/')[0]
    cases=[('Remember this decision: use cyan accents.','save_memory'),('What is on my calendar tomorrow?','delegate_task'),
      ('Remind me at 5pm to call mum.','schedule_task'),('Is the scoreboard build finished?','job_status')]
    for model in candidates.get(host,[cloud['model']]):
        extra={'reasoning_effort':'none'} if model.startswith('gpt-5') else {}
        firsts=[];right=0
        for text,want in cases:
            try:
                meter={}
                result=brain.cloud_chat({**cloud,'model':model,'body':extra},{'messages':[{'role':'system','content':companion_tools.system_prompt()},{'role':'user','content':text}],
                  'tools':companion_tools.TOOLS,'options':{'num_predict':200,'temperature':.2}},threading.Event(),lambda t:None,meter)
                firsts.append(meter['calls'][0]['first_token'])
                right+=any(c['function']['name']==want for c in result.get('tool_calls',[]))
            except brain.CloudError as error:print(f'  {model}: {error}');break
        if firsts:print(f'{model:28} first token avg {sum(firsts)/len(firsts):.2f}s · right tool {right}/{len(cases)}')
    print('Switch with: python3 jarvis_setup.py brain <provider> --model NAME')

def telegram_test(_):
    print(ok(notify.send(Core,'Test from your Jarvis setup. Proactive updates will arrive here.'))+' Telegram test message')

def twilio(_):
    print('From the Twilio console (console.twilio.com): Account SID, Auth Token, and your Twilio phone number.')
    sid=input('Account SID: ').strip()
    token=getpass.getpass('Auth Token (hidden): ').strip()
    from_number=input('Your Twilio number (e.g. +15551234567): ').strip()
    my_number=input('YOUR mobile number Jarvis should call and accept calls from: ').strip()
    host=tailscale_host()
    default=f'https://{host}:10000' if host else ''
    public=input(f'Public URL [{default}]: ').strip() or default
    auth=base64.b64encode(f'{sid}:{token}'.encode()).decode()
    try:
        with urlopen(Request(f'https://api.twilio.com/2010-04-01/Accounts/{sid}/IncomingPhoneNumbers.json?'+urlencode({'PhoneNumber':from_number}),headers={'Authorization':'Basic '+auth}),timeout=15) as response:
            numbers=json.load(response).get('incoming_phone_numbers',[])
    except Exception as error:raise SystemExit(f'❌ Twilio rejected those credentials or that number: {error}')
    if not numbers:raise SystemExit('❌ That number is not on this Twilio account.')
    body=urlencode({'VoiceUrl':public.rstrip('/')+'/twilio/voice','VoiceMethod':'POST'}).encode()
    with urlopen(Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/IncomingPhoneNumbers/{numbers[0]['sid']}.json",data=body,headers={'Authorization':'Basic '+auth}),timeout=15):pass
    path=DATA/'twilio.json'
    path.write_text(json.dumps({'account_sid':sid,'auth_token':token,'from_number':from_number,'my_number':my_number,'public_url':public.rstrip('/')},indent=1));os.chmod(path,0o600)
    print(f'✅ Saved, and pointed {from_number} at {public}/twilio/voice')
    print('\nNext, publish ONLY the phone bridge to the internet (Twilio must reach it):')
    print(f'   tailscale funnel --bg --https=10000 http://127.0.0.1:{phone.PORT}')
    print('Then restart Jarvis:  python3 jarvis_setup.py restart')

def call_test(_):
    # The call must be placed by the running companion: it owns the bridge that answers Twilio.
    port=os.environ.get('VOICE_PORT','4321')
    request=Request(f'http://127.0.0.1:{port}/api/phone/call',data=b'{}',headers={'Content-Type':'application/json','X-Voice-Client':'1'})
    try:
        with urlopen(request,timeout=30) as response:print('✅',json.load(response))
    except Exception as error:
        detail=getattr(error,'read',lambda:b'')().decode(errors='replace')
        raise SystemExit(f'❌ Jarvis could not place the call: {error} {detail}'.strip())

def restart(_):
    subprocess.run(['launchctl','kickstart','-k',f'gui/{os.getuid()}/{LABEL}'],check=True)
    print('Jarvis restarted.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('status').set_defaults(run=status)
    b=sub.add_parser('brain');b.add_argument('provider',nargs='?',default='openai',choices=list(brain.PRESETS));b.add_argument('--model');b.set_defaults(run=setup_brain)
    sub.add_parser('bench').set_defaults(run=bench)
    sub.add_parser('telegram-test').set_defaults(run=telegram_test)
    sub.add_parser('twilio').set_defaults(run=twilio)
    sub.add_parser('call-test').set_defaults(run=call_test)
    sub.add_parser('restart').set_defaults(run=restart)
    args=parser.parse_args();args.run(args)
