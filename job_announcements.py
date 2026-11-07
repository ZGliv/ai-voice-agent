"""Cached task-completion speech. Only assistant answers (meant for Zack) are read aloud; other worker output never is."""
import hashlib, re, threading
import fish_voice, speech_text
LOCK=threading.Lock()
TERMINAL={'completed','failed','interrupted','cancelled','awaiting_approval'}

def spoken_answer(text):
    # The assistant puts a short spoken answer first; read only that paragraph, bounded.
    first=speech_text.for_speech(text.strip().split('\n\n')[0])
    # Two sentences at most: anything longer is a monologue on the phone.
    first=' '.join(re.split(r'(?<=[.!?])\s+',first)[:2])
    if len(first)>300:first=first[:300].rsplit(' ',1)[0]+'.'
    return first

def message(job):
    if job['project_id']=='__assistant__':
        if job['status']=='awaiting_approval':
            return 'I need your approval before I go ahead. '+spoken_answer(job.get('result','') or '')+' Shall I proceed?'
        if job['status']=='completed' and job.get('result'):return spoken_answer(job['result'])
    if job['status']=='completed':
        if job.get('error'):return 'The task finished, but its checks need attention. Ask me for the details.'
        if job['project_id']=='__research__':return 'Your research report is ready. Ask me what I found.'
        if job.get('preview_dir'):return 'Your website preview is ready. You can review it in your task history.'
        return 'Your task has finished. The report is ready for review.'
    if job['status']=='cancelled':return 'The task has been cancelled.'
    return 'The task stopped before finishing. Ask me for its status.'

def audio_path(core,job):
    provider='fish-'+fish_voice.MODEL if fish_voice.key(core.DATA) else 'piper-'+str(core.PIPER_MODEL)
    digest=hashlib.sha256((provider+'\n'+message(job)).encode()).hexdigest()[:24]
    return core.DATA/'announcements'/(digest+'.wav')

def prepare(core,job):
    if job['status'] not in TERMINAL:raise core.Problem('The task is still running.',409)
    destination=audio_path(core,job)
    if destination.is_file():return destination
    if not LOCK.acquire(blocking=False):raise core.Problem('Another task announcement is being prepared.',409)
    pending=destination.with_suffix('.pending.wav')
    try:
        if core.CURRENT:raise core.Problem('Wait for the current reply.',409)
        destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        secret=fish_voice.key(core.DATA)
        try:
            if secret:fish_voice.synthesize(message(job),pending,secret,threading.Event())
            else:core.SPEECH.call({'text':message(job),'destination':str(pending)},threading.Event(),45)
        except Exception:raise core.Problem('The announcement could not be prepared. The task report is still available.',503) from None
        pending.replace(destination)
        return destination
    finally:
        pending.unlink(missing_ok=True);LOCK.release()
