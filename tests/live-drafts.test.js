import test from 'node:test';import assert from 'node:assert/strict';import {LiveDrafts} from '../src/live-drafts.js';
test('continued speech invalidates older preparation with higher revision',async()=>{
 const requests=[];const drafts=new LiveDrafts(async(...args)=>requests.push(args),async()=>'conversation');
 drafts.preview(new Blob(['first']),true);await drafts.current.pending;const id=drafts.current.id;
 drafts.invalidate();assert.match(requests[1][0],/revision=2/);assert.equal(requests[1][1].method,'DELETE');
 drafts.preview(new Blob(['continued']),true);await drafts.current.pending;
 assert.deepEqual(drafts.finish(),{'X-Voice-Draft':id,'X-Voice-Draft-Revision':'3'});assert.equal(drafts.current,null);
});
test('stopping while conversation is created cannot launch a stale draft',async()=>{
 let created;const requests=[];const drafts=new LiveDrafts(async(...args)=>requests.push(args),()=>new Promise(r=>created=r));
 drafts.preview(new Blob(['speech']),false);const pending=drafts.current.pending;drafts.cancel();created('conversation');await pending;
 assert.equal(requests.length,1);assert.equal(requests[0][1].method,'DELETE');
});
