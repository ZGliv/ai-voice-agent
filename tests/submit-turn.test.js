import test from 'node:test';import assert from 'node:assert/strict';
import {submitTurn} from '../src/submit-turn.js';
test('lost acknowledgement retries identical request identity and body',async()=>{
 const calls=[],body=new Blob(['voice']);
 const result=await submitTurn(async(path,options)=>{calls.push({path,options});if(calls.length===1)throw TypeError('Network lost');return {id:'saved'};},'/audio',{method:'POST',body},{delay:0});
 assert.equal(result.id,'saved');assert.equal(calls.length,2);
 assert.match(calls[0].options.headers['X-Voice-Request'],/^[a-f0-9]{32}$/);
 assert.equal(calls[0].options.headers['X-Voice-Request'],calls[1].options.headers['X-Voice-Request']);assert.equal(calls[1].options.body,body);
});
test('rejected input is not retried; network retries are bounded',async()=>{
 let calls=0;await assert.rejects(submitTurn(async()=>{calls++;throw Object.assign(Error('Busy'),{status:409});},'/turns',{}));assert.equal(calls,1);
 calls=0;await assert.rejects(submitTurn(async()=>{calls++;throw TypeError('Offline');},'/turns',{},{delay:0}));assert.equal(calls,2);
});
test('stalled submissions abort and use the same identity for the bounded retry',async()=>{
 const ids=[];await assert.rejects(submitTurn(async(path,options)=>{ids.push(options.headers['X-Voice-Request']);return new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>reject(Error('Timeout'))));},'/turns',{},{timeout:5,delay:0}));
 assert.equal(ids.length,2);assert.equal(ids[0],ids[1]);
});
