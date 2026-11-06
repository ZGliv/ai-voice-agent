import {StreamPlayback} from './stream-playback.js';
import captureUrl from './voice-capture.worklet.js?url';
import {VoiceDetector,InterruptionDetector,wavBlob} from './voice-detector.js';
export class LiveConversation {
 constructor({onState,onLevel,onUtterance,onError,onInterrupt,onPreview,onContinue,onCancelDraft,onStreamChunk,onCancelStream}){Object.assign(this,{onState,onLevel,onUtterance,onError,onInterrupt,onPreview,onContinue,onCancelDraft,onStreamChunk,onCancelStream});this.phase='off';this.generation=0;this.pendingReply=null;this.enabled=false;}
 state(phase){this.phase=phase;this.onState(phase);}
 async start(automatic=false){
  if(this.enabled)return;
  const generation=++this.generation;
  this.enabled=true;this.unheardTimes=[];this.interruptionPending=null;this.state('starting');
  try{
   const ctx=new AudioContext();this.context=ctx;
   if(automatic&&ctx.state!=='running'){this.stop();return;}
   await ctx.resume();
   if(generation!==this.generation)return;
   const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true,channelCount:1}});
   if(generation!==this.generation){stream.getTracks().forEach(t=>t.stop());return;}
   this.echoCancelled=stream.getAudioTracks()[0]?.getSettings?.().echoCancellation===true;
   this.stream=stream;stream.getAudioTracks().forEach(t=>t.onended=()=>{if(this.enabled)this.fail('Microphone disconnected. Tap the orb to reconnect.');});
   await ctx.audioWorklet.addModule(captureUrl);
   if(generation!==this.generation)return;
   ctx.onstatechange=()=>{
    if(generation===this.generation&&this.enabled&&['suspended','interrupted','closed'].includes(ctx.state)){
     this.suspend();this.onError('Audio was interrupted. Tap the orb to reconnect.');
    }
   };
   if(ctx.state!=='running'){this.fail('Tap the orb to reconnect audio.');return;}
   this.detector=new VoiceDetector(ctx.sampleRate);
   this.capture=new AudioWorkletNode(ctx,'voice-capture');this.source=ctx.createMediaStreamSource(stream);
   const mute=ctx.createGain();mute.gain.value=0;this.source.connect(this.capture);this.capture.connect(mute);mute.connect(ctx.destination);
   this.capture.port.onmessage=e=>this.captureChunk(e.data);
   if(navigator.wakeLock)navigator.wakeLock.request('screen').then(lock=>{if(this.enabled&&generation===this.generation)this.wakeLock=lock;else lock.release();}).catch(()=>{});
   if(this.pendingReply){const url=this.pendingReply,pauseAfter=this.pendingReplyPause;this.pendingReply=null;this.pendingReplyPause=false;await this.play(url,{pauseAfter});}else this.listen();
  }catch(error){if(generation===this.generation)this.fail(error.name==='NotAllowedError'?'Allow microphone access, then tap the orb to talk.':'Voice could not start. Tap the orb to retry, or hold it for settings.');}
 }
 unheard(){
  if(!this.enabled)return;
  const now=Date.now();this.unheardTimes=(this.unheardTimes||[]).filter(t=>now-t<30000);this.unheardTimes.push(now);
  if(this.unheardTimes.length>=3){this.fail('Too much background noise to hear clearly. Tap the orb when you are ready to try again.');return;}
  this.listen();
 }
 listen(){if(!this.enabled)return;this.chunks=[];this.preroll=[];this.previewAt=0;this.pauseSnapshot=null;this.detector.reset();this.state('listening');}
 captureChunk(chunk){
  if(!this.enabled)return;
  if(this.phase==='speaking'&&this.echoCancelled&&this.playback){
   this.interruptionChunks.push(chunk);
   while(this.interruptionChunks.length>Math.ceil(this.context.sampleRate*.7/2048))this.interruptionChunks.shift();
   if(this.interruptionDetector.feed(chunk)){
    const source=this.playback;this.voiceInterruptedPlayback=source;this.pendingReply=null;this.pendingReplyPause=false;this.playingUrl=null;this.playback=null;
    this.cancelSpeech();source.stop();this.detector.reset();this.detector.started=true;
    this.chunks=this.interruptionChunks;for(const frame of this.chunks)this.onStreamChunk?.(frame,this.context.sampleRate,true);this.interruptionChunks=[];this.preroll=[];this.previewAt=0;this.pauseSnapshot=null;this.state('listening');
   }
   return;
  }
  if(this.phase!=='listening')return;
  const event=this.detector.feed(chunk);this.onLevel(Math.min(1,event.rms*12));
  if(!event.started){this.preroll.push(chunk);while(this.preroll.length>Math.ceil(this.context.sampleRate*.45/2048))this.preroll.shift();this.detector.total=0;return;}
  if(!this.chunks.length){this.chunks.push(...this.preroll);for(const frame of this.preroll)this.onStreamChunk?.(frame,this.context.sampleRate,false);this.preroll=[];}
  this.chunks.push(chunk);this.onStreamChunk?.(chunk,this.context.sampleRate,this.detector.quiet===0);
  if(this.pauseSnapshot&&this.detector.quiet===0){this.pauseSnapshot=null;this.onContinue?.();}
  if(this.onPreview){
   if(this.detector.quiet>=.20&&!this.pauseSnapshot){
    this.pauseSnapshot=wavBlob(this.chunks,this.context.sampleRate);
    this.onPreview(this.pauseSnapshot,true);this.previewAt=this.detector.total;
   }else if(!this.pauseSnapshot&&this.detector.total-(this.previewAt||0)>=1.2){
    this.onPreview(wavBlob(this.chunks,this.context.sampleRate),false);this.previewAt=this.detector.total;
   }
  }
  if((!this.onStreamChunk&&event.ended)||event.limit){
   if(event.limit)this.onCancelStream?.();
   const blob=this.pauseSnapshot||wavBlob(this.chunks,this.context.sampleRate),generation=this.generation;this.chunks=[];this.state('waiting');
   Promise.resolve(this.interruptionPending).then(()=>generation===this.generation?this.onUtterance(blob):null).then(id=>{if(generation===this.generation&&!id)this.fail('The turn could not be sent. Tap the orb to try again.');}).catch(()=>{if(generation===this.generation)this.fail('Connection lost. Tap the orb to reconnect.');});
  }
 }
 finishSemantic(blob,headers){
  if(!this.enabled||this.phase!=='listening')return;
  const generation=this.generation;this.chunks=[];this.state('waiting');
  Promise.resolve(this.interruptionPending).then(()=>generation===this.generation?this.onUtterance(blob,headers):null).then(id=>{if(generation===this.generation&&!id)this.fail('The turn could not be sent. Tap to retry.');}).catch(()=>{if(generation===this.generation)this.fail('Connection lost. Tap to reconnect.');});
 }
 async play(url,{pauseAfter=false}={}){
  if(!this.enabled){this.pendingReply=url;this.pendingReplyPause=pauseAfter;return false;}
  if(url.endsWith('/audio-stream'))return this.playStream(url,{pauseAfter});
  const generation=this.generation;this.playingUrl=url;this.playingPause=pauseAfter;this.state('waiting');
  const request=new AbortController();this.audioRequest=request;
  const timeout=setTimeout(()=>request.abort(),20000);
  try{
   const response=await fetch(url,{signal:request.signal});if(!response.ok)throw Error();
   const buffer=await this.context.decodeAudioData(await response.arrayBuffer());
   if(generation!==this.generation)return false;
   const ctx=this.context;await ctx.resume();if(ctx.state!=='running')throw Error();
   const source=ctx.createBufferSource(),meter=ctx.createAnalyser();meter.fftSize=256;source.buffer=buffer;source.connect(meter);meter.connect(ctx.destination);this.playback=source;this.playingUrl=url;this.playingPause=pauseAfter;
   source.onended=()=>{source.disconnect();meter.disconnect();if(this.voiceInterruptedPlayback===source){this.voiceInterruptedPlayback=null;return;}if(generation===this.generation){this.playback=null;this.playingUrl=null;const interrupted=this.interruptedPlayback===source;this.interruptedPlayback=null;if(pauseAfter&&!interrupted){this.stop();return;}this.resumeListening(interrupted);}};
   this.interruptionDetector=new InterruptionDetector(ctx.sampleRate,this.detector.noise);this.interruptionChunks=[];
   source.start();this.unheardTimes=[];this.state('speaking');const samples=new Float32Array(meter.fftSize);
   const frame=()=>{if(this.playback!==source||generation!==this.generation)return;meter.getFloatTimeDomainData(samples);this.onLevel(Math.min(1,Math.sqrt(samples.reduce((s,x)=>s+x*x,0)/samples.length)*8));requestAnimationFrame(frame);};frame();return true;
  }catch{if(generation===this.generation){this.pendingReply=url;this.pendingReplyPause=pauseAfter;this.fail('Tap the orb to play the reply and continue.');}return false;}finally{clearTimeout(timeout);if(this.audioRequest===request)this.audioRequest=null;}
 }
 async playStream(url,{pauseAfter=false}={}){
  const generation=this.generation,ctx=this.context;this.playingUrl=url;this.playingPause=pauseAfter;this.state('waiting');
  const request=new AbortController();this.audioRequest=request;
  try{
   await ctx.resume();if(ctx.state!=='running'||generation!==this.generation)throw Error();
   const source=new StreamPlayback(ctx),meter=ctx.createAnalyser();meter.fftSize=256;source.connect(meter);meter.connect(ctx.destination);this.playback=source;
   source.onended=()=>{source.disconnect();meter.disconnect();if(this.voiceInterruptedPlayback===source){this.voiceInterruptedPlayback=null;return;}if(generation===this.generation){this.playback=null;this.playingUrl=null;const interrupted=this.interruptedPlayback===source;this.interruptedPlayback=null;if(pauseAfter&&!interrupted){this.stop();return;}this.resumeListening(interrupted);}};
   const ready=await source.start(url,{signal:request.signal,onError:error=>{if(generation===this.generation){const failed=error.serverFailure||[404,409].includes(error.status);this.pendingReply=failed?null:url;this.pendingReplyPause=failed?false:pauseAfter;this.fail(failed?'Speech generation stopped. Hold the orb to retry the saved answer.':'Speech was interrupted. Tap the orb to replay the saved reply.');}}});
   if(!ready||generation!==this.generation)return false;
   this.interruptionDetector=new InterruptionDetector(ctx.sampleRate,this.detector.noise);this.interruptionChunks=[];
   this.unheardTimes=[];this.state('speaking');const samples=new Float32Array(meter.fftSize);
   const frame=()=>{if(this.playback!==source||generation!==this.generation)return;meter.getFloatTimeDomainData(samples);this.onLevel(Math.min(1,Math.sqrt(samples.reduce((s,x)=>s+x*x,0)/samples.length)*8));requestAnimationFrame(frame);};frame();return true;
  }catch{if(generation===this.generation){this.pendingReply=url;this.pendingReplyPause=pauseAfter;this.fail('Tap the orb to reconnect audio.');}return false;}
 }
 resumeListening(interrupted){
  // Echo-cancelled capture can accept the next words immediately. Retain the
  // speaker-tail guard on devices that cannot confirm echo cancellation.
  if(this.echoCancelled){this.listen();return;}
  this.state('settling');this.resumeTimer=setTimeout(()=>this.listen(),interrupted?120:400);
 }
 cancelSpeech(){
  this.interruptionPending=Promise.resolve().then(()=>this.onInterrupt?.());
  this.interruptionPending.catch(()=>{});
 }
 interrupt(){
  if(!this.enabled||!this.playback)return false;
  const source=this.playback;this.interruptedPlayback=source;this.pendingReply=null;this.pendingReplyPause=false;this.playingUrl=null;
  this.cancelSpeech();source.stop();this.playback=null;this.state('settling');return true;
 }
 suspend(){
  if(this.playingUrl){this.pendingReply=this.playingUrl;this.pendingReplyPause=this.playingPause;}
  this.stop();
 }
 fail(message){this.stop();this.onError(message);}
 stop(){
  this.onCancelStream?.();this.onCancelDraft?.();this.enabled=false;this.generation++;clearTimeout(this.resumeTimer);this.audioRequest?.abort();this.audioRequest=null;this.playingUrl=null;this.playback?.stop();this.playback=null;this.interruptedPlayback=null;this.voiceInterruptedPlayback=null;this.interruptionChunks=[];
  this.capture?.disconnect();this.source?.disconnect();this.stream?.getTracks().forEach(t=>{t.onended=null;t.stop();});this.stream=null;
  if(this.context){this.context.onstatechange=null;this.context.close().catch(()=>{});}this.context=null;this.wakeLock?.release().catch(()=>{});this.wakeLock=null;this.chunks=[];this.preroll=[];this.state('off');
 }
}
