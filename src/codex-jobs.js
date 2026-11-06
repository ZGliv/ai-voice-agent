import {reportLinks} from './report-links.js';
import {verificationHtml} from './job-verification.js';
export function mountJobs({api,esc,getTurns,notice,onJobs=()=>{}}) {
  const drawer=document.createElement('section');drawer.id='jobs-drawer';
  document.querySelector('#sidebar-options').prepend(drawer);
  const surface=document.createElement('section');surface.id='job-cards';surface.hidden=true;
  document.querySelector('#workspace').append(surface);
  let jobs=[],last=0,signature='';
  function contextText(job){try{return JSON.parse(job.context).map(m=>`${m.kind==='decision'?'Decision':m.status==='done'?'Completed step':'Next step'}: ${m.content}`).join('\n\n')}catch{return 'Saved context could not be displayed.'}}
  function card(job){return `<article class="job-card"><div class="job-label">CODEX · ${esc(job.status)}</div><p>${esc(job.task)}</p><span class="small">${esc(job.project_name||job.project_id)}</span>${job.status==='draft'?'<p class="small">Runs on this Mac in a separate workspace. Existing projects start from the latest commit. Uncommitted edits are not copied. Uses your Codex account; project context is sent to OpenAI.</p>':''}${job.parent_id?`<p class="small"><a href="/?job=${esc(job.parent_id)}" target="_blank" rel="noopener">View original task</a> · original files preserved</p>`:''}${job.context&&job.context!=='[]'?`<details><summary>Project memory included</summary><p>${esc(contextText(job))}</p></details>`:''}${['preparing','running'].includes(job.status)?`<p class="job-live">${esc(JSON.parse(job.progress||'[]').at(-1)?.text||'Starting Codex…')}</p>`:''}${job.error?`<p class="job-error">${esc(job.error)}</p>`:''}${verificationHtml(job,esc)}<div class="job-actions"><a class="button secondary job-watch" href="/?job=${job.id}" target="_blank" rel="noopener">Watch progress</a>${job.preview_dir||job.preview_url?`<button class="button primary" data-job="${job.id}" data-action="preview">Open site on Mac</button><button class="button secondary" data-job="${job.id}" data-action="preview-device">Open on this device</button>`:''}${job.status==='draft'?`<button class="button primary" data-job="${job.id}" data-action="start">Start Codex job</button>`:''}${['draft','preparing','running'].includes(job.status)?`<button class="button secondary" data-job="${job.id}" data-action="cancel">${job.status==='draft'?'Dismiss':'Cancel job'}</button>`:''}</div>${job.preview_dir?'<p class="small">Opening another site replaces the shared phone preview.</p>':''}${job.result?`<details><summary>Result</summary><p>${reportLinks(job.result,esc)}</p></details>`:''}${job.session_id?`<p class="small">Session: ${esc(job.session_id)}</p>`:''}</article>`}
  async function act(e){const b=e.target.closest('[data-job]');if(!b)return;b.disabled=true;try{const result=await api(`/jobs/${b.dataset.job}/${b.dataset.action}`,{method:'POST'});if(b.dataset.action==='preview-device'){location.assign(result.url);return;}last=0;await refresh();}catch(error){notice(error.message);b.disabled=false;}}
  surface.onclick=drawer.onclick=act;
  async function refresh(){
    if(Date.now()-last>1200){const data=await api('/jobs');jobs=data.jobs;last=Date.now();onJobs(jobs);}
    const turnIds=new Set(getTurns().map(t=>t.id));
    const current=jobs.filter(j=>turnIds.has(j.source_turn_id));
    const next=JSON.stringify([jobs,current]);if(signature===next)return;signature=next;
    surface.hidden=!current.length;surface.innerHTML=current.map(card).join('');
    const drawerOpen=drawer.querySelector(':scope > details')?.open;
    drawer.innerHTML=jobs.length?`<details ${drawerOpen?'open':''}><summary>Codex jobs${jobs.some(j=>['preparing','running'].includes(j.status))?' · running':''}</summary>${jobs.map(card).join('')}</details>`:'';
  }
  return {refresh};
}
