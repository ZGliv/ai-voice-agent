"""Incremental free-model Fish TTS. Provider secrets never enter browser events."""
import queue,re,threading,time,wave
from pathlib import Path
import fish_voice,speech_text


def available():
    try:import msgpack;from websockets.sync.client import connect
    except ImportError:return False
    return True


class TextSpeech:
    def __init__(self,directory,secret,stop,on_audio=None):
        self.directory=Path(directory);self.secret=secret;self.stop=stop;self.on_audio=on_audio
        self.queue=queue.Queue(maxsize=128);self.abandoned=threading.Event();self.done=threading.Event()
        self.error=None;self.raw='';self.buffer='';self.started=time.monotonic();self.first_audio=None;self.first_text=None;self.text_done=None
        self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()
    def _put(self,value):
        if self.stop.is_set() or self.abandoned.is_set():raise InterruptedError()
        if self.error:raise self.error
        try:self.queue.put_nowait(value)
        except queue.Full:raise fish_voice.VoiceError('Speech text stream exceeded its buffer.')
    def feed(self,partial):
        if not partial.startswith(self.raw):raise fish_voice.VoiceError('The streamed answer changed unexpectedly.')
        if len(partial)>16000:raise fish_voice.VoiceError('The spoken answer is too long.')
        self.buffer+=partial[len(self.raw):];self.raw=partial
        while self.buffer:
            match=re.search(r'[.!?](?:\s|$)',self.buffer)
            boundary=match.end() if match else (self.buffer.rfind(' ',0,160)+1 if len(self.buffer)>160 else 0)
            if not boundary and self.first_text is None:
                # The first words matter most: start the voice at the first natural pause instead of the full sentence.
                pause=re.search(r'^(?:\S+\s+){2,}?\S+[,;:\u2014](?=\s)',self.buffer)
                if pause:boundary=pause.end()
                elif len(self.buffer.split())>10:boundary=self.buffer.rfind(' ')+1
            if not boundary:break
            self._text(self.buffer[:boundary]);self.buffer=self.buffer[boundary:]
    def _text(self,text):
        if not text.strip():return
        if self.first_text is None:self.first_text=time.monotonic()-self.started
        self._put(speech_text.for_speech(text)+' ')
    def finish(self,text):
        self.feed(text);self._text(self.buffer);self.buffer='';self.text_done=time.monotonic()-self.started;self._put(None)
    def wait(self):
        while not self.done.wait(.05):
            if self.stop.is_set():self.close();raise InterruptedError()
        if self.error:raise self.error
        return {'first_text':round(self.first_text or 0,3),'first_audio':round(self.first_audio or 0,3),'text_complete':round(self.text_done or 0,3),'total':round(time.monotonic()-self.started,3)}
    def close(self):
        self.abandoned.set();self.thread.join(timeout=1)
    def _run(self):
        try:
            import msgpack
            from websockets.sync.client import connect
            # Explicit model header is essential: Fish defaults to paid if it is absent.
            with connect('wss://api.fish.audio/v1/tts/live',additional_headers={'Authorization':'Bearer '+self.secret,'model':fish_voice.MODEL},open_timeout=10,close_timeout=1,max_size=2*1024*1024,compression=None) as ws:
                if self.abandoned.is_set() or self.stop.is_set():raise InterruptedError()
                send=lambda event:ws.send(msgpack.packb(event,use_bin_type=True))
                send({'event':'start','request':{'text':'','reference_id':fish_voice.VOICE,'format':'pcm','sample_rate':24000,'latency':'balanced'}})
                total=0;tail=b'';sent_stop=False;first=True
                with wave.open(str(self.directory/'reply.pending.wav'),'wb') as output,(self.directory/'reply.pcm').open('wb') as pcm:
                    output.setparams((1,2,24000,0,'NONE','not compressed'))
                    while True:
                        if self.abandoned.is_set() or self.stop.is_set():raise InterruptedError()
                        if time.monotonic()-self.started>120:raise fish_voice.VoiceError('Fish text streaming timed out. No paid fallback was used.')
                        if not sent_stop:
                            try:text=self.queue.get_nowait()
                            except queue.Empty:pass
                            else:
                                if text is None:send({'event':'stop'});sent_stop=True
                                else:
                                    send({'event':'text','text':text})
                                    if first:send({'event':'flush'});first=False
                        try:event=msgpack.unpackb(ws.recv(timeout=.03),raw=False)
                        except TimeoutError:continue
                        if event.get('event')=='audio':
                            audio=event.get('audio')
                            if not isinstance(audio,bytes):raise fish_voice.VoiceError('Fish returned invalid streamed audio.')
                            chunk=tail+audio;tail=chunk[len(chunk)//2*2:];chunk=chunk[:len(chunk)//2*2];total+=len(chunk)
                            if total>8*1024*1024:raise fish_voice.VoiceError('Fish returned oversized speech.')
                            if chunk:
                                output.writeframesraw(chunk);pcm.write(chunk);pcm.flush()
                                if self.first_audio is None:
                                    self.first_audio=time.monotonic()-self.started
                                    if self.on_audio:self.on_audio(self.first_audio)
                        elif event.get('event')=='finish':
                            if event.get('reason')!='stop' or not sent_stop or total<4800 or tail:raise fish_voice.VoiceError('Fish text streaming did not finish successfully. Your text is saved.')
                            break
                        elif event.get('event')=='error':raise fish_voice.VoiceError('Fish refused text streaming. No paid fallback was used.')
        except Exception as error:
            if isinstance(error,(fish_voice.VoiceError,InterruptedError)):self.error=error
            else:self.error=fish_voice.VoiceError('Fish text streaming is unavailable. No paid model was used; your answer remains saved for retry.')
        finally:
            self.secret='';self.done.set()
