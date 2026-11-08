"""'Give me the rundown': what changed across Zack's projects, Jarvis's jobs and his day.

Everything here is local and instant: git history of each linked project, coding and
research jobs that finished, and the latest briefing (job search, Parl.ai, Notion).
"""
import json, subprocess, time
from datetime import datetime, timedelta
import briefing, codex_jobs, project_memory

def since_default(now=None):
    # Mornings look back to 6 pm yesterday ("overnight"); later in the day, the last 12 hours.
    now=datetime.fromtimestamp(now or time.time()).astimezone()
    if now.hour<12:return (now-timedelta(days=1)).replace(hour=18,minute=0,second=0,microsecond=0).timestamp()
    return (now-timedelta(hours=12)).timestamp()

def git_activity(path,since):
    stamp=datetime.fromtimestamp(since).astimezone().isoformat()
    try:out=subprocess.run(['git','log','--all','--no-merges','--since='+stamp,'--format=%s'],cwd=path,capture_output=True,text=True,timeout=10).stdout
    except (OSError,subprocess.SubprocessError):return None
    subjects=[line.strip()[:100] for line in out.splitlines() if line.strip()]
    return {'commits':len(subjects),'latest':subjects[:3]} if subjects else None

def gather(core,hours=None,now=None):
    now=now or time.time()
    since=now-float(hours)*3600 if hours else since_default(now)
    names={p['id']:p['name'] for p in project_memory.catalog()}
    projects={}
    for pid,path in codex_jobs.projects(core).items():
        activity=git_activity(path,since)
        if activity:projects[names.get(pid,pid)]=activity
    with core.connect() as db:
        rows=db.execute("SELECT project_id,task,status,branch,engine,error FROM codex_jobs WHERE updated>=? AND status IN ('completed','failed','awaiting_approval','interrupted') AND project_id!='__assistant__' ORDER BY updated DESC LIMIT 8",(since,)).fetchall()
    labels={**names,**codex_jobs.LABELS}
    jobs=[{'project':labels.get(r['project_id'],r['project_id']),'task':r['task'][:160],'status':r['status'],
      'by':'Claude Code' if r['engine']=='claude' else ('Codex' if r['project_id'] not in codex_jobs.STANDALONE else ''),
      'branch':r['branch'] or None,'problem':r['error'][:160] or None} for r in rows]
    saved=briefing.load(core.DATA)
    day=None
    if saved and now-saved.get('updated',0)<18*3600:
        day={**{k:v for k,v in saved['data'].items() if k!='opener'},'as_of':datetime.fromtimestamp(saved['updated']).astimezone().strftime('%-I:%M %p')}
    with core.connect() as db:
        running=[{'project':labels.get(r[0],r[0]),'task':r[1][:120]} for r in db.execute("SELECT project_id,task FROM codex_jobs WHERE status IN ('running','preparing') AND project_id!='__assistant__'")]
    return {'since':datetime.fromtimestamp(since).astimezone().strftime('%a %-I:%M %p'),'project_commits':projects,
      'jobs_finished':jobs,'jobs_still_running':running,'day':day,
      'linked_projects':[names.get(pid,pid) for pid in codex_jobs.projects(core)],
      'how_to_say_it':'Speak it as a short rundown: one line per project or area that changed, most important first, nothing that did not change. '
        'Then offer to start work: "Shall I get anything started?"'}
