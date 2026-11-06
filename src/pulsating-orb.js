import * as THREE from 'three';
let currentState='idle', level=0, smoothed=0, root, invalidateOrb=()=>{};
const palette={idle:0x69dfff,recording:0x96fff1,thinking:0x65bfff,transcribing:0x65bfff,queued:0x65bfff,synthesizing:0x9fe6ff,speaking:0xc3f7ff,error:0xe9aa66};
const target=new THREE.Color(palette.idle);
export function initializeOrb(container){
  root=container;
  try{
    const renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'});
    renderer.setPixelRatio(Math.min(devicePixelRatio,1.75));
    renderer.setClearColor(0x000000,0);
    const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(40,1,.1,30);
    camera.position.z=5.8;
    const globe=new THREE.Group();scene.add(globe);
    const lineMaterial=new THREE.LineBasicMaterial({color:0x65dfff,transparent:true,opacity:.44,blending:THREE.AdditiveBlending,depthWrite:false});
    // Spherical latitude and longitude lines, not a painted orb image.
    for(let lat=-4;lat<=4;lat++){
      const phi=lat*Math.PI/12,r=Math.cos(phi)*1.05,y=Math.sin(phi)*1.05;
      const pts=Array.from({length:145},(_,i)=>new THREE.Vector3(r*Math.cos(i*Math.PI/72),y,r*Math.sin(i*Math.PI/72)));
      globe.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),lineMaterial));
    }
    for(let meridian=0;meridian<12;meridian++){
      const a=meridian*Math.PI/12;
      const pts=Array.from({length:145},(_,i)=>{const t=i*Math.PI/72;return new THREE.Vector3(Math.cos(t)*Math.cos(a)*1.05,Math.sin(t)*1.05,Math.cos(t)*Math.sin(a)*1.05)});
      globe.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),lineMaterial));
    }
    const particles=[];
    for(let i=0;i<850;i++){
      const y=1-2*i/849,a=i*2.39996323,r=Math.sqrt(1-y*y);
      particles.push(r*Math.cos(a)*1.08,y*1.08,r*Math.sin(a)*1.08);
    }
    const particleMaterial=new THREE.PointsMaterial({color:0x9feeff,size:.018,transparent:true,opacity:.6,blending:THREE.AdditiveBlending,depthWrite:false});
    const particleGeometry=new THREE.BufferGeometry();particleGeometry.setAttribute('position',new THREE.Float32BufferAttribute(particles,3));globe.add(new THREE.Points(particleGeometry,particleMaterial));
    const rings=[];
    for(let n=0;n<7;n++){
      const group=new THREE.Group(),r=1.26+n*.095;
      const mat=new THREE.LineBasicMaterial({color:n===3?0xd5ab64:0x61dfff,transparent:true,opacity:n===3?.65:.6,blending:THREE.AdditiveBlending,depthWrite:false});
      for(let j=0;j<3;j++){
        const start=j*Math.PI*2/3+n*.33,span=n%2?1.3:1.8;
        const pts=Array.from({length:81},(_,i)=>{const a=start+i/80*span;return new THREE.Vector3(Math.cos(a)*r,Math.sin(a)*r,0)});
        group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),mat));
      }
      group.rotation.x=n===1?.65:n===4?-.35:0;group.rotation.y=n===5?.3:0;
      scene.add(group);rings.push(group);
    }
    const ticks=[];
    for(let i=0;i<120;i++){
      const a=i*Math.PI/60,r=i%5===0?1.94:1.91;
      ticks.push(Math.cos(a)*1.86,Math.sin(a)*1.86,0,Math.cos(a)*r,Math.sin(a)*r,0);
    }
    const tickGeo=new THREE.BufferGeometry();tickGeo.setAttribute('position',new THREE.Float32BufferAttribute(ticks,3));
    scene.add(new THREE.LineSegments(tickGeo,new THREE.LineBasicMaterial({color:0x79cbdf,transparent:true,opacity:.42})));
    const glow=new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,uniforms:{t:{value:0},energy:{value:0},color:{value:target.clone()}},vertexShader:'varying vec2 v; void main(){v=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:`varying vec2 v;uniform float t;uniform float energy;uniform vec3 color;
      void main(){vec2 p=(v-.5)*2.;float r=length(p);float core=exp(-r*r*85.);float halo=exp(-r*r*4.)*.12;float shell=exp(-pow((r-.49)*45.,2.))*.16;float beam=exp(-abs(p.y)*260.)*exp(-r*3.)*.22;float flare=(core*(.6+energy)+halo+shell+beam);gl_FragColor=vec4(color+vec3(core*.3),clamp(flare,0.,1.));}`});
    const glowPlane=new THREE.Mesh(new THREE.PlaneGeometry(4.5,4.5),glow);scene.add(glowPlane);
    renderer.domElement.setAttribute('aria-hidden','true');container.append(renderer.domElement);
    const resize=()=>{const {width,height}=container.getBoundingClientRect();if(!width||!height)return;renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();invalidateOrb()};new ResizeObserver(resize).observe(container);resize();
    const motion=matchMedia('(prefers-reduced-motion: reduce)');let last=0,phase=0,frameId=0,contextLost=false,pageHidden=false;
    function schedule(){if(!frameId&&!document.hidden&&!pageHidden&&!contextLost)frameId=requestAnimationFrame(frame);}
    function pause(){cancelAnimationFrame(frameId);frameId=0;last=0;}
    function frame(t){
      frameId=0;if(document.hidden||pageHidden||contextLost)return;
      if(!motion.matches&&last&&t-last<1000/30-.1){schedule();return;}
      const dt=last?Math.min((t-last)/1000,.05):1/30;last=t;
      smoothed=motion.matches?0:smoothed+(level-smoothed)*(1-Math.exp(-dt*10));
      const active=['thinking','transcribing','synthesizing','queued'].includes(currentState);
      if(!motion.matches){phase+=dt*(active?.32:.1);globe.rotation.y=phase;globe.rotation.z=Math.sin(phase*.6)*.12;rings.forEach((g,i)=>g.rotation.z=phase*(i%2?-1:1)*(i*.15+.4));}
      const energy=motion.matches?0:smoothed,blend=motion.matches?1:1-Math.exp(-dt*5);
      globe.scale.setScalar(1+energy*.16);glow.uniforms.energy.value=energy;glow.uniforms.t.value=t/1000;glow.uniforms.color.value.lerp(target,blend);
      lineMaterial.color.lerp(target,blend);lineMaterial.opacity=.4+energy*.4;particleMaterial.opacity=.65+energy*.35;
      rings.forEach((g,i)=>g.scale.setScalar(1+energy*.035*Math.sin(i+phase*2)));
      renderer.render(scene,camera);
      if(!motion.matches)schedule();
    }
    invalidateOrb=schedule;
    motion.addEventListener('change',()=>{pause();schedule()});
    document.addEventListener('visibilitychange',()=>{pause();schedule()});
    window.addEventListener('pagehide',()=>{pageHidden=true;pause()});
    window.addEventListener('pageshow',()=>{pageHidden=false;schedule()});
    schedule();
    renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();contextLost=true;pause();container.classList.add('orb-unavailable')});
    renderer.domElement.addEventListener('webglcontextrestored',()=>{contextLost=false;container.classList.remove('orb-unavailable');schedule()});
  }catch{container.classList.add('orb-unavailable');container.textContent='';}
}
export function updateOrb(state,value){
  if(state){const changed=state!==currentState;currentState=state;target.set(palette[state]||palette.idle);if(root)root.dataset.state=state;if(changed)invalidateOrb();}
  if(value!==undefined){level=Math.max(0,Math.min(1,value));if(root)root.dataset.level=level.toFixed(3);}
}
let playbackContext;const sources=new WeakMap();let playbackGeneration=0;
export async function meterPlayback(audio){
  const generation=++playbackGeneration;
  try{
    playbackContext ||= new AudioContext();await playbackContext.resume();
    let source=sources.get(audio);if(!source){source=playbackContext.createMediaElementSource(audio);sources.set(audio,source)}
    source.disconnect();const analyser=playbackContext.createAnalyser();analyser.fftSize=256;source.connect(analyser);analyser.connect(playbackContext.destination);
    const samples=new Uint8Array(analyser.fftSize);
    function frame(){if(audio.paused||audio.ended||generation!==playbackGeneration){try{source.disconnect(analyser)}catch{}analyser.disconnect();if(currentState==='speaking'&&generation===playbackGeneration)updateOrb(null,0);return;}
      analyser.getByteTimeDomainData(samples);const rms=Math.sqrt(samples.reduce((s,x)=>s+(x-128)**2,0)/samples.length)/32;updateOrb(null,rms);requestAnimationFrame(frame);
    }frame();
  }catch{/* Playback remains usable when Web Audio is unavailable. */}
}
