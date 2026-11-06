import {reportLinks} from './report-links.js';
import './style.css';
import {verificationHtml,canAutoOpen} from './job-verification.js';
export function mountJobView(id){
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 document.title='Jarvis · Building';
 document.querySelector('#app').innerHTML=`<main class="build-view"><div class="build-top"><a href="/">J.A.R.V.I.S.</a><span id="build-state" role="status">Connecting</span></div><p class="eyebrow">Working on your Mac</p><h1 id="build-title">Getting started.</h1><p id="build-brief"></p><a id="build-parent" hidden>View original task</a><p id="build-location" class="small"></p><div class="build-controls"><button id="build-cancel" class="button secondary">Cancel job</button><button id="build-preview" class="button primary" hidden>Open finished site on Mac</button><button id="build-device" class="button secondary" hidden>Open on this device</button></div><p id="build-preview-note" class="small" hidden>Opening another site replaces the shared phone preview.</p><p id="build-error" role="alert"></p><section id="build-verification"></section><ol id="build-events" aria-label="Live build progress"></ol><details id="build-report" hidden><summary>Final report</summary><pre></pre></details></main>`;
 const $=s=>document.querySelector(s);let previewUrl='',signature='',verificationSignature='',navigating=false,polling=false,stopped=false;
 async function api(path,method='GET'){
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),10000);
  try{const r=await fetch('/api/jobs/'+id+path,{method,signal:controller.signal,headers:{'X-Voice-Client':'1'}});const j=await r.json();if(!r.ok)throw Error(j.error);return j;}
  catch(error){if(error.name==='AbortError')throw Error('Connection timed out. Reconnecting…');throw error;}
  finally{clearTimeout(timeout);}
 }
 async function action(button,work){if(button.disabled)return;button.disabled=true;try{await work()}catch(error){$('#build-error').textContent=error.message}finally{button.disabled=false}}

 $('#build-cancel').onclick=event=>action(event.currentTarget,async()=>{await api('/cancel','POST');await refresh()});
 $('#build-preview').onclick=event=>action(event.currentTarget,async()=>{if(previewUrl&&location.hostname==='127.0.0.1'){location.assign(previewUrl);return;}await api('/preview','POST');$('#build-error').textContent='Requested the preview on your Mac.'});
 $('#build-device').onclick=event=>action(event.currentTarget,async()=>{const r=await api('/preview-device','POST');location.assign(r.url)});
 async function refresh(){if(polling||stopped)return;polling=true;try{
  const j=await api('');document.title=j.project_id==='__research__'?'Jarvis · Research':'Jarvis · Working';previewUrl=j.preview_url;$('#build-state').textContent=j.status==='completed'&&j.error?'Needs attention':j.status==='completed'&&j.preview_url?'Preview available':j.status;
  $('#build-title').textContent=j.status==='completed'?(j.error?'The work needs a closer look.':'Your work is ready.'):['failed','cancelled','interrupted'].includes(j.status)?'The job has stopped.':j.project_id==='__research__'?'Looking into it.':'Bringing your idea to life.';$('#build-brief').textContent=j.task;$('#build-parent').hidden=!j.parent_id;if(j.parent_id)$('#build-parent').href='/?job='+encodeURIComponent(j.parent_id);$('#build-location').textContent=j.worktree?'Files saved in '+j.worktree:'Preparing your workspace';
  $('#build-cancel').hidden=!['preparing','running','draft'].includes(j.status);$('#build-preview').hidden=!(j.preview_dir||j.preview_url);$('#build-device').hidden=!(j.preview_dir||j.preview_url)||location.hostname==='127.0.0.1';$('#build-preview-note').hidden=$('#build-device').hidden;
  $('#build-error').textContent=j.error||'';const verification=verificationHtml(j,esc);if(verification!==verificationSignature){verificationSignature=verification;$('#build-verification').innerHTML=verification;}
  if(signature!==j.progress){signature=j.progress;const entries=JSON.parse(j.progress||'[]');$('#build-events').innerHTML=entries.map(e=>`<li><time>${esc(new Date(e.time*1000).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'}))}</time>${e.text.startsWith('Running: ')?`<details class="build-command"><summary>Running a local command</summary><pre>${esc(e.text.slice(9))}</pre></details>`:`<p>${esc(e.text)}</p>`}</li>`).join('');}
  $('#build-report').hidden=!j.result;$('#build-report pre').innerHTML=reportLinks(j.result,esc);
  if(canAutoOpen(j)&&j.preview_url&&location.hostname==='127.0.0.1'&&!navigating){navigating=true;setTimeout(()=>location.assign(j.preview_url),1400);}
 }catch(e){$('#build-error').textContent=e.message||'Connection lost. Reconnecting…'}finally{polling=false}}
 refresh();const timer=setInterval(refresh,750);window.addEventListener('pagehide',()=>{stopped=true;clearInterval(timer)},{once:true});
}
