// One rolling utterance; stale requests cannot resurrect cancelled preparation.
export class LiveDrafts {
 constructor(api,ensureConversation){this.api=api;this.ensureConversation=ensureConversation;this.current=null;}
 preview(blob,prepare){
  const state=this.current??={id:crypto.randomUUID().replaceAll('-',''),revision:0};
  const revision=++state.revision;
  state.pending=(async()=>{
   const cid=await this.ensureConversation();
   if(this.current!==state||revision!==state.revision)return;
   await this.api(`/drafts/${state.id}?conversation_id=${cid}&revision=${revision}&prepare=${prepare?1:0}`,{method:'POST',headers:{'Content-Type':'audio/wav'},body:blob});
  })().catch(()=>{});
 }
 invalidate(){const state=this.current;if(!state)return;const revision=++state.revision;this.api(`/drafts/${state.id}?revision=${revision}`,{method:'DELETE'}).catch(()=>{});}
 finish(){const state=this.current;this.current=null;return state?{'X-Voice-Draft':state.id,'X-Voice-Draft-Revision':String(state.revision)}:{};}
 cancel(){this.invalidate();this.current=null;}
}
