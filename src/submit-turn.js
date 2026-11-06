// Reuse one request identity if an acknowledgement is lost. The Mac deduplicates
// before starting work, including if the first request has already completed.
export async function submitTurn(api,path,options,{timeout=20000,delay=400}={}){
 const id=crypto.randomUUID().replaceAll('-','');
 for(let attempt=0;attempt<2;attempt++){
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeout);
  try{return await api(path,{...options,signal:controller.signal,headers:{...options.headers,'X-Voice-Request':id}});}
  catch(error){if(attempt||error.status&&error.status<500)throw error;}
  finally{clearTimeout(timer);}
  await new Promise(resolve=>setTimeout(resolve,delay));
 }
}
