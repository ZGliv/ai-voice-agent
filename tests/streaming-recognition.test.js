import test from 'node:test';import assert from 'node:assert/strict';import {StreamingRecognition} from '../src/streaming-recognition.js';
const tick=()=>new Promise(r=>setImmediate(r));
test('semantic endpoint waits for current speech, then commits exact accepted PCM',async()=>{
 const sent=[];let ended;const errors=[];
 const recognition=new StreamingRecognition(async(path,options)=>{sent.push(options.body);return {end:true,samples:sent.length*5760,text:'Hello sir'};},async()=>'conversation',(blob,headers)=>ended={blob,headers},e=>errors.push(e));
 for(let i=0;i<6;i++)recognition.feed(new Float32Array(1920).fill(.1),24000,true);
 await tick();assert.equal(ended,undefined,'semantic signal cannot cut current voiced audio');
 for(let i=0;i<6;i++)recognition.feed(new Float32Array(1920),24000,false);
 await tick();assert.ok(ended);assert.equal(recognition.current,null);assert.deepEqual(errors,[]);
 const wav=new Uint8Array(await ended.blob.arrayBuffer()).slice(44);
 const expected=Buffer.concat(sent.map(s=>Buffer.from(s.buffer,s.byteOffset,s.byteLength)));
 assert.deepEqual(Buffer.from(wav),expected);
});
test('cancel ignores an in-flight end result',async()=>{
 let resolve;let ended=false;
 const recognition=new StreamingRecognition((path,options)=>options.method==='DELETE'?Promise.resolve({}):new Promise(r=>resolve=r),async()=>'conversation',()=>ended=true,()=>{});
 recognition.feed(new Float32Array(5760).fill(.1),24000,true);await tick();recognition.cancel();resolve({end:true,samples:5760});await tick();assert.equal(ended,false);
});
