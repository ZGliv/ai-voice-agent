"""Conversation model: a configured OpenAI-compatible cloud model, else local Ollama.

Config lives in the private data directory (never the repository):
  brain.json      {"base_url": "...", "model": "...", "body": {...extra request fields}}
  brain-api-key   the provider key, owner-only permissions
JARVIS_LLM_API_KEY overrides the key file. Without a key, the local model is used.
"""
import json, os, queue, socket, threading, time, uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import local_runtime

OLLAMA='http://127.0.0.1:11434'
LOCAL_MODEL='qwen3:8b'
DEFAULTS={'base_url':'https://api.openai.com/v1','model':'gpt-4.1-mini','body':{}}
PRESETS={
 'openai':{'base_url':'https://api.openai.com/v1','model':'gpt-4.1-mini'},
 'groq':{'base_url':'https://api.groq.com/openai/v1','model':'openai/gpt-oss-120b'},
 'anthropic':{'base_url':'https://api.anthropic.com/v1','model':'claude-haiku-5-5'},
 'openrouter':{'base_url':'https://openrouter.ai/api/v1','model':'openai/gpt-4.1-mini'},
}

class CloudError(Exception):pass

def key(data):
    if os.environ.get('JARVIS_LLM_API_KEY'):return os.environ['JARVIS_LLM_API_KEY'].strip()
    try:return (data/'brain-api-key').read_text().strip() or None
    except OSError:return None

def config(data):
    """Cloud settings, or None when no key is configured (local model)."""
    secret=key(data)
    if not secret:return None
    try:saved=json.loads((data/'brain.json').read_text())
    except (OSError,ValueError):saved={}
    merged={**DEFAULTS,**{k:v for k,v in saved.items() if k in DEFAULTS}}
    merged['base_url']=merged['base_url'].rstrip('/')
    return {**merged,'key':secret}

def save(data,base_url,model,secret=None,body=None):
    data.mkdir(parents=True,exist_ok=True,mode=0o700)
    (data/'brain.json').write_text(json.dumps({'base_url':base_url.rstrip('/'),'model':model,'body':body or {}},indent=1))
    os.chmod(data/'brain.json',0o600)
    if secret is not None:
        path=data/'brain-api-key';path.write_text(secret.strip());os.chmod(path,0o600)

def label(data):
    cloud=config(data)
    return cloud['model']+' · '+(cloud['base_url'].split('//')[-1].split('/')[0]) if cloud else LOCAL_MODEL+' · local'

def to_openai(messages):
    """Ollama-style history -> OpenAI chat messages with matched tool_call ids."""
    out=[];pending=[]
    def close():
        # Calls beyond the per-round limit were never executed; say so explicitly.
        for cid in pending:out.append({'role':'tool','tool_call_id':cid,'content':json.dumps({'error':'Not run: action limit for this round.'})})
        pending.clear()
    for message in messages:
        role=message.get('role')
        if role=='tool':
            if pending:out.append({'role':'tool','tool_call_id':pending.pop(0),'content':message.get('content','')})
            else:out.append({'role':'user','content':'Tool result ('+str(message.get('tool_name',''))+', reference data): '+message.get('content','')})
            continue
        close()
        if role=='assistant' and message.get('tool_calls'):
            calls=[]
            for call in message['tool_calls']:
                function=call.get('function',{});cid=call.get('id') or 'call_'+uuid.uuid4().hex[:24]
                arguments=function.get('arguments',{})
                calls.append({'id':cid,'type':'function','function':{'name':function.get('name',''),'arguments':arguments if isinstance(arguments,str) else json.dumps(arguments)}})
                pending.append(cid)
            out.append({'role':'assistant','content':message.get('content') or None,'tool_calls':calls})
        else:out.append({'role':role,'content':message.get('content','')})
    close()
    return out

def request_body(cloud,payload):
    options=payload.get('options',{})
    body={'model':cloud['model'],'messages':to_openai(payload['messages']),'stream':True}
    if 'api.openai.com' in cloud['base_url']:body['stream_options']={'include_usage':True}
    if payload.get('tools'):body['tools']=payload['tools']
    if 'num_predict' in options:body['max_completion_tokens' if 'api.openai.com' in cloud['base_url'] else 'max_tokens']=options['num_predict']
    if 'temperature' in options and not cloud['model'].startswith(('gpt-5','o1','o3','o4')):body['temperature']=options['temperature']
    body.update(cloud.get('body') or {})
    return body

def cloud_chat(cloud,payload,stop,on_text,meter=None):
    events=queue.Queue();abandoned=threading.Event();connection=[]
    started=time.monotonic()
    def read():
        try:
            request=Request(cloud['base_url']+'/chat/completions',data=json.dumps(request_body(cloud,payload)).encode(),
              headers={'Content-Type':'application/json','Authorization':'Bearer '+cloud['key']})
            with urlopen(request,timeout=20) as response:
                connection.append(response)
                for line in response:
                    if abandoned.is_set():break
                    line=line.strip()
                    if not line.startswith(b'data:'):continue
                    line=line[5:].strip()
                    if line==b'[DONE]':break
                    events.put(json.loads(line))
        except HTTPError as error:
            try:detail=json.loads(error.read()).get('error',{})
            except Exception:detail={}
            finally:error.close()
            message=detail.get('message','') if isinstance(detail,dict) else str(detail)
            events.put(CloudError(f'{error.code} {message}'[:240]))
        except Exception as error:events.put(CloudError(type(error).__name__+': '+str(error)[:200]))
        finally:events.put(None)
    threading.Thread(target=read,daemon=True).start()
    content='';calls={};last=0;first=None;usage={};deadline=time.monotonic()+120
    try:
        while True:
            if stop.is_set():raise InterruptedError()
            if time.monotonic()>deadline:raise CloudError('Cloud model timed out')
            try:event=events.get(timeout=.05)
            except queue.Empty:continue
            if event is None:break
            if isinstance(event,Exception):raise event
            if event.get('usage'):usage=event['usage']
            for choice in event.get('choices') or []:
                delta=choice.get('delta') or {}
                if delta.get('content'):
                    content+=delta['content']
                    if first is None:first=time.monotonic()-started
                for part in delta.get('tool_calls') or []:
                    if first is None:first=time.monotonic()-started
                    slot=calls.setdefault(part.get('index',len(calls)),{'id':'','name':'','arguments':''})
                    slot['id']=part.get('id') or slot['id']
                    function=part.get('function') or {}
                    slot['name']+=function.get('name') or ''
                    slot['arguments']+=function.get('arguments') or ''
            if content and not calls and time.monotonic()-last>.12:
                on_text(content);last=time.monotonic()
        if not content and not calls:raise CloudError('Empty model response')
        if meter is not None:
            meter.setdefault('calls',[]).append({'first_token':round(first or 0,3),'total':round(time.monotonic()-started,3),
              'input_tokens':usage.get('prompt_tokens',0),'output_tokens':usage.get('completion_tokens',0)})
        if not calls:return {'role':'assistant','content':content}
        parsed=[]
        for index in sorted(calls):
            slot=calls[index]
            try:arguments=json.loads(slot['arguments'] or '{}')
            except ValueError:arguments={}
            parsed.append({'id':slot['id'] or 'call_'+uuid.uuid4().hex[:24],'function':{'name':slot['name'],'arguments':arguments if isinstance(arguments,dict) else {}}})
        return {'role':'assistant','content':content,'tool_calls':parsed}
    finally:
        abandoned.set()
        for response in connection:
            try:response.fp.raw._sock.shutdown(socket.SHUT_RDWR)
            except (AttributeError,OSError):pass
            response.close()

def chat(data,payload,stop,on_text,meter=None):
    """Same contract as local_runtime.chat: returns an Ollama-style assistant message."""
    cloud=config(data)
    if cloud:
        if meter is not None:meter['model']=cloud['model']
        streamed=[]
        def guarded(text):
            streamed.append(True);on_text(text)
        try:return cloud_chat(cloud,payload,stop,guarded,meter)
        except CloudError as error:
            # Fall back only if nothing has been spoken yet; a half-streamed reply cannot be replaced silently.
            if streamed:raise RuntimeError('The cloud model stopped mid-reply.') from None
            if meter is not None:meter['fallback']=str(error)
    local={**payload,'model':LOCAL_MODEL,'think':False,'keep_alive':-1}
    local['options']={'num_ctx':8192,**payload.get('options',{})}
    if meter is not None:meter.setdefault('model',LOCAL_MODEL);meter['local']=True
    started=time.monotonic()
    reply=local_runtime.chat(OLLAMA+'/api/chat',local,stop,on_text)
    if meter is not None:meter.setdefault('calls',[]).append({'total':round(time.monotonic()-started,3),'local':True})
    return reply

def cloud_ready(data):
    cloud=config(data)
    if not cloud:return None
    headers={'Authorization':'Bearer '+cloud['key']}
    # Anthropic's model list is its native API, which authenticates differently from its OpenAI-compatible chat endpoint.
    if 'api.anthropic.com' in cloud['base_url']:headers={'x-api-key':cloud['key'],'anthropic-version':'2023-06-01'}
    try:
        with urlopen(Request(cloud['base_url']+'/models',headers=headers),timeout=3) as response:return response.status==200
    except Exception:return False
