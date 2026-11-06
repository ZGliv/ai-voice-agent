// Small PCM jitter buffer. The server keeps provider credentials and saved audio.
export class StreamPlayback {
 constructor(context){this.context=context;this.output=context.createGain();this.sources=new Set();this.stopped=false;this.done=false;this.next=0;this.total=0;this.reader=null;this.onended=null;}
 connect(node){this.output.connect(node);}
 disconnect(){this.output.disconnect();}
 finish(){if(!this.stopped&&this.done&&!this.sources.size){this.stopped=true;this.onended?.();}}
 stop(){if(this.stopped)return;this.stopped=true;this.reader?.cancel().catch(()=>{});for(const s of this.sources){s.onended=null;s.stop();s.disconnect();}this.sources.clear();this.readyResolve?.(false);queueMicrotask(()=>this.onended?.());}
 async start(url,{signal,onError}={}){
  const ready=new Promise(resolve=>this.readyResolve=resolve);
  const abort=()=>this.stop();signal?.addEventListener('abort',abort,{once:true});
  this.run(url,signal).then(()=>{if(!this.total&&!this.stopped)throw Error('Empty audio stream');this.done=true;this.finish();}).catch(error=>{
   if(!this.stopped&&!signal?.aborted){onError?.(error);this.stop();}
   this.readyResolve(false);
  }).finally(()=>signal?.removeEventListener('abort',abort));
  return ready;
 }
 async run(url,signal){
  const response=await fetch(url,{signal,headers:{'X-Voice-Client':'1'}});
  if(!response.ok||!response.body){const error=Error('Audio stream unavailable');error.status=response.status;throw error;}
  this.reader=response.body.getReader();const decoder=new TextDecoder();let pending='',finished=false;
  while(!this.stopped){
   let timer;const result=await Promise.race([this.reader.read(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Audio stream stalled')),15000);})]).finally(()=>clearTimeout(timer));
   if(result.done)break;
   pending+=decoder.decode(result.value,{stream:true});
   let end;while((end=pending.indexOf('\n'))>=0){const line=pending.slice(0,end);pending=pending.slice(end+1);if(!line)continue;if(line.length>20000)throw Error('Invalid audio frame');const event=JSON.parse(line);
    if(event.error){const error=Error(event.error);error.serverFailure=true;throw error;}
    if(event.done){finished=true;continue;}
    if(event.audio){if(finished)throw Error('Audio after completion');this.enqueue(event.audio,event.sample_rate);}
   }
   if(pending.length>20000)throw Error('Invalid audio stream');
  }
  if(!this.stopped&&!finished)throw Error('Audio stream ended early');
 }
 enqueue(encoded,rate){
  if(this.stopped)return;
  if(!Number.isInteger(rate)||rate<8000||rate>48000)throw Error('Invalid audio rate');
  const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
  if(bytes.length%2||!bytes.length)throw Error('Invalid PCM chunk');
  this.total+=bytes.length;if(this.total>8*1024*1024)throw Error('Audio stream too large');
  const pcm=new DataView(bytes.buffer),buffer=this.context.createBuffer(1,bytes.length/2,rate),channel=buffer.getChannelData(0);
  for(let i=0;i<channel.length;i++)channel[i]=pcm.getInt16(i*2,true)/32768;
  const source=this.context.createBufferSource();source.buffer=buffer;source.connect(this.output);this.sources.add(source);
  source.onended=()=>{source.disconnect();this.sources.delete(source);this.finish();};
  const start=Math.max(this.context.currentTime+.08,this.next);this.next=start+buffer.duration;
  source.start(start);this.readyResolve?.(true);
 }
}
