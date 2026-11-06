import {StreamingRecognition} from './streaming-recognition.js';
import {submitTurn} from './submit-turn.js';
import {JobAnnouncements} from './job-announcements.js';
import {LiveConversation} from './live-conversation.js';
import { mountVoiceSettings } from './voice-settings.js';
import {mountJobs} from './codex-jobs.js';
import {mountProjectMemory} from './project-memory.js';
import './style.css';
import {initializeOrb,updateOrb,meterPlayback} from './pulsating-orb.js';
const LOCAL=!!document.querySelector('meta[name="companion-runtime"][content="private"]')||['127.0.0.1','localhost'].includes(location.hostname);
const $=s=>document.querySelector(s), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const activeStates=['queued','transcribing','thinking','synthesizing'];
let health=null, conversations=[], current=null, turns=[], busy=null, posting=false, requestingMic=false, recording=false, recorder=null, stream=null, chunks=[], audioContext=null, recordTimer=null, recordingStarted=0, lastSignature='', autoPlayId=null, polling=false;
const icons={mic:'<path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Z"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/>',arrow:'<path d="m6 12 6-6 6 6M12 6v14"/>',plus:'<path d="M12 5v14M5 12h14"/>',history:'<path d="M3 11a9 9 0 1 1 2 7M3 4v7h7M12 7v5l3 2"/>',stop:'<rect x="6" y="6" width="12" height="12" rx="2"/>',upload:'<path d="M12 16V3m-4 4 4-4 4 4M4 15v5h16v-5"/>'};
const icon=(name)=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name]}</svg>`;
$('#app').innerHTML=`<div class="shell"><button id="history-backdrop" aria-label="Close conversation history" hidden></button><aside class="sidebar" id="history-panel" aria-label="Conversations and options" inert><a class="wordmark" href="/" aria-label="Project Room companion home"><span class="brand-orb"></span><span>PROJECT ROOM</span></a><button id="new" class="button secondary">${icon('plus')}New conversation</button><div id="sidebar-projects"></div><div class="eyebrow history-label">Your conversations</div><nav id="conversations" aria-label="Conversation history"></nav><div id="sidebar-options"></div><div class="sidebar-foot"><button class="button text" id="setup">Settings</button><span id="connection" class="status-pill">Connecting…</span></div></aside><main><header><button id="history-toggle" class="button icon-only" aria-label="Toggle conversation history" aria-expanded="false" aria-controls="history-panel">${icon('history')}</button></header><section class="stage"><div class="stage-copy" aria-live="polite"><p class="eyebrow">Your personal project companion</p><h1>J.A.R.V.I.S.</h1><p class="intro">Ready when you are, Zack.</p><div class="stage-status"><span class="status-dot"></span><span id="stage-status">${LOCAL?'Connecting to your companion…':'Your voice. Your computer.'}</span></div></div><div class="orb-wrap"><div id="orb"></div><span class="orb-caption" id="orb-caption">VOICE INTERFACE · STANDBY</span></div></section><section id="hosted" ${LOCAL?'hidden':''} class="launcher"><p class="eyebrow">Ready when you are</p><h2>The conversation happens locally.</h2><p>This Vercel page is your doorway. Speech, replies and saved conversations run on your computer through the local companion.</p><a class="button primary" href="http://127.0.0.1:4321" target="_blank" rel="noopener">Open local companion <span aria-hidden="true">↗</span></a><button class="button secondary" id="host-setup">Set it up</button><p class="small">Start the companion first. Your browser will ask for microphone permission only when you choose to record.</p></section><section id="workspace" ${LOCAL?'':'hidden'}><div class="conversation-heading"><div><p class="eyebrow">The conversation</p><h2 id="conversation-title">Start with a thought.</h2></div><div class="conversation-actions"><button id="export" class="button text" disabled>Export</button><button id="delete" class="button text" disabled>Delete</button></div></div><div id="turns" aria-live="polite"><div class="empty"><span class="empty-line"></span><p>No rush. Say what’s on your mind,<br>or start by typing below.</p></div></div><div class="composer"><div id="notice" role="status" hidden></div><div id="recording-panel" hidden><span class="record-light"></span><span id="record-time">Recording · 0:00 / 1:00</span><button id="discard" class="button text">Discard</button></div><form id="text-form"><label class="sr-only" for="message">Your message</label><textarea id="message" rows="1" maxlength="4000" placeholder="Talk to Jarvis…"></textarea><button id="send" class="button send" aria-label="Send message" type="submit">${icon('arrow')}</button></form><div class="composer-tools"><button type="button" class="button primary" id="record" title="Start talking">${icon('mic')}<span>Start talking</span></button><button class="button secondary" id="upload">${icon('upload')}<span>Upload audio</span></button><button class="button secondary" id="cancel" hidden>${icon('stop')}Stop response</button><input id="audio-file" type="file" accept="audio/*,.webm,.m4a,.mp4" hidden><label class="autoplay"><input id="autoplay" type="checkbox">Speak replies</label></div><p class="composer-note">English · up to 60 seconds · saved on the companion Mac</p></div></section><footer>Your ideas. In motion.<span>PROJECT ROOM / PRIVATE</span></footer></main></div><dialog id="setup-dialog"><div class="dialog-header"><p class="eyebrow">Your local companion</p><button id="close-setup" class="button text">Close</button></div><h2>Your Jarvis setup.</h2><p>The companion runs on your Mac. Keep the Mac awake and signed in while you use Jarvis from your phone. With Fish connected, reply text is sent to Fish Audio for AI-generated speech; microphone recordings and project memory remain on your Mac unless included in an explicitly requested Codex job.</p><div id="voice-settings"></div><div id="checks"></div><h3>On this Mac</h3><p>Jarvis is installed as a background service that starts when you sign in. You do not need to keep Terminal open. To check the service, run:</p><pre>cd ~/Developer/ai-voice-agent
python3 mac_service.py status</pre><button id="copy-command" class="button secondary">Copy status command</button><p>Open <a href="http://127.0.0.1:4321" target="_blank" rel="noopener">Jarvis on this Mac</a>, or use your private HTTPS link with Tailscale connected on your phone. If the service is already running, do not start a second companion process.</p><details><summary>Another computer or missing dependencies</summary><p>Download the source and follow README.md to install Python, FFmpeg, Whisper, Ollama / qwen3:8b and Piper / Alan (British English). Models are installed separately; nothing downloads automatically.</p><a href="/voice-agent-source.zip" class="button secondary" download>Download companion source</a></details><h3>What stays here</h3><p>Transcripts and generated speech are saved in a local SQLite library. Uploaded recordings are deleted after a successful turn; unfinished recordings remain for retry until you delete their conversation. Export downloads transcripts, not audio.</p><p>Up to the last eight completed turns in this conversation (within a context budget) are sent to the local model. Selected project context and your saved decisions are included. Project memory tools are local. Codex jobs run on this Mac in isolated worktrees when you explicitly request work; their prompts and project context go to OpenAI through your Codex account. No wake word or background listening. A local model can make mistakes; review its answers.</p><p class="small">Whisper base · Qwen3 8B · selected speech voice. Your browser controls microphone permission. Tap the orb to start or pause a voice conversation. Hold it for history and settings. Switching apps pauses the microphone; return and tap to continue.</p></dialog><dialog id="delete-dialog"><h2>Delete this conversation?</h2><p>Its transcript, generated speech and unfinished recordings will be removed from the companion Mac. Saved project takeaways and their original thought remain; remove those separately. Export the transcript first if you want a copy.</p><div class="dialog-actions"><button id="keep" class="button secondary">Keep conversation</button><button id="confirm-delete" class="button danger">Delete conversation</button></div></dialog>`;
initializeOrb($('#orb'));
const jobs = LOCAL ? mountJobs({api,esc,getTurns:()=>turns,notice,onJobs:items=>announcements.observe(items)}) : null;
const memory = LOCAL ? mountProjectMemory({api,esc,getTurns:()=>turns,getCurrent:()=>current,getBusy:()=>busy||posting||recording,newConversation:async()=>{selectId(null);turns=[];lastSignature='';renderList();renderTurns();},notice}) : null;
// Keep the conversation surface quiet; supporting tools live in the drawer.
if(LOCAL)$('#sidebar-projects').append($('.project-memory'));
$('#sidebar-options').append($('.conversation-heading'),$('.composer-tools'));
$('#text-form').insertBefore($('#record'),$('#send'));
$('.composer').append($('#cancel'));
$('#turns').hidden=true;
// The active experience is only the orb; text/history remain available on demand.
document.body.classList.add('orb-only');
$('#sidebar-options').append($('#workspace'));
$('#orb').setAttribute('role','button');$('#orb').tabIndex=0;$('#orb').setAttribute('aria-label','Start voice conversation. Hold for history and settings.');
let liveTurn=null,liveOutputTurn=null,livePhase='off';
const recognition=new StreamingRecognition(api,ensureConversation,(blob,headers)=>live.finishSemantic(blob,headers),message=>live.fail(message));
const live=new LiveConversation({
 onStreamChunk:(chunk,rate,voiced)=>recognition.feed(chunk,rate,voiced),onCancelStream:()=>recognition.cancel(),
 onState:phase=>{livePhase=phase;document.body.dataset.voice=phase;$('#orb').setAttribute('aria-pressed',String(phase!=='off'));$('#orb').setAttribute('aria-label',phase==='off'?'Start voice conversation. Hold for history and settings.':phase==='speaking'?'Interrupt reply and speak. Hold for history and settings.':'Pause voice conversation. Hold for history and settings.');setStage(({listening:'recording',waiting:'thinking',speaking:'speaking',starting:'queued',settling:'idle'})[phase]||'idle',phase==='listening'?'Listening':phase==='off'?'Conversation paused':phase);},
 onLevel:level=>updateOrb(null,level),
 onInterrupt:async()=>{
  const id=liveOutputTurn;if(!id)return;
  const result=await api(`/turns/${id}/cancel`,{method:'POST'});
  if(!result.cancel_requested)return;
  for(let i=0;i<50;i++){
   const status=await api('/health');
   if(status.active!==id){if(busy===id)busy=null;return;}
   await new Promise(resolve=>setTimeout(resolve,100));
  }
  throw Error('The interrupted reply is still stopping. Tap to retry.');
 },
 onUtterance:async (blob,headers)=>{const id=await submitAudio(blob,headers);liveTurn=id;return id;},onError:notice
});
live.state('off');
const quietForAnnouncement=()=>live.enabled&&live.phase==='listening'&&!live.detector?.started&&!live.detector?.voiced&&!busy&&!posting&&!document.hidden;
let announcementStorage;try{announcementStorage=localStorage;}catch{announcementStorage={getItem:()=>null,setItem:()=>{}};}
const announcements=new JobAnnouncements({storage:announcementStorage,ready:quietForAnnouncement,speak:async job=>{
 const audio=await api(`/jobs/${job.id}/announcement`,{method:'POST'});
 if(!quietForAnnouncement())return false;
 const delivered=await live.play(audio.url);if(!delivered)live.pendingReply=null;return delivered;
}});

async function toggleLive(){notice('');if(live.interrupt())return;if(live.enabled){live.stop();if(busy){try{await api(`/turns/${busy}/cancel`,{method:'POST'})}catch(e){notice(e.message)}}}else{if(busy){notice('A reply is still finishing. Tap the orb again in a moment.');return;}autoPlayId=null;await live.start();}}
let holdTimer,held=false;
$('#orb').addEventListener('pointerdown',()=>{held=false;holdTimer=setTimeout(()=>{held=true;live.stop();setHistory(true);},650)});
for(const event of ['pointerup','pointercancel','pointerleave'])$('#orb').addEventListener(event,()=>clearTimeout(holdTimer));
$('#orb').onclick=()=>{if(!held)toggleLive();};
$('#orb').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();toggleLive();}if(e.key==='ContextMenu'||(e.shiftKey&&e.key==='F10')){e.preventDefault();live.stop();setHistory(true);}};
$('#orb').oncontextmenu=e=>{e.preventDefault();held=true;live.stop();setHistory(true);};
// The corner control appears only on explicit pointer movement or keyboard focus.
let revealTimer;document.addEventListener('pointermove',()=>{document.body.classList.add('show-controls');clearTimeout(revealTimer);revealTimer=setTimeout(()=>document.body.classList.remove('show-controls'),1800);});
document.addEventListener('visibilitychange',()=>{if(document.hidden)live.suspend();});

async function api(path,options={}){
 const controller=options.signal?null:new AbortController();
 const timer=controller?setTimeout(()=>controller.abort(),10000):null;
 try{
  const response=await fetch('/api'+path,{...options,signal:options.signal||controller.signal,headers:{'X-Voice-Client':'1',...(options.headers||{})}});
  let data;try{data=await response.json()}catch{throw Error('The companion response could not be read. Check the connection and retry.')}
  if(!response.ok){const error=Error(data.error||'The companion could not complete this request.');error.status=response.status;throw error;}
  return data;
 }finally{if(timer)clearTimeout(timer);}
}

function notice(message){$('#notice').hidden=!message;$('#notice').textContent=message||''}
document.querySelector('main').append($('#notice'));
function selectId(value){if(current){live.stop();live.pendingReply=null;liveTurn=null;liveOutputTurn=null;}document.querySelectorAll('audio').forEach(a=>a.pause());current=value;autoPlayId=null;}
function renderList(){ $('#conversations').innerHTML=conversations.length?conversations.map(c=>`<button class="history-item ${c.id===current?'selected':''}" data-conversation="${c.id}" ${recording?'disabled':''}><span>${esc(c.title)}</span><time>${new Date(c.updated*1000).toLocaleDateString(undefined,{month:'short',day:'numeric'})}</time></button>`).join(''):'<p class="history-empty">Your conversations will<br>be here when you return.</p>';$('#conversation-title').textContent=conversations.find(c=>c.id===current)?.title||'Start with a thought.';$('#export').disabled=!current;$('#delete').disabled=!current||!!busy||recording;}
function setStage(state,text){$('#stage-status').textContent=text;$('#orb-caption').textContent=state==='recording'?'LISTENING · ONLY WHILE YOU RECORD':state==='speaking'?'SPOKEN RESPONSE':'VOICE INTERFACE · STANDBY';updateOrb(state,0)}
function renderTurns(){const wasNearBottom=$('#turns').scrollHeight-$('#turns').scrollTop-$('#turns').clientHeight<90;$('#turns').hidden=!turns.length;const signature=JSON.stringify(turns);if(signature===lastSignature)return;lastSignature=signature;
  $('#turns').innerHTML=turns.length?turns.map(t=>`<article class="turn" data-turn="${t.id}"><div class="message user"><span class="speaker">YOU <span>${t.source==='audio'?'VOICE':'TEXT'}</span></span><p>${esc(t.input_text||(activeStates.includes(t.status)?'Audio received. Transcribing…':'Audio input · no transcript yet'))}</p></div>${(t.output_text||t.partial_text)?`<div class="message assistant"><span class="speaker">JARVIS</span><p>${esc(t.output_text||t.partial_text)}</p>${t.has_audio?`<audio controls preload="metadata" src="/api/turns/${t.id}/audio" aria-label="Spoken response"></audio>`:''}</div>`:''}${activeStates.includes(t.status)?`<p class="turn-state"><span class="pulse-dot"></span>${({queued:'Starting your turn',transcribing:'Transcribing your audio',thinking:'Thinking through a reply',synthesizing:'Giving the reply a voice'})[t.status]}…</p>`:''}${['failed','cancelled','interrupted','unheard'].includes(t.status)?`<div class="turn-error"><p>${esc(t.error)}</p><button class="button secondary retry" data-retry="${t.id}">Retry this turn</button></div>`:''}${t.status==='complete'?`<span class="turn-meta">Saved on this computer · ${['transcribing','thinking','synthesizing'].reduce((sum,stage)=>sum+(Number(t.timings?.[stage])||0),0).toFixed(1)}s</span>`:''}</article>`).join(''):'<div class="empty"><span class="empty-line"></span><p>No rush. Say what’s on your mind,<br>or start by typing below.</p></div>';
  if(wasNearBottom)$('#turns').scrollTop=$('#turns').scrollHeight;
  document.querySelectorAll('audio').forEach(audio=>{audio.onplay=()=>{document.querySelectorAll('audio').forEach(other=>{if(other!==audio)other.pause()});setStage('speaking','Speaking · you can pause below');meterPlayback(audio)};audio.onpause=audio.onended=()=>{if(!busy&&!recording)setStage('idle','Ready for your next thought')}});
  const latest=turns.at(-1);if(latest?.id===autoPlayId&&latest.has_audio&&latest.status==='complete'){autoPlayId=null;if(!liveTurn&&!live.enabled&&$('#autoplay').checked){const audio=$(`[data-turn="${latest.id}"] audio`);audio.play().catch(()=>notice('Your response is ready. Press play below to hear it.'))}}
}
function controls(){const blocked=posting||!!busy||requestingMic;memory?.controls(blocked||recording);$('#record').disabled=blocked||!health;$('#upload').disabled=blocked||recording||!health;$('#message').disabled=blocked||recording||!health;$('#send').disabled=blocked||recording||!health;$('#new').disabled=recording||posting;$('#cancel').hidden=!busy;$('#cancel').disabled=!busy;$('#delete').disabled=!current||blocked||recording;$('#record').innerHTML=recording?`${icon('stop')}<span>Finish & send</span>`:`${icon('mic')}<span>Start talking</span>`;$('#record').title=recording?'Finish & send':'Start talking';$('#recording-panel').hidden=!recording;document.querySelectorAll('.retry').forEach(b=>b.disabled=blocked||recording);}
let detailsRefreshing=false,lastDetailsRefresh=0;
async function refreshDetails(requested,projectId){
 if(detailsRefreshing||Date.now()-lastDetailsRefresh<1500)return;
 detailsRefreshing=true;lastDetailsRefresh=Date.now();
 try{
  const results=await Promise.allSettled([api('/conversations'),memory?.sync(projectId),jobs?.refresh()]);
  if(current!==requested)return;
  if(results[0].status==='fulfilled'){
   conversations=results[0].value;
   if(current&&!posting&&!conversations.some(c=>c.id===current))selectId(null);
   renderList();
  }
  const failure=results.find(result=>result.status==='rejected');
  if(failure&&$('#history-panel').classList.contains('open'))notice(failure.reason.message);
 }finally{detailsRefreshing=false;}
}
async function refresh(){if(!LOCAL||polling||recording)return;polling=true;try{
 const requested=current;
 const [nextHealth,data]=await Promise.all([api('/health'),requested?api(`/conversations/${requested}`).catch(error=>{if(error.status===404)return {missing:true};throw error;}):Promise.resolve(null)]);
 if(current!==requested)return;
 health=nextHealth;busy=health.active;
 if(data?.missing)selectId(null);
 $('#connection').textContent=health.ready?'Local companion connected':'Local setup needs attention';$('#connection').classList.toggle('warning',!health.ready);
 turns=data?.turns||[];renderTurns();
 // Drawer data must never hold up ready speech or the next voice poll.
 refreshDetails(requested,data?.project_id);

if(liveTurn){const reply=turns.find(t=>t.id===liveTurn);if(reply?.has_stream||(reply?.status==='complete'&&reply.has_audio)){const id=liveTurn;liveTurn=null;liveOutputTurn=id;autoPlayId=null;await live.play(`/api/turns/${id}/${reply.has_stream?'audio-stream':'audio'}`,{pauseAfter:reply.client_action==='pause_listening'});}else if(reply?.status==='unheard'){liveTurn=null;autoPlayId=null;live.unheard();}else if(reply&&['failed','cancelled','interrupted'].includes(reply.status)){liveTurn=null;live.fail(reply.error||'The reply stopped. Tap the orb to continue.');}}
if(!live.enabled&&!recording&&[...document.querySelectorAll('audio')].every(a=>a.paused)){const active=turns.find(t=>activeStates.includes(t.status));if(active)setStage(active.status,({queued:'Starting your turn…',transcribing:'Turning your voice into words…',thinking:'Thinking through a reply…',synthesizing:'Preparing a spoken response…'})[active.status]);else if(busy)setStage('thinking','A turn is running in another conversation');else if(!document.querySelector('audio')||[...document.querySelectorAll('audio')].every(a=>a.paused))setStage('idle',health.ready?'Ready for your next thought':'Text is available · check setup for missing tools');}controls();}catch(error){health=null;$('#connection').textContent='Companion disconnected';setStage('error','Start the companion, then reconnect');notice(error.message);controls();}finally{polling=false;announcements.tick();}}
let conversationCreation=null;
async function ensureConversation(){if(current)return current;if(conversationCreation)return conversationCreation;conversationCreation=createConversation();try{return await conversationCreation;}finally{conversationCreation=null}}
async function createConversation(){const c=await api('/conversations',{method:'POST'});if(memory?.selected())await api(`/conversations/${c.id}/project`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:memory.selected()})});selectId(c.id);conversations.unshift(c);renderList();return c.id}
async function submitText(text){if(posting||busy)return;posting=true;notice('');controls();try{const cid=await ensureConversation();const t=await submitTurn(api,'/turns',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({conversation_id:cid,text})});busy=t.id;autoPlayId=t.id;$('#message').value='';await refresh()}catch(error){notice(error.message)}finally{posting=false;controls()}}
async function submitAudio(blob,draftHeaders={}){if(blob.size>10*1024*1024){notice('Choose a recording smaller than 10 MB.');return}posting=true;controls();notice('');try{const cid=await ensureConversation();const t=await submitTurn(api,'/audio?conversation_id='+cid,{method:'POST',headers:{'Content-Type':blob.type||'application/octet-stream',...draftHeaders},body:blob});busy=t.id;autoPlayId=t.id;await refresh();return t.id;}catch(error){notice(error.message);return null;}finally{posting=false;controls()}}
function stopTracks(){stream?.getTracks().forEach(t=>t.stop());stream=null;audioContext?.close().catch(()=>{});audioContext=null;clearInterval(recordTimer);recording=false;controls();}
function stopRecording(discard=false){if(recorder?.state==='recording'){recorder.discard=discard;recorder.stop()}else stopTracks()}
async function startRecording(){if(requestingMic)return;if(recording){stopRecording();return}notice('');if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder){notice('Recording is unavailable in this browser. Upload an audio file or type instead.');return}requestingMic=true;controls();try{document.querySelectorAll('audio').forEach(a=>a.pause());stream=await navigator.mediaDevices.getUserMedia({audio:true});requestingMic=false;const mime=['audio/webm;codecs=opus','audio/mp4','audio/webm'].find(x=>MediaRecorder.isTypeSupported(x));recorder=new MediaRecorder(stream,mime?{mimeType:mime}:undefined);chunks=[];recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};recorder.onerror=()=>{recorder.discard=true;stopTracks();notice('Recording stopped unexpectedly. Try again, upload a file, or type instead.')};recorder.onstop=()=>{const discard=recorder.discard,blob=new Blob(chunks,{type:recorder.mimeType});stopTracks();setStage('idle','Ready for your next thought');if(!discard&&blob.size)submitAudio(blob)};recorder.start();recording=true;recordingStarted=Date.now();controls();setStage('recording','Listening · finish when you’re ready');recordTimer=setInterval(()=>{const seconds=Math.floor((Date.now()-recordingStarted)/1000);$('#record-time').textContent=`Recording · ${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')} / 1:00`;if(seconds>=60)stopRecording()},200);try{audioContext=new AudioContext();const analyser=audioContext.createAnalyser();analyser.fftSize=256;audioContext.createMediaStreamSource(stream).connect(analyser);const samples=new Uint8Array(analyser.fftSize);function meter(){if(!recording||!audioContext)return;analyser.getByteTimeDomainData(samples);updateOrb(null,Math.sqrt(samples.reduce((s,x)=>s+(x-128)**2,0)/samples.length)/25);requestAnimationFrame(meter)}meter()}catch{}}catch(error){stopTracks();notice(error.name==='NotAllowedError'?'Microphone access was denied. You can allow it in your browser settings, upload an audio file, or keep typing.':'The microphone could not start. Check that it is connected, or upload audio / type instead.')}finally{requestingMic=false;controls()}}
$('#text-form').onsubmit=e=>{e.preventDefault();const text=$('#message').value.trim();if(text)submitText(text)};
$('#message').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('#text-form').requestSubmit()}};
$('#record').onclick=startRecording;$('#discard').onclick=()=>stopRecording(true);$('#upload').onclick=()=>$('#audio-file').click();$('#audio-file').onchange=e=>{const file=e.target.files[0];e.target.value='';if(file)submitAudio(file)};
$('#cancel').onclick=async()=>{if(!busy)return;$('#cancel').disabled=true;try{await api(`/turns/${busy}/cancel`,{method:'POST'});notice('Stopping the current step…');await refresh()}catch(e){notice(e.message)}};
$('#new').onclick=()=>{if(recording)return;selectId(null);turns=[];lastSignature='';renderList();renderTurns();jobs?.refresh();$('#message').value='';notice('');setHistory(false);$('#orb').focus()};
$('#conversations').onclick=async e=>{const button=e.target.closest('[data-conversation]');if(button&&!recording){selectId(button.dataset.conversation);lastSignature='';setHistory(false);await refresh()}};
$('#turns').onclick=async e=>{const button=e.target.closest('[data-retry]');if(button){try{posting=true;controls();const t=await api(`/turns/${button.dataset.retry}/retry`,{method:'POST'});busy=t.id;autoPlayId=t.id;notice('');await refresh()}catch(error){notice(error.message)}finally{posting=false;controls()}}};
function setHistory(expanded){if(expanded)live.stop();$('#history-panel').classList.toggle('open',expanded);$('#history-panel').inert=!expanded;$('#history-toggle').setAttribute('aria-expanded',String(expanded));$('#history-backdrop').hidden=!expanded;if(!expanded&&$('#history-panel').contains(document.activeElement))$('#history-toggle').focus();}
$('#history-toggle').onclick=()=>setHistory(!$('#history-panel').classList.contains('open'));$('#history-backdrop').onclick=()=>setHistory(false);document.addEventListener('keydown',e=>{if(e.key==='Escape')setHistory(false)});
const voiceSettings=mountVoiceSettings(LOCAL);
function showSetup(){voiceSettings.refresh();$('#checks').innerHTML=health?Object.entries(health.checks).map(([key,ok])=>`<div class="check"><span>${esc(key)}</span><span class="${ok?'good':'missing'}">${ok?'Available':'Needs setup'}</span></div>`).join(''):'<p class="small">Open the local companion to check installed models.</p>';$('#setup-dialog').showModal()}
$('#setup').onclick=$('#host-setup').onclick=showSetup;$('#close-setup').onclick=()=>$('#setup-dialog').close();
$('#copy-command').onclick=async()=>{try{await navigator.clipboard.writeText('cd ~/Developer/ai-voice-agent && python3 mac_service.py status');$('#copy-command').textContent='Copied'}catch{$('#copy-command').textContent='Select and copy the command above'}};
$('#export').onclick=async()=>{try{const data=await api(`/conversations/${current}/export`);const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='voice-conversation-'+current.slice(0,8)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(e){notice(e.message)}};
$('#delete').onclick=()=>$('#delete-dialog').showModal();$('#keep').onclick=()=>$('#delete-dialog').close();$('#confirm-delete').onclick=async()=>{try{await api(`/conversations/${current}`,{method:'DELETE'});selectId(null);$('#delete-dialog').close();await refresh()}catch(e){$('#delete-dialog').close();notice(e.message)}};
window.addEventListener('pagehide',()=>{live.suspend();if(recording)stopRecording(true);stopTracks()});
let lastIdleRefresh=0;
if(LOCAL){memory.init();selectId(null);refresh();setInterval(()=>{if(busy||Date.now()-lastIdleRefresh>1500){lastIdleRefresh=Date.now();refresh()}},150)}else{$('#new').disabled=true;$('#history-toggle').hidden=true;$('#conversations').innerHTML='<p class="history-empty">Your history lives in<br>the local companion.</p>'}

if(LOCAL)navigator.permissions?.query({name:'microphone'}).then(p=>{if(p.state==='granted'&&!document.hidden)live.start(true);}).catch(()=>{});
