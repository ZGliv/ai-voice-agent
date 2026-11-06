async (page) => {
 const options=__JARVIS_OPTIONS__;
 const origin=new URL(options.url).origin;
 const testPage=await page.context().newPage();
 const runs=[];let errors=[],badAssets=[];
 testPage.on('pageerror',error=>errors.push(error.message.slice(0,300)));
 testPage.on('dialog',dialog=>dialog.dismiss());
 testPage.on('popup',popup=>popup.close());
 await testPage.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());
 testPage.on('response',response=>{if(response.status()>=400&&!response.url().endsWith('/favicon.ico'))badAssets.push(response.url().slice(0,200));});
 try{
  for(const size of [{name:'desktop',width:1440,height:1000},{name:'mobile',width:390,height:844}]){
   errors=[];badAssets=[];const checks=[];
   await testPage.setViewportSize({width:size.width,height:size.height});
   try{
    const response=await testPage.goto(options.url,{waitUntil:'domcontentloaded',timeout:15000});
    if(!response?.ok())throw Error('Preview document did not load successfully.');
    await testPage.waitForTimeout(250);
    const overflow=await testPage.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
    checks.push({name:'No horizontal overflow',passed:!overflow});
    for(let i=0;i<options.steps.length;i++){
     const step=options.steps[i];
     try{
      const target=step.selector?testPage.locator(step.selector):null;
      if(step.action==='click')await target.click({timeout:3000});
      if(step.action==='fill')await target.fill(step.text,{timeout:3000});
      if(step.action==='visible'&&!await target.isVisible())throw Error('Element is not visible.');
      if(step.action==='wait')await testPage.waitForTimeout(step.ms);
      if(['expect_text','expect_not_text'].includes(step.action)){
       const actual=await target.innerText({timeout:3000}),contains=actual.includes(step.text);
       if(step.action==='expect_text'?!contains:contains)throw Error('Text assertion failed; actual: '+actual.slice(0,150));
      }
      if(step.action==='expect_value'&&await target.inputValue({timeout:3000})!==step.text)throw Error('Input value assertion failed.');
      if(new URL(testPage.url()).origin!==origin)throw Error('Check navigated away from the preview.');
      checks.push({name:`${i+1}. ${step.action} ${step.selector||''}`,passed:true});
     }catch(error){checks.push({name:`${i+1}. ${step.action} ${step.selector||''}`,passed:false,error:String(error.message).slice(0,300)});break;}
    }
    checks.push({name:'No overflow after interaction',passed:!await testPage.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1)});
    checks.push({name:'No JavaScript exceptions',passed:errors.length===0,errors});
    checks.push({name:'Local assets loaded',passed:badAssets.length===0,errors:badAssets});
    await testPage.screenshot({path:options.directory+'/'+size.name+'.png',fullPage:false,timeout:5000});
   }catch(error){checks.push({name:'Browser run',passed:false,error:String(error.message).slice(0,300)});}
   runs.push({viewport:size.name,checks});
  }
  const failed=runs.some(run=>run.checks.some(check=>!check.passed));
  return {status:failed?'failed':options.steps.length?'passed':'smoke_passed',summary:failed?'Browser checks found problems.':options.steps.length?'Desktop and mobile checks passed.':'Desktop and mobile load checks passed; no interaction checks were provided.',interactionSteps:options.steps.length,runs,network:'Only preview-origin requests allowed during verification.'};
 }finally{await testPage.close();}
}
