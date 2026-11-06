import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source=(await readFile(new URL('../src/live-conversation.js',import.meta.url),'utf8')).replace("import captureUrl from './voice-capture.worklet.js?url';","const captureUrl='capture';").replace("'./stream-playback.js'",JSON.stringify(new URL('../src/stream-playback.js',import.meta.url).href)).replace("'./voice-detector.js'",JSON.stringify(new URL('../src/voice-detector.js',import.meta.url).href));
const {LiveConversation}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
function harness(){
 const contexts=[],tracks=[],errors=[];
 class Context{
  constructor(){this.state='running';this.sampleRate=48000;this.audioWorklet={addModule:async()=>{}};contexts.push(this);}
  async resume(){} async close(){this.state='closed';}
  createGain(){return {gain:{},connect(){}};}
  createMediaStreamSource(){return {connect(){},disconnect(){}};}
 }
 globalThis.AudioContext=Context;globalThis.AudioWorkletNode=class{constructor(){this.port={};}connect(){}disconnect(){}};
 Object.defineProperty(globalThis,'navigator',{configurable:true,value:{mediaDevices:{getUserMedia:async()=>{const t={stop(){this.stopped=true;}};tracks.push(t);return {getTracks:()=>[t],getAudioTracks:()=>[t]};}}}});
 const live=new LiveConversation({onState(){},onLevel(){},onUtterance(){},onError:e=>errors.push(e)});
 return {live,contexts,tracks,errors};
}
test('suspended audio stops microphone and retains interrupted reply for next tap',async()=>{
 const {live,contexts,tracks,errors}=harness();await live.start();assert.equal(live.phase,'listening');
 live.playingUrl='/api/reply';contexts[0].state='suspended';contexts[0].onstatechange();
 assert.equal(live.phase,'off');assert.equal(tracks[0].stopped,true);assert.equal(live.pendingReply,'/api/reply');assert.equal(errors.length,1);
});
test('stop during context resume cannot request microphone afterward',async()=>{
 const {live,contexts,tracks}=harness();let resolve;AudioContext.prototype.resume=()=>new Promise(r=>resolve=r);
 const starting=live.start();live.stop();resolve();await starting;
 assert.equal(tracks.length,0);assert.equal(live.enabled,false);assert.equal(contexts[0].state,'closed');
});
test('stop aborts a pending reply download without a stale error',async()=>{
 const {live,errors}=harness();await live.start();let signal;const previous=globalThis.fetch;
 globalThis.fetch=async(url,options)=>{signal=options.signal;return new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(Error('aborted'))));};
 try{const playing=live.play('/api/reply');live.stop();assert.equal(await playing,false);assert.equal(signal.aborted,true);assert.deepEqual(errors,[]);}finally{globalThis.fetch=previous;}
});
test('interrupting playback keeps microphone and context alive and resumes listening',async()=>{
 const {live,contexts,tracks,errors}=harness();const previousFetch=globalThis.fetch,previousFrame=globalThis.requestAnimationFrame;
 globalThis.fetch=async()=>({ok:true,arrayBuffer:async()=>new ArrayBuffer(8)});globalThis.requestAnimationFrame=()=>{};
 await live.start();const ctx=contexts[0];let stopped=false;
 ctx.decodeAudioData=async()=>({});ctx.createAnalyser=()=>({fftSize:256,connect(){},disconnect(){},getFloatTimeDomainData(){}});
 ctx.createBufferSource=()=>({connect(){},disconnect(){},start(){},stop(){stopped=true;queueMicrotask(()=>this.onended());}});
 try{
  assert.equal(await live.play('/api/reply'),true);assert.equal(live.phase,'speaking');
  assert.equal(live.interrupt(),true);await new Promise(r=>setTimeout(r,150));
  assert.equal(stopped,true);assert.equal(live.phase,'listening');assert.equal(live.enabled,true);assert.ok(!tracks[0].stopped);assert.equal(ctx.state,'running');assert.equal(live.pendingReply,null);assert.deepEqual(errors,[]);
 }finally{live.stop();globalThis.fetch=previousFetch;globalThis.requestAnimationFrame=previousFrame;}
});
test('unheard clips resume listening but repeated noise pauses the session',async()=>{
 const {live,tracks,errors}=harness();await live.start();
 for(let i=0;i<2;i++){live.state('waiting');live.unheard();assert.equal(live.phase,'listening');assert.ok(!tracks[0].stopped);}
 live.state('waiting');live.unheard();assert.equal(live.phase,'off');assert.equal(tracks[0].stopped,true);assert.match(errors[0],/background noise/);
});

test('voice interruption preserves onset and submits once without resetting on playback end',async()=>{
 const {live,contexts,tracks}=harness();const oldFetch=globalThis.fetch,oldFrame=globalThis.requestAnimationFrame;
 globalThis.fetch=async()=>({ok:true,arrayBuffer:async()=>new ArrayBuffer(8)});globalThis.requestAnimationFrame=()=>{};
 await live.start();live.echoCancelled=true;const ctx=contexts[0];let playback,stopped=false,submitted=[];
 ctx.decodeAudioData=async()=>({});ctx.createAnalyser=()=>({connect(){},disconnect(){},getFloatTimeDomainData(){}});
 ctx.createBufferSource=()=>playback={connect(){},disconnect(){},start(){},stop(){stopped=true;}};
 live.onUtterance=blob=>{submitted.push(blob);return 'turn';};
 const feed=(n,level)=>{for(let i=0;i<n;i++)live.captureChunk(new Float32Array(2048).fill(level));};
 try{
  await live.play('/reply');feed(12,.005);feed(9,.1);
  assert.equal(live.phase,'listening');assert.equal(stopped,true);assert.ok(!tracks[0].stopped);
  const retained=live.chunks.length;assert.ok(retained>=8);playback.onended();assert.equal(live.chunks.length,retained);
  feed(30,0);await new Promise(resolve=>setImmediate(resolve));assert.equal(submitted.length,1);assert.equal(live.phase,'waiting');
  const pcm=new DataView(await submitted[0].arrayBuffer());let loud=0;
  for(let i=44;i<pcm.byteLength;i+=2)if(pcm.getInt16(i,true)>3000)loud++;
  assert.ok(loud>=8*2048,'onset preserved in submitted WAV');
 }finally{live.stop();globalThis.fetch=oldFetch;globalThis.requestAnimationFrame=oldFrame;}
});
test('microphone input cannot interrupt when echo cancellation is unavailable',async()=>{
 const {live}=harness();await live.start();let stopped=false;live.playback={stop(){stopped=true;}};live.state('speaking');
 for(let i=0;i<50;i++)live.captureChunk(new Float32Array(2048).fill(.5));
 assert.equal(stopped,false);assert.equal(live.phase,'speaking');live.stop();
});

test('pause acknowledgement releases microphone after playback; interruption overrides pause',async()=>{
 const oldFetch=globalThis.fetch,oldFrame=globalThis.requestAnimationFrame;
 globalThis.fetch=async()=>({ok:true,arrayBuffer:async()=>new ArrayBuffer(8)});globalThis.requestAnimationFrame=()=>{};
 try{
  for(const interrupt of [false,true]){
   const {live,contexts,tracks}=harness();await live.start();const ctx=contexts[0];let source;
   ctx.decodeAudioData=async()=>({});ctx.createAnalyser=()=>({connect(){},disconnect(){},getFloatTimeDomainData(){}});
   ctx.createBufferSource=()=>source={connect(){},disconnect(){},start(){},stop(){queueMicrotask(()=>this.onended());}};
   await live.play('/pause',{pauseAfter:true});assert.ok(!tracks[0].stopped);
   if(interrupt)live.interrupt();else source.onended();
   await new Promise(r=>setTimeout(r,150));
   assert.equal(live.phase,interrupt?'listening':'off');assert.equal(!!tracks[0].stopped,!interrupt);live.stop();
  }
 }finally{globalThis.fetch=oldFetch;globalThis.requestAnimationFrame=oldFrame;}
});

test('an interrupted pause acknowledgement keeps its pause action when replayed',async()=>{
 const {live,contexts}=harness();await live.start();live.playingUrl='/pause';live.playingPause=true;
 contexts[0].state='suspended';contexts[0].onstatechange();
 assert.equal(live.pendingReply,'/pause');assert.equal(live.pendingReplyPause,true);
 let replay;live.play=async(url,options)=>{replay={url,options};return true;};
 await live.start();assert.deepEqual(replay,{url:'/pause',options:{pauseAfter:true}});live.stop();
});


test('backgrounding during reply download preserves the reply and pause action for the next tap',async()=>{
 const {live,tracks}=harness();await live.start();const oldFetch=globalThis.fetch;let signal;
 globalThis.fetch=async(url,options)=>{signal=options.signal;return new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(Error('aborted'))));};
 try{
  const playing=live.play('/pending-pause',{pauseAfter:true});live.suspend();
  assert.equal(await playing,false);assert.equal(signal.aborted,true);assert.equal(tracks[0].stopped,true);
  assert.equal(live.pendingReply,'/pending-pause');assert.equal(live.pendingReplyPause,true);
  let replay;live.play=async(url,options)=>{replay={url,options};return true;};
  await live.start();assert.deepEqual(replay,{url:'/pending-pause',options:{pauseAfter:true}});
 }finally{live.stop();globalThis.fetch=oldFetch;}
});

test('a follow-up waits for interrupted server speech to stop before submission',async()=>{
 const {live}=harness();await live.start();let cancelled,submitted=0;
 live.onInterrupt=()=>new Promise(resolve=>cancelled=resolve);live.onUtterance=()=>{submitted++;return 'next';};
 live.cancelSpeech();await Promise.resolve();live.listen();
 for(let i=0;i<10;i++)live.captureChunk(new Float32Array(2048).fill(.1));
 for(let i=0;i<30;i++)live.captureChunk(new Float32Array(2048));
 await new Promise(resolve=>setImmediate(resolve));assert.equal(submitted,0);
 cancelled();await new Promise(resolve=>setImmediate(resolve));assert.equal(submitted,1);live.stop();
});


test('echo-cancelled reply completion captures immediate next words',async()=>{
 const {live}=harness();await live.start();live.echoCancelled=true;live.state('speaking');
 live.resumeListening(false);assert.equal(live.phase,'listening');
 for(let i=0;i<6;i++)live.captureChunk(new Float32Array(2048).fill(.1));
 assert.equal(live.detector.started,true);assert.ok(live.chunks.length>=6);live.stop();
});
test('without echo cancellation reply completion keeps speaker-tail guard',async()=>{
 const {live}=harness();await live.start();live.echoCancelled=false;live.state('speaking');
 live.resumeListening(false);assert.equal(live.phase,'settling');live.stop();
});

test('rolling recognition cancels a pause draft when speech continues and final matches latest snapshot',async()=>{
 const {live}=harness();await live.start();const previews=[];let invalidations=0,submitted;
 live.onPreview=(blob,prepare)=>previews.push({blob,prepare});live.onContinue=()=>invalidations++;
 live.onUtterance=blob=>{submitted=blob;return 'turn';};
 const feed=(n,level)=>{for(let i=0;i<n;i++)live.captureChunk(new Float32Array(2048).fill(level));};
 feed(40,.1);assert.ok(previews.some(p=>!p.prepare),'recognizes while speaking');
 feed(6,0);assert.equal(previews.at(-1).prepare,true);const obsolete=previews.at(-1).blob;
 feed(15,.1);assert.equal(invalidations,1);feed(20,0);await new Promise(r=>setImmediate(r));
 assert.notEqual(submitted,obsolete);assert.equal(submitted,previews.at(-1).blob);
 assert.equal(previews.at(-1).prepare,true);live.stop();
});

test('semantic recognition keeps listening past the legacy silence cutoff',async()=>{
 const {live}=harness();await live.start();let packets=0,submitted=0;
 live.onStreamChunk=()=>packets++;live.onCancelStream=()=>{};live.onUtterance=()=>submitted++;
 for(let i=0;i<12;i++)live.captureChunk(new Float32Array(2048).fill(.1));
 for(let i=0;i<35;i++)live.captureChunk(new Float32Array(2048));
 await new Promise(r=>setImmediate(r));assert.equal(submitted,0);assert.equal(live.phase,'listening');assert.ok(packets>35);
 await live.finishSemantic(new Blob(['test']),{'X-Voice-Stream':'test'});
 assert.equal(submitted,1);live.stop();
});
