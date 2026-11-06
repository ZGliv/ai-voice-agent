"""Bounded browser checks against a generated loopback preview, using an existing session."""
import json,re,shutil,subprocess
from pathlib import Path
from urllib.parse import urlparse

def load_steps(workspace):
    path=workspace/'.jarvis-checks.json'
    if not path.is_file():return []
    if path.is_symlink() or path.stat().st_size>20000:raise ValueError('Invalid browser check file.')
    steps=json.loads(path.read_text())
    if not isinstance(steps,list) or len(steps)>12:raise ValueError('Browser checks must be a list of at most 12 steps.')
    total_wait=0
    for step in steps:
        if not isinstance(step,dict) or step.get('action') not in {'click','fill','expect_text','expect_not_text','expect_value','visible','wait'}:raise ValueError('Unsupported browser check action.')
        if step['action']=='wait':
            ms=step.get('ms')
            if not isinstance(ms,int) or not 0<=ms<=2000:raise ValueError('Each wait must be between zero and 2000 milliseconds.')
            total_wait+=ms
        else:
            if not isinstance(step.get('selector'),str) or not 1<=len(step['selector'])<=300:raise ValueError('A check needs a bounded selector.')
            if step['action'] in {'fill','expect_text','expect_not_text','expect_value'} and (not isinstance(step.get('text'),str) or len(step['text'])>1000):raise ValueError('Invalid expected text.')
    if total_wait>8000:raise ValueError('Browser waits exceed eight seconds.')
    return steps

def verify(core,job,url,steps_override=None,attempt='initial'):
    config=core.DATA/'browser-session'
    if not config.is_file():return {'status':'unavailable','summary':'Browser verification is not configured.'}
    session=config.read_text().strip()
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',session) or not shutil.which('npx'):return {'status':'unavailable','summary':'The configured browser session is unavailable.'}
    parsed=urlparse(url)
    if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or not parsed.port:raise ValueError('Only the generated loopback preview can be tested.')
    workspace=Path(job['worktree'])
    try:steps=load_steps(workspace) if steps_override is None else steps_override
    except (ValueError,OSError) as error:return {'status':'failed','summary':str(error)}
    if attempt not in {'initial','repair'}:raise ValueError('Invalid verification attempt.')
    output=core.DATA/'jobs'/job['id']/'verification'/attempt;output.mkdir(parents=True,exist_ok=True,mode=0o700)
    options={'url':url,'steps':steps,'directory':str(output)}
    script=(Path(__file__).parent/'preview_verifier.js').read_text().replace('__JARVIS_OPTIONS__',json.dumps(options))
    try:
        result=subprocess.run(['npx','--no-install','--package','@playwright/cli','playwright-cli','--session',session,'run-code',script],capture_output=True,text=True,timeout=90)
        match=re.search(r'### Result\s*\n(.*?)\n### ',result.stdout,re.S)
        if result.returncode or not match:raise ValueError('No browser verification result.')
        report=json.loads(match[1]);assert report.get('status') in {'passed','smoke_passed','failed'}
        (output/'report.json').write_text(json.dumps(report,indent=2))
        return report
    except (OSError,ValueError,AssertionError,subprocess.TimeoutExpired):
        return {'status':'unavailable','summary':'Browser verification could not run. Open the existing browser session and retry; this is not a pass.'}
