import * as THREE from 'three';
import { vertexShader } from './orb.vertex.glsl.js';
import { fragmentShader } from './orb.fragment.glsl.js';
let material, orb, target = new THREE.Color(0x174dff), amplitude = .12;
const states = {idle:0x174dff,recording:0x00e3ea,thinking:0x6f53ff,synthesizing:0x8b74ff,speaking:0xff6644,error:0x4a6792};
export function initializeOrb(container) {
  try {
    const renderer = new THREE.WebGLRenderer({alpha:true,antialias:true});
    renderer.setPixelRatio(Math.min(devicePixelRatio,2));
    const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(65,1,.1,100);
    camera.position.z=5.2;
    material=new THREE.ShaderMaterial({vertexShader,fragmentShader,transparent:true,uniforms:{time:{value:0},baseColor:{value:target.clone()},amplitude:{value:.12},pulseSpeed:{value:.5},pulseIntensity:{value:.2},noiseIntensity:{value:.5}}});
    orb=new THREE.Mesh(new THREE.SphereGeometry(2,64,64),material);scene.add(orb);
    renderer.domElement.setAttribute('aria-hidden','true');container.append(renderer.domElement);
    new ResizeObserver(()=>{const {width,height}=container.getBoundingClientRect();renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix()}).observe(container);
    const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
    function frame(t){requestAnimationFrame(frame);if(document.hidden)return;material.uniforms.time.value=reduced?0:t/1600;material.uniforms.baseColor.value.lerp(target,.06);material.uniforms.amplitude.value+=(amplitude-material.uniforms.amplitude.value)*.1;if(!reduced){orb.rotation.y=t/10000;orb.rotation.x=t/20000}renderer.render(scene,camera)}requestAnimationFrame(frame);
  } catch {container.classList.add('orb-fallback');}
}
export function updateOrb(state, level) {
  if(state){target.set(states[state]||states.idle);if(material){material.uniforms.pulseSpeed.value=state==='recording'?2:.6;material.uniforms.noiseIntensity.value=state==='recording'?1.1:.5}}
  if(level!==undefined)amplitude=Math.max(.1,Math.min(.8,level));
}
