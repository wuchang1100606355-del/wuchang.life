import * as THREE from 'three';
import { GLTFLoader } from '../node_modules/three/examples/jsm/loaders/GLTFLoader.js';

const canvas=document.querySelector('#raw');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(1); renderer.setSize(innerWidth,innerHeight,false); renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.shadowMap.enabled=true;
const scene=new THREE.Scene(); scene.background=new THREE.Color(0xd7d9dc);
const camera=new THREE.PerspectiveCamera(28,innerWidth/innerHeight,.001,1000);
scene.add(new THREE.HemisphereLight(0xffffff,0x7b8790,2.5));
const key=new THREE.DirectionalLight(0xffffff,3.2); key.position.set(3,5,5); key.castShadow=true; scene.add(key);
const fill=new THREE.DirectionalLight(0xbad9ff,1.4); fill.position.set(-4,2,3); scene.add(fill);
const rim=new THREE.DirectionalLight(0xffffff,1.1); rim.position.set(0,3,-5); scene.add(rim);

const asset=new URLSearchParams(location.search).get('asset')||'raw';
const assetPath=asset==='rigged'?'../assets/xiaoj_clean_humanoid_rigged.glb':asset==='clean'?'../assets/xiaoj_clean_humanoid_stage1.glb':'../assets/xiaoj_single_core_geometry.glb';
new GLTFLoader().load(assetPath,({scene:model})=>{
  model.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}});
  scene.add(model);
  const box=new THREE.Box3().setFromObject(model),size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3());
  const floor=new THREE.Mesh(new THREE.PlaneGeometry(Math.max(size.x,size.z)*4,Math.max(size.x,size.z)*4),new THREE.MeshStandardMaterial({color:0xc9ccd0,roughness:.9}));
  floor.rotation.x=-Math.PI/2; floor.position.y=box.min.y-size.y*.005; floor.receiveShadow=true; scene.add(floor);
  const view=new URLSearchParams(location.search).get('view')||'front';
  const dist=Math.max(size.y*2.05,size.x*4.0,size.z*5.0);
  const direction={front:[0,0,1],left:[1,0,0],back:[0,0,-1]}[view]||[0,0,1];
  camera.position.set(center.x+direction[0]*dist,center.y+size.y*.01,center.z+direction[2]*dist);
  camera.lookAt(center.x,center.y+size.y*.01,center.z); camera.near=dist/100;camera.far=dist*3;camera.updateProjectionMatrix();
  document.querySelector('#stamp').textContent=`${view.toUpperCase()} · ${asset.toUpperCase()} GLB · RIG OFF · SKIN OFF · ADI OFF`;
  renderer.render(scene,camera);
  document.documentElement.dataset.stage1='ready';
},undefined,error=>{document.documentElement.dataset.stage1='error';document.querySelector('#stamp').textContent=`LOAD ERROR: ${error}`;});
