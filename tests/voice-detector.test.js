import test from 'node:test';import assert from 'node:assert/strict';import {VoiceDetector,wavBlob} from '../src/voice-detector.js';
const block=(level)=>new Float32Array(480).fill(level);
test('silence and short clicks never submit a turn',()=>{const d=new VoiceDetector(48000);for(let i=0;i<500;i++)assert.equal(d.feed(block(.003)).started,false);for(let i=0;i<5;i++)d.feed(block(.1));for(let i=0;i<200;i++)assert.equal(d.feed(block(0)).ended,false);});
test('speech waits through a short pause and ends after sustained silence',()=>{const d=new VoiceDetector(48000);for(let i=0;i<40;i++)d.feed(block(.1));for(let i=0;i<60;i++)assert.equal(d.feed(block(0)).ended,false);d.feed(block(.1));let end;for(let i=0;i<120;i++)end=d.feed(block(0));assert.equal(end.ended,true);d.reset();assert.equal(d.feed(block(0)).ended,false);});
test('WAV preserves sample count and clips amplitude safely',async()=>{const b=await wavBlob([new Float32Array([0,2,-2,.5])],24000).arrayBuffer();const v=new DataView(b);assert.equal(v.getUint32(24,true),24000);assert.equal(v.getUint32(40,true),8);assert.equal(v.getInt16(46,true),32767);assert.equal(v.getInt16(48,true),-32767);});

test('interruption rejects calibration, steady residual echo, and short clicks',async()=>{
 const {InterruptionDetector}=await import('../src/voice-detector.js');const d=new InterruptionDetector(48000);
 for(let i=0;i<200;i++)assert.equal(d.feed(block(.02)),false);
 for(let i=0;i<20;i++)assert.equal(d.feed(block(.2)),false);
 for(let i=0;i<80;i++)assert.equal(d.feed(block(.01)),false);
});
test('interruption accepts sustained onset above learned residual energy',async()=>{
 const {InterruptionDetector}=await import('../src/voice-detector.js');const d=new InterruptionDetector(48000);
 for(let i=0;i<50;i++)d.feed(block(.005));let interrupted=false;
 for(let i=0;i<40;i++)interrupted=d.feed(block(.1));
 assert.equal(interrupted,true);
});


test('a brief loud startup transient does not mask the next spoken interruption',async()=>{
 const {InterruptionDetector}=await import('../src/voice-detector.js');const d=new InterruptionDetector(48000);
 for(let i=0;i<10;i++)assert.equal(d.feed(block(.3)),false);
 for(let i=0;i<30;i++)assert.equal(d.feed(block(.005)),false);
 let interrupted=false;for(let i=0;i<40;i++)interrupted=d.feed(block(.1));
 assert.equal(interrupted,true);
});
test('sustained loud playback residual is still rejected after calibration',async()=>{
 const {InterruptionDetector}=await import('../src/voice-detector.js');const d=new InterruptionDetector(48000);
 for(let i=0;i<500;i++)assert.equal(d.feed(block(.1)),false);
});


test('turn ends within 800ms but keeps a 600ms thinking pause',()=>{
 const d=new VoiceDetector(48000);for(let i=0;i<40;i++)d.feed(block(.1));
 for(let i=0;i<60;i++)assert.equal(d.feed(block(0)).ended,false);
 let ended=false;for(let i=0;i<20;i++)ended=d.feed(block(0)).ended;
 assert.equal(ended,true);
});
test('interrupt stops sustained speech within 260ms after calibration',async()=>{
 const {InterruptionDetector}=await import('../src/voice-detector.js');const d=new InterruptionDetector(48000);
 for(let i=0;i<50;i++)d.feed(block(.003));let interrupted=false;
 for(let i=0;i<26;i++)interrupted=d.feed(block(.1));assert.equal(interrupted,true);
});
