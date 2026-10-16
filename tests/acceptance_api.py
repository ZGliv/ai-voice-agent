"""Opt-in real local acceptance; uses only synthetic fixtures, deletes its own conversations."""
import io,json,time,wave,urllib.request,urllib.error,concurrent.futures
from pathlib import Path
BASE='http://127.0.0.1:4321/api'
def call(path,data=None,method=None,headers=None):
    if isinstance(data,dict):data=json.dumps(data).encode()
    request=urllib.request.Request(BASE+path,data=data,method=method,headers={'X-Voice-Client':'1','Content-Type':'application/json',**(headers or {})})
    try:
        with urllib.request.urlopen(request,timeout=20) as response:return response.status,json.load(response)
    except urllib.error.HTTPError as error:return error.code,json.load(error)
def wait(tid,expected):
    deadline=time.monotonic()+100
    while time.monotonic()<deadline:
        _,t=call('/turns/'+tid)
        if t['status'] not in {'queued','transcribing','thinking','synthesizing'}:
            assert t['status']==expected,t;return t
        time.sleep(.3)
    raise AssertionError('Turn timed out')
if __name__=='__main__':
    c=call('/conversations',{},'POST')[1];cid=c['id'];results={}
    try:
        audio=Path('tests/synthetic-prompt.wav').read_bytes()
        _,t=call('/audio?conversation_id='+cid,audio,'POST')
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            t=call('/turns/'+t['id'])[1]
            if t['status']=='transcribing':break
            time.sleep(.1)
        time.sleep(2)  # Allow the actual Whisper child to begin before cancelling.
        start=time.monotonic();call('/turns/'+t['id']+'/cancel',{},'POST');cancelled=wait(t['id'],'cancelled')
        results['cancel_latency']=round(time.monotonic()-start,2);assert not cancelled['has_audio'];assert not cancelled['output_text']
        call('/turns/'+t['id']+'/retry',{},'POST');retried=wait(t['id'],'complete')
        assert 'synthetic test recording' in retried['input_text'].lower();results['retry_transcript']=retried['input_text']
        # Silence and invalid input must never become invented transcripts.
        buf=io.BytesIO()
        with wave.open(buf,'wb') as wav:wav.setparams((1,2,16000,0,'NONE','not compressed'));wav.writeframes(b'\0\0'*32000)
        _,silent=call('/audio?conversation_id='+cid,buf.getvalue(),'POST');silent=wait(silent['id'],'failed');assert not silent['input_text'];results['silence_error']=silent['error']
        _,bad=call('/audio?conversation_id='+cid,b'not an audio file','POST');bad=wait(bad['id'],'failed');assert not bad['input_text'];results['invalid_error']=bad['error']
        def submit():return call('/turns',{'conversation_id':cid,'text':'This is a synthetic concurrency test. Say hello in one sentence.'},'POST')
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:race=list(pool.map(lambda _:submit(),range(2)))
        assert sorted(x[0] for x in race)==[202,409],race
        accepted=next(x[1] for x in race if x[0]==202);wait(accepted['id'],'complete');results['concurrency_statuses']=[x[0] for x in race]
        assert call('/health',headers={'Origin':'https://unrelated.example'})[0]==403
        assert call('/health',headers={'Host':'attacker.example'})[0]==403
        assert call('/record',{},'POST')[0]==404
        results['cross_origin_and_host_rejected']=True;results['host_microphone_endpoint_absent']=True
        exported=call('/conversations/'+cid+'/export')[1];assert len(exported['turns'])==4;results['export_turns']=len(exported['turns'])
    finally:
        while call('/health')[1].get('active'):time.sleep(.2)
        status,_=call('/conversations/'+cid,None,'DELETE');assert status==200
        assert call('/conversations/'+cid)[0]==404
    Path('output/acceptance-api.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
