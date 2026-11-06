export function verificationReport(job){
 try {const report=typeof job.verification==='string'?JSON.parse(job.verification):job.verification;return report&&typeof report==='object'?report:{};}catch{return {};}
}
export function verificationHtml(job,esc){
 const report=verificationReport(job);if(!report.status)return '';
 return `<details class="job-verification"><summary>${esc(report.summary||'Browser verification: '+report.status)}</summary>${report.repair?`<p>One automatic repair attempted. ${esc(report.repair.error||"Original checks repeated without changes.")}</p>`:""}${(report.runs||[]).map(run=>`<p>${esc(run.viewport)}</p><ul>${(run.checks||[]).map(check=>`<li>${check.passed?'Passed':'Failed'}: ${esc(check.name)}${check.error?` — ${esc(check.error)}`:''}${check.errors?.length?` — ${esc(check.errors.join('; '))}`:''}</li>`).join('')}</ul>`).join('')}<p class="small">${esc(report.network||'No browser verification evidence is available.')}</p></details>`;
}
export function canAutoOpen(job){return job.status==='completed'&&!job.error&&['passed','smoke_passed'].includes(verificationReport(job).status);}
