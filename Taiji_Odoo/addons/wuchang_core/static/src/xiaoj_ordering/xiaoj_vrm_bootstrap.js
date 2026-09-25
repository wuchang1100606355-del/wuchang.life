import * as THREE from "https://esm.sh/three@0.160.0";
import { GLTFLoader } from "https://esm.sh/three@0.160.0/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "https://esm.sh/three@0.160.0/examples/jsm/controls/OrbitControls.js";
import { VRMLoaderPlugin, VRMUtils } from "https://esm.sh/@pixiv/three-vrm@2.1.2?deps=three@0.160.0";

const VRM_PATH = "/wuchang_core/static/src/xiaoj_ordering/avatar/lung.vrm";

function mountStage() {
  let stage = document.getElementById("xiaoj-vrm-stage");
  if (!stage) {
    stage = document.createElement("div");
    stage.id = "xiaoj-vrm-stage";
    stage.style.cssText = `
      position: fixed;
      right: 16px;
      bottom: 16px;
      width: 360px;
      height: 520px;
      z-index: 9999;
      border-radius: 18px;
      overflow: hidden;
      background: radial-gradient(circle at center,#343434,#111);
      box-shadow: 0 12px 40px rgba(0,0,0,.45);
    `;
    document.body.appendChild(stage);
  }
  return stage;
}

function showStatus(stage, text) {
  let box = document.getElementById("xiaoj-vrm-status");
  if (!box) {
    box = document.createElement("div");
    box.id = "xiaoj-vrm-status";
    box.style.cssText = `
      position:absolute; left:10px; top:10px;
      color:#fff; background:rgba(0,0,0,.55);
      padding:8px 10px; border-radius:10px;
      font:14px system-ui,sans-serif;
      z-index:2;
    `;
    stage.appendChild(box);
  }
  box.textContent = text;
}

async function boot() {
  const stage = mountStage();
  showStatus(stage, "小J 3D 載入中…");

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(28, stage.clientWidth / stage.clientHeight, 0.1, 20);
  camera.position.set(0, 1.25, 3.0);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(stage.clientWidth, stage.clientHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  stage.appendChild(renderer.domElement);

  const light = new THREE.DirectionalLight(0xffffff, 2.2);
  light.position.set(1, 2, 3);
  scene.add(light);
  scene.add(new THREE.AmbientLight(0xffffff, 1.2));

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 1.05, 0);
  controls.enableDamping = true;
  controls.enablePan = false;

  const loader = new GLTFLoader();
  loader.register((parser) => new VRMLoaderPlugin(parser));

  loader.load(
    VRM_PATH,
    (gltf) => {
      VRMUtils.removeUnnecessaryVertices(gltf.scene);
      VRMUtils.removeUnnecessaryJoints(gltf.scene);

      const vrm = gltf.userData.vrm;
      scene.add(vrm.scene);
      vrm.scene.rotation.y = Math.PI;
      vrm.scene.position.set(0, -0.85, 0);

      showStatus(stage, "小J 3D 已啟動");

      const clock = new THREE.Clock();
      function animate() {
        requestAnimationFrame(animate);
        const dt = clock.getDelta();
        if (vrm) vrm.update(dt);
        controls.update();
        renderer.render(scene, camera);
      }
      animate();
    },
    undefined,
    (err) => {
      console.error(err);
      showStatus(stage, "小J 3D 載入失敗：請檢查 VRM / CDN / 網路");
    }
  );

  window.addEventListener("resize", () => {
    renderer.setSize(stage.clientWidth, stage.clientHeight);
    camera.aspect = stage.clientWidth / stage.clientHeight;
    camera.updateProjectionMatrix();
  });
}

boot().catch((err) => {
  console.error(err);
  const stage = mountStage();
  showStatus(stage, "小J 3D runtime 載入失敗");
});
