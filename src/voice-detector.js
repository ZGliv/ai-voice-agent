// Local endpointing only. Raw idle audio is discarded and never uploaded.
export class VoiceDetector {
 constructor(rate){this.rate=rate;this.reset();this.noise=.003;}
 reset(){this.voiced=0;this.quiet=0;this.total=0;this.started=false;}
 feed(samples){
  const seconds=samples.length/this.rate;
  const rms=Math.sqrt(samples.reduce((sum,n)=>sum+n*n,0)/samples.length);
  const loud=rms>Math.max(.012,Math.min(.045,this.noise*3));
  if(!this.started&&!loud)this.noise=this.noise*.98+rms*.02;
  this.total+=seconds;
  if(loud){this.voiced+=seconds;this.quiet=0;}else{this.quiet+=seconds;if(!this.started)this.voiced=Math.max(0,this.voiced-seconds*.5);}
  if(this.voiced>=.18)this.started=true;
  return {rms,started:this.started,ended:this.started&&this.quiet>=.75,limit:this.started&&this.total>=55};
 }
}
// Barge-in uses echo-cancelled microphone audio only. A short calibration
// window learns residual speaker/background energy before accepting an onset.
export class InterruptionDetector {
 constructor(rate,noise=.003){this.rate=rate;this.elapsed=0;this.voiced=0;this.noise=noise;this.calibration=[];}
 feed(samples){
  const seconds=samples.length/this.rate;
  const rms=Math.sqrt(samples.reduce((sum,n)=>sum+n*n,0)/samples.length);
  this.elapsed+=seconds;
  if(this.calibration){
   this.calibration.push(rms);
   if(this.elapsed<.35)return false;
   // A click/cough during startup must not set the threshold for the whole reply.
   // Median still rejects sustained residual speaker energy during calibration.
   this.calibration.sort((a,b)=>a-b);
   this.noise=Math.max(this.noise,this.calibration[Math.floor(this.calibration.length/2)]);
   this.calibration=null;return false;
  }
  const loud=rms>Math.max(.03,this.noise*4);
  if(loud)this.voiced+=seconds;
  else{this.voiced=0;this.noise=this.noise*.98+rms*.02;}
  return this.voiced>=.24;
 }
}
export function wavBlob(chunks,rate){
 const length=chunks.reduce((sum,c)=>sum+c.length,0),buffer=new ArrayBuffer(44+length*2),view=new DataView(buffer);
 const text=(offset,s)=>[...s].forEach((c,i)=>view.setUint8(offset+i,c.charCodeAt(0)));
 text(0,'RIFF');view.setUint32(4,36+length*2,true);text(8,'WAVE');text(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,rate,true);view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);text(36,'data');view.setUint32(40,length*2,true);
 let offset=44;for(const chunk of chunks)for(const sample of chunk){view.setInt16(offset,Math.round(Math.max(-1,Math.min(1,sample))*32767),true);offset+=2;}
 return new Blob([buffer],{type:'audio/wav'});
}
