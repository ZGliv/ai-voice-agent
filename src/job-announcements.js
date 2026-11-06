const TERMINAL=new Set(['completed','failed','interrupted','cancelled','awaiting_approval']);
export class JobAnnouncements {
 constructor({storage,ready,speak,now=Date.now}){
  Object.assign(this,{storage,ready,speak,now});this.pending=new Map();this.inflight=false;this.retryAt=0;this.sessionStart=now()/1000;
  try{this.seen=JSON.parse(storage.getItem('jarvis-job-announcements')||'{}');if(!this.seen||Array.isArray(this.seen)||typeof this.seen!=='object')this.seen={};}catch{this.seen={};}
 }
 persist(){try{this.storage.setItem('jarvis-job-announcements',JSON.stringify(Object.fromEntries(Object.entries(this.seen).slice(-100))));}catch{}}
 observe(jobs){
  for(const job of jobs){
   const prior=this.seen[job.id];
   if(['running','preparing'].includes(job.status)){this.seen[job.id]='watching';continue;}
   if(!TERMINAL.has(job.status))continue;
   if(prior==='watching'||prior==='pending'||(!prior&&job.created>=this.sessionStart)){
    this.pending.set(job.id,job);this.seen[job.id]='pending';
   }else if(!prior)this.seen[job.id]='seen';
  }
  this.persist();
 }
 async tick(){
  if(this.inflight||!this.pending.size||!this.ready()||this.now()<this.retryAt)return;
  this.inflight=true;const [id,job]=this.pending.entries().next().value;
  try{if(await this.speak(job)){this.pending.delete(id);this.seen[id]='seen';this.persist();}else this.retryAt=this.now()+5000;}
  catch{this.retryAt=this.now()+30000;}
  finally{this.inflight=false;}
 }
}
