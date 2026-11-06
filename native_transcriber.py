"""Cancellable whisper.cpp adapter. Audio and temporary transcripts stay local."""
import json, re, subprocess, tempfile, threading, time, wave
from pathlib import Path

def speech_text(segments):
    text=''.join(s.get('text','') for s in segments).strip()
    labels={'blank_audio','silence','music','noise','background noise','static','static noise',
      'water running','running water','wind','wind blowing','wind noise','applause','laughter',
      'soft music','quiet music','loud music','background music','instrumental music',
      'upbeat music','gentle music','dramatic music','rustling','beeping','humming'}
    # Only whole annotation labels are removed. Spoken sentences mentioning sounds remain intact.
    tokens=re.findall(r'\(([^()]*)\)|\[([^\[\]]*)\]',text)
    remainder=re.sub(r'\([^()]*\)|\[[^\[\]]*\]','',text).strip()
    if tokens and not remainder and all((a or b).strip().casefold() in labels for a,b in tokens):return ''
    return text

class NativeTranscriber:
    def __init__(self,binary,model):
        self.binary=str(binary);self.model=Path(model);self.lock=threading.Lock();self.process=None
    def close(self):
        process=self.process
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=2)
            except subprocess.TimeoutExpired:process.kill();process.wait()
    def call(self,job,stop,timeout=120):
        with self.lock:
            if stop.is_set():raise InterruptedError()
            if not self.model.is_file():raise RuntimeError('Native Whisper model is missing.')
            with tempfile.TemporaryDirectory(prefix='jarvis-transcription-') as temporary:
                output=Path(temporary)/'result'
                source=job.get('source')
                if job.get('warm'):
                    source=str(Path(temporary)/'warm.wav')
                    with wave.open(source,'wb') as audio:
                        audio.setparams((1,2,16000,0,'NONE','not compressed'));audio.writeframes(b'\0\0'*16000)
                command=[self.binary,'-m',str(self.model),'-f',str(source),'-l','en','-oj','-of',str(output),'-np']
                with (Path(temporary)/'diagnostics.log').open('wb') as diagnostics:
                    process=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=diagnostics)
                    self.process=process;deadline=time.monotonic()+timeout
                    try:
                        while process.poll() is None:
                            if stop.wait(.05):raise InterruptedError()
                            if time.monotonic()>deadline:raise TimeoutError('Native transcription timed out.')
                        if stop.is_set():raise InterruptedError()
                        if process.returncode:raise RuntimeError('Native transcription failed.')
                        if job.get('warm'):return {'ready':True}
                        result=json.loads(output.with_suffix('.json').read_text())
                        segments=result.get('transcription')
                        if not isinstance(segments,list):raise ValueError('Invalid transcription result.')
                        text=speech_text(segments)
                        # whisper.cpp applies its own no-speech threshold; do not invent probabilities.
                        return {'text':text,'segments':[]}
                    finally:
                        self.close();self.process=None
