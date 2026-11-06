import {wavBlob} from './voice-detector.js';
export class StreamingRecognition {
 constructor(api,ensureConversation,onEnd,onError){Object.assign(this,{api,ensureConversation,onEnd,onError});this.current=null;}
 feed(chunk,rate,voiced){
  const s=this.current??={id:crypto.randomUUID().replaceAll('-',''),sequence:0,queue:[],audio:[],pending:[],position:0,total:0,lastVoice:0,busy:false,closed:false};
  // Continuous sample position preserves phase across worklet blocks at any rate.
  const samples=[];for(let pos=s.position;pos<chunk.length;pos+=rate/24000)samples.push(chunk[Math.floor(pos)]);
  s.position=(s.position+Math.ceil((chunk.length-s.position)/(rate/24000))*(rate/24000))-chunk.length;
  s.pending.push(...samples);s.total+=samples.length;if(voiced)s.lastVoice=s.total;
  while(s.pending.length>=5760)s.queue.push(new Float32Array(s.pending.splice(0,5760)));
  if(s.queue.length>12){this.cancel();this.onError('Recognition cannot keep up. Tap the orb to reconnect.');return;}
  this.pump(s);
 }
 async pump(s){
  if(s.busy||s.closed||this.current!==s)return;s.busy=true;
  try{
   const cid=await this.ensureConversation();
   while(s.queue.length&&!s.closed&&this.current===s){
    const block=s.queue.shift();s.audio.push(block);const pcm=new Int16Array(block.length);
    for(let i=0;i<block.length;i++)pcm[i]=Math.round(Math.max(-1,Math.min(1,block[i]))*32767);
    const seq=s.sequence++;
    const result=await this.api(`/listen/${s.id}?conversation_id=${cid}&sequence=${seq}`,{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:pcm});
    if(s.closed||this.current!==s)return;
    if(result.end&&result.samples>=s.lastVoice&&s.total-s.lastVoice>=7200){
     // Use precisely the PCM accepted by the server, not newer queued audio.
     s.closed=true;this.current=null;
     this.onEnd(wavBlob(s.audio,24000),{'X-Voice-Stream':s.id,'X-Voice-Stream-Sequence':String(seq)});return;
    }
   }
  }catch(error){if(this.current===s){this.cancel();this.onError(error.message||'Streaming recognition stopped. Tap the orb to reconnect.');}}
  finally{s.busy=false;}
 }
 cancel(){const s=this.current;this.current=null;if(s){s.closed=true;this.api(`/listen/${s.id}`,{method:'DELETE'}).catch(()=>{});}}
}
