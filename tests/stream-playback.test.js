import test from 'node:test';import assert from 'node:assert/strict';import {StreamPlayback} from '../src/stream-playback.js';
function context(){const sources=[];return {currentTime:0,sources,createGain:()=>({connect(){},disconnect(){}}),createBuffer:(n,length,rate)=>({duration:length/rate,getChannelData:()=>new Float32Array(length)}),createBufferSource:()=>{const s={connect(){},disconnect(){},start(t){this.at=t;},stop(){this.stopped=true;}};sources.push(s);return s;}};}
const packet=JSON.stringify({audio:btoa('\x01\x01'.repeat(2400)),sample_rate:24000})+'\n';
test('plays first PCM before stream completes, then waits for playback to end',async()=>{
 const old=globalThis.fetch;let feed;globalThis.fetch=async()=>({ok:true,body:new ReadableStream({start(c){feed=c;}})});
 const c=context(),player=new StreamPlayback(c);let ended=0;player.onended=()=>ended++;
 try{const ready=player.start('/stream');await new Promise(r=>setImmediate(r));feed.enqueue(new TextEncoder().encode(packet));assert.equal(await ready,true);assert.equal(c.sources.length,1);assert.equal(ended,0);
 feed.enqueue(new TextEncoder().encode('{"done":true}\n'));feed.close();await new Promise(r=>setImmediate(r));assert.equal(ended,0);c.sources[0].onended();assert.equal(ended,1);
 }finally{player.stop();globalThis.fetch=old;}
});
test('stream failure stops queued playback and reports an error',async()=>{
 const old=globalThis.fetch;globalThis.fetch=async()=>({ok:true,body:new ReadableStream({start(c){c.enqueue(new TextEncoder().encode(packet+'{"error":"failed"}\n'));c.close();}})});
 const c=context(),player=new StreamPlayback(c);let error;
 try{await player.start('/stream',{onError:e=>error=e});await new Promise(r=>setImmediate(r));assert.match(error.message,/failed/);assert.equal(c.sources[0].stopped,true);}finally{player.stop();globalThis.fetch=old;}
});
test('explicit stop cancels remaining network audio and queued buffers',async()=>{
 const old=globalThis.fetch;let cancelled=false;globalThis.fetch=async()=>({ok:true,body:new ReadableStream({start(c){c.enqueue(new TextEncoder().encode(packet));},cancel(){cancelled=true;}})});
 const c=context(),player=new StreamPlayback(c);try{await player.start('/stream');player.stop();assert.equal(cancelled,true);assert.equal(c.sources[0].stopped,true);}finally{globalThis.fetch=old;}
});


test('many valid frames coalesced into one network read still play',async()=>{
 const old=globalThis.fetch;globalThis.fetch=async()=>({ok:true,body:new ReadableStream({start(c){c.enqueue(new TextEncoder().encode(packet.repeat(30)+'{"done":true}\n'));c.close();}})});
 const c=context(),player=new StreamPlayback(c);let error;try{assert.equal(await player.start('/stream',{onError:e=>error=e}),true);await new Promise(r=>setImmediate(r));assert.equal(error,undefined);assert.equal(c.sources.length,30);}finally{player.stop();globalThis.fetch=old;}
});
