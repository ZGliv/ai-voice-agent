"""Proactive schedule: reminders, a morning briefing and an inbox watch.

Reminders deliver their text directly. Tasks run through the assistant and deliver its
answer (watch tasks stay silent when nothing needs attention). Delivery is Telegram, or
a phone call when the schedule asks for one or the answer is marked URGENT.
"""
import json, re, threading, time, uuid
from datetime import datetime, timedelta

POLL=20
STOP=threading.Event()
DEFAULTS=[
 {'id':'morning-briefing','kind':'task','label':'Morning briefing','repeat':'daily','at':'07:30','window':'','deliver':'telegram','quiet':0,
  'task':'Morning briefing for Zack: today\'s calendar events with times and locations, important unread emails that need a reply or action, and anything due today. Lead with the single most important thing. Keep it tight.'},
 {'id':'inbox-watch','kind':'task','label':'Inbox watch','repeat':'30min','at':'','window':'08:00-22:00','deliver':'telegram','quiet':1,
  'task':'Check Zack\'s email and calendar for anything new since {since} that genuinely needs his attention: a reply from a real person, a deadline, a meeting change, a payment or security alert. Ignore newsletters, promotions, job-board alerts and automatic application confirmations. '
   'If nothing qualifies, reply with exactly NOTHING. '
   'Phone him (begin your answer with URGENT:) when it is worth interrupting him: a recruiter or employer replying about an interview, an offer or next steps; anything that needs action within two hours; a calendar event starting in the next 45 minutes that changed or that he may not know about; a security or payment alert. '
   'After URGENT:, write exactly what JARVIS should say when Zack picks up: one or two short spoken sentences with the news (who and what, no email addresses or links), then one concrete offer of the next step you could take, such as "Shall I draft a reply suggesting Tuesday at ten?". '
   'Draft nothing and send nothing now; he answers on the call. For everything else that qualifies, write a short Telegram summary instead.'},
]
# Earlier built-in wording, upgraded in place so an untouched default picks up improvements.
RETIRED={'inbox-watch':['Check Zack\'s email and calendar for anything new since {since} that genuinely needs his attention: a reply from a real person, a deadline, a meeting change, a payment or security alert. Ignore newsletters, promotions and routine notifications. If nothing qualifies, reply with exactly NOTHING. If something needs action within two hours, begin your answer with URGENT:']}

def initialize(db):
    db.execute('''CREATE TABLE IF NOT EXISTS schedules(id TEXT PRIMARY KEY,kind TEXT NOT NULL,label TEXT NOT NULL,task TEXT NOT NULL,
      repeat TEXT NOT NULL,at TEXT DEFAULT '',window TEXT DEFAULT '',deliver TEXT DEFAULT 'telegram',quiet INTEGER DEFAULT 0,
      enabled INTEGER DEFAULT 1,next_run REAL,last_run REAL DEFAULT 0,created REAL)''')
    for item in DEFAULTS:
        row=db.execute('SELECT task FROM schedules WHERE id=?',(item['id'],)).fetchone()
        if row and row[0] in RETIRED.get(item['id'],[]):
            db.execute('UPDATE schedules SET task=?,repeat=?,window=?,next_run=? WHERE id=?',(item['task'],item['repeat'],item['window'],next_run(item,time.time()),item['id']))
        if not row:
            db.execute('INSERT INTO schedules(id,kind,label,task,repeat,at,window,deliver,quiet,enabled,next_run,created) VALUES(:id,:kind,:label,:task,:repeat,:at,:window,:deliver,:quiet,1,:next_run,:created)',
              {**item,'next_run':next_run(item,time.time()),'created':time.time()})

def parse_hm(value):
    match=re.fullmatch(r'([01]?\d|2[0-3]):([0-5]\d)',value or '')
    if not match:raise ValueError('Use a 24-hour time like 07:30.')
    return int(match[1]),int(match[2])

def next_run(item,after):
    now=datetime.fromtimestamp(after).astimezone()
    if item['repeat']=='once':
        when=datetime.fromisoformat(item['at'])
        if when.tzinfo is None:when=when.astimezone()
        return when.timestamp()
    if item['repeat']=='daily':
        hour,minute=parse_hm(item['at'])
        when=now.replace(hour=hour,minute=minute,second=0,microsecond=0)
        return (when if when.timestamp()>after else when+timedelta(days=1)).timestamp()
    if item['repeat'] in {'hourly','30min'}:
        step=timedelta(minutes=30 if item['repeat']=='30min' else 60)
        start,end=(parse_hm(x) for x in (item.get('window') or '00:00-23:59').split('-'))
        when=now.replace(minute=0,second=0,microsecond=0)
        while when.timestamp()<=after:when+=step
        for _ in range(96):
            if start<=(when.hour,when.minute)<=end:return when.timestamp()
            when+=step
    raise ValueError('Unknown repeat '+str(item.get('repeat')))

def describe(row):
    when=datetime.fromtimestamp(row['next_run']).astimezone().strftime('%a %d %b %H:%M') if row['next_run'] else 'not scheduled'
    return {'id':row['id'],'label':row['label'],'kind':row['kind'],'repeat':row['repeat'],'at':row['at'],'window':row['window'],
      'deliver':row['deliver'],'enabled':bool(row['enabled']),'next':when}

def listing(core):
    with core.connect() as db:return [describe(r) for r in db.execute('SELECT * FROM schedules ORDER BY enabled DESC,next_run')]

def create(core,kind,label,task,repeat,at,deliver='telegram',window=''):
    if kind not in {'reminder','task'}:raise core.Problem('Kind must be reminder or task.')
    if repeat not in {'once','daily','hourly'}:raise core.Problem('Repeat must be once, daily or hourly.')
    if deliver not in {'telegram','call'}:raise core.Problem('Deliver by telegram or call.')
    if not isinstance(task,str) or not 2<=len(task.strip())<=2000:raise core.Problem('Describe the reminder or task in up to 2,000 characters.')
    item={'id':uuid.uuid4().hex[:12],'kind':kind,'label':(label or task)[:80],'task':task.strip(),'repeat':repeat,'at':at or '','window':window or '','deliver':deliver,'quiet':0}
    try:item['next_run']=next_run(item,time.time())
    except (ValueError,TypeError) as error:raise core.Problem('That time could not be understood: '+str(error)[:120])
    if item['next_run']<time.time()-60:raise core.Problem('That time has already passed.')
    with core.connect() as db:
        if db.execute('SELECT COUNT(*) FROM schedules WHERE enabled=1').fetchone()[0]>=50:raise core.Problem('Fifty active schedules is the limit. Remove one first.')
        db.execute('INSERT INTO schedules(id,kind,label,task,repeat,at,window,deliver,quiet,enabled,next_run,created) VALUES(:id,:kind,:label,:task,:repeat,:at,:window,:deliver,:quiet,1,:next_run,:created)',{**item,'created':time.time()})
        return describe(db.execute('SELECT * FROM schedules WHERE id=?',(item['id'],)).fetchone())

def change(core,sid,action,deliver=None,at=None):
    with core.connect() as db:
        row=db.execute('SELECT * FROM schedules WHERE id=?',(sid,)).fetchone()
        if not row:raise core.Problem('No schedule with that ID. List schedules first.')
        if action=='delete':
            db.execute('DELETE FROM schedules WHERE id=?',(sid,));return {'id':sid,'deleted':True}
        values={}
        if action in {'enable','disable'}:values['enabled']=int(action=='enable')
        if deliver:
            if deliver not in {'telegram','call'}:raise core.Problem('Deliver by telegram or call.')
            values['deliver']=deliver
        if at:
            values['at']=at
        if not values:raise core.Problem('Say enable, disable, delete, or give a new time or delivery.')
        item={**dict(row),**values}
        try:values['next_run']=next_run(item,time.time())
        except (ValueError,TypeError) as error:raise core.Problem('That time could not be understood: '+str(error)[:120])
        db.execute('UPDATE schedules SET '+','.join(k+'=?' for k in values)+' WHERE id=?',[*values.values(),sid])
        return describe(db.execute('SELECT * FROM schedules WHERE id=?',(sid,)).fetchone())

def deliver(core,row,text,urgent=False):
    import notify, phone
    sent=False
    if (row['deliver']=='call' or urgent) and phone.ready(core.DATA):
        try:phone.deliver(core,text);sent=True
        except Exception:pass
    return notify.send(core,('URGENT · ' if urgent else '')+row['label']+'\n\n'+text) or sent

def job_done(core,job):
    """Deliver a finished scheduled assistant task."""
    sid=job.get('source_turn_id','').split(':')[1]
    with core.connect() as db:row=db.execute('SELECT * FROM schedules WHERE id=?',(sid,)).fetchone()
    if not row:return
    text=(job.get('result') or '').strip()
    if job['status']!='completed' or not text:return
    if row['quiet'] and re.match(r'^\W*NOTHING\b',text,re.I):return
    urgent=bool(re.match(r'^\W*URGENT\s*:',text,re.I))
    deliver(core,row,re.sub(r'^\W*URGENT\s*:\s*','',text,flags=re.I) if urgent else text,urgent)

def tick(core,now=None):
    import assistant_jobs
    now=now or time.time()
    with core.connect() as db:due=list(db.execute('SELECT * FROM schedules WHERE enabled=1 AND next_run<=? ORDER BY next_run',(now,)))
    for row in due:
        if row['kind']=='reminder':
            deliver(core,row,row['task'])
        else:
            since=datetime.fromtimestamp(row['last_run'] or now-3600).astimezone().strftime('%A %H:%M')
            try:assistant_jobs.delegate(core,row['task'].replace('{since}',since),f"schedule:{row['id']}:{int(row['next_run'])}")
            except core.Problem as error:
                if error.status==409:continue  # Assistant busy; retry next poll without advancing.
        with core.connect() as db:
            if row['repeat']=='once':db.execute('UPDATE schedules SET enabled=0,last_run=? WHERE id=?',(now,row['id']))
            else:db.execute('UPDATE schedules SET next_run=?,last_run=? WHERE id=?',(next_run(dict(row),now),now,row['id']))

def start(core):
    def loop():
        while not STOP.wait(POLL):
            try:tick(core)
            except Exception:pass
    threading.Thread(target=loop,daemon=True).start()
