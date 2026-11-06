// Link only explicit HTTP(S) sources; all other report content remains escaped text.
export function reportLinks(text,escape){
 return String(text||'').split(/(https?:\/\/[^\s<>"\]\)]+)/g).map(part=>{
  if(!/^https?:\/\//.test(part))return escape(part);
  const clean=part.replace(/[.,;:!?]+$/,'');
  try{const url=new URL(clean);if(!['http:','https:'].includes(url.protocol))return escape(part);}catch{return escape(part);}
  return `<a href="${escape(clean)}" target="_blank" rel="noopener noreferrer">${escape(clean)}</a>${escape(part.slice(clean.length))}`;
 }).join('');
}
