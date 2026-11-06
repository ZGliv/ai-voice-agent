import test from 'node:test';
import assert from 'node:assert/strict';
import {canAutoOpen,verificationHtml} from '../src/job-verification.js';
test('automatic opening requires actual browser evidence and no job errors',()=>{
 for(const status of ['failed','unavailable',undefined])assert.equal(canAutoOpen({status:'completed',verification:JSON.stringify({status})}),false);
 assert.equal(canAutoOpen({status:'completed',verification:'invalid'}),false);
 assert.equal(canAutoOpen({status:'completed',verification:'{"status":"passed"}'}),true);
 assert.equal(canAutoOpen({status:'completed',error:'problem',verification:'{"status":"passed"}'}),false);
});
test('browser evidence escapes generated text',()=>{
 const html=verificationHtml({verification:{status:'failed',summary:'<script>',runs:[{viewport:'mobile',checks:[{name:'<img>',passed:false,error:'<b>'}]}]}},s=>String(s).replaceAll('<','&lt;'));
 assert.ok(!html.includes('<script>'));assert.ok(html.includes('&lt;img>'));assert.ok(html.includes('Failed:'));
});
