"""Warm local speech processes and cancellable Ollama streaming."""
import json, queue, subprocess, threading, time, socket
from urllib.request import Request, urlopen

class Worker:
    def __init__(self, command):
        self.command=command; self.process=None; self.lock=threading.Lock(); self.lines=None
    def close(self):
        p=self.process; self.process=None
        if p and p.poll() is None:
            p.terminate()
            try:p.wait(timeout=2)
            except subprocess.TimeoutExpired:p.kill();p.wait()
        if p:
            for pipe in (p.stdin,p.stdout):
                if pipe:pipe.close()
    def call(self, job, stop, timeout=120):
        with self.lock:
            if stop.is_set():raise InterruptedError()
            if not self.process or self.process.poll() is not None:
                self.close();self.lines=queue.Queue()
                self.process=subprocess.Popen(self.command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,bufsize=1)
                def read(pipe, lines):
                    for line in pipe:lines.put(line)
                    lines.put(None)
                threading.Thread(target=read,args=(self.process.stdout,self.lines),daemon=True).start()
            self.process.stdin.write(json.dumps(job)+'\n');self.process.stdin.flush()
            deadline=time.monotonic()+timeout
            while True:
                if stop.is_set() or time.monotonic()>deadline:
                    self.close()
                    if stop.is_set():raise InterruptedError()
                    raise TimeoutError('Speech step timed out')
                try:line=self.lines.get(timeout=.1)
                except queue.Empty:continue
                if line is None: self.close();raise RuntimeError('Speech worker stopped')
                result=json.loads(line)
                if result.get('error'):raise RuntimeError(result['error'])
                return result

def chat(url, payload, stop, on_text):
    events=queue.Queue(); abandoned=threading.Event(); connection=[]
    def read():
        try:
            request=Request(url,data=json.dumps({**payload,'stream':True}).encode(),headers={'Content-Type':'application/json'})
            with urlopen(request,timeout=30) as response:
                connection.append(response)
                if abandoned.is_set():return
                for line in response:
                    if abandoned.is_set():break
                    events.put(json.loads(line))
        except Exception as error:events.put(error)
        finally:events.put(None)
    threading.Thread(target=read,daemon=True).start()
    content='';calls=[];last=0;deadline=time.monotonic()+180
    try:
        while True:
            if stop.is_set():raise InterruptedError()
            if time.monotonic()>deadline:raise TimeoutError('Model timed out')
            try:event=events.get(timeout=.1)
            except queue.Empty:continue
            if event is None:break
            if isinstance(event,Exception):raise event
            if event.get('error'):raise RuntimeError(event['error'])
            message=event.get('message',{});content+=message.get('content','');calls.extend(message.get('tool_calls',[]))
            if content and not calls and time.monotonic()-last>.12:
                on_text(content);last=time.monotonic()
        if not content and not calls:raise RuntimeError('Empty model response')
        return {'role':'assistant','content':content,'tool_calls':calls} if calls else {'role':'assistant','content':content}
    finally:
        abandoned.set()
        # Stop Ollama's generation as well as our reader. Otherwise cancelled
        # speculative turns keep occupying the model while the next turn waits.
        for response in connection:
            try:response.fp.raw._sock.shutdown(socket.SHUT_RDWR)
            except (AttributeError,OSError):pass
            response.close()
