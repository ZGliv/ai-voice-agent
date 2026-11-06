const job=new URLSearchParams(location.search).get('job');
if(job&&/^[a-f0-9]{32}$/.test(job))import('./job-view.js').then(m=>m.mountJobView(job));
else import('./app.js');
