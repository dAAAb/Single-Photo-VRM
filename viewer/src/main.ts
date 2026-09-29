import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { VRM, VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
import {
  VRMAnimation, VRMAnimationLoaderPlugin, VRMLookAtQuaternionProxy, createVRMAnimationClip,
} from '@pixiv/three-vrm-animation';
import { ARKIT_52, arkitToPresets } from './arkit';
import { arkitReport, metaSummary, runChecks, type ArkitRow } from './checks';
import { FaceTracker } from './face';
import { Locomotion, type LocoState } from './locomotion';
import { loadMixamoFBX, retargetMixamo } from './mixamo';

// ---------- scene ----------
const canvas = document.querySelector<HTMLCanvasElement>('#c')!;
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 1, 0.05, 200);
camera.position.set(0, 1.4, 3.2);
const controls = new OrbitControls(camera, canvas);
controls.target.set(0, 1.0, 0);
controls.enableDamping = true;

scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8f99, 1.6));
const sun = new THREE.DirectionalLight(0xffffff, 1.8);
sun.position.set(1.5, 3, 2);
scene.add(sun);
const grid = new THREE.GridHelper(40, 40, 0x888888, 0xbbbbbb);
(grid.material as THREE.Material).transparent = true;
(grid.material as THREE.Material).opacity = 0.5;
scene.add(grid);
const shadow = new THREE.Mesh(
  new THREE.CircleGeometry(0.35, 32).rotateX(-Math.PI / 2),
  new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.18, depthWrite: false }),
);
shadow.position.y = 0.002;
scene.add(shadow);

const loco = new Locomotion(camera);
scene.add(loco.root);
const lookTarget = new THREE.Object3D();
camera.add(lookTarget);
scene.add(camera);

function resize() {
  const { clientWidth: w, clientHeight: h } = canvas.parentElement!;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(canvas.parentElement!);

// ---------- loaders ----------
const loader = new GLTFLoader();
loader.register((p) => new VRMLoaderPlugin(p));
loader.register((p) => new VRMAnimationLoaderPlugin(p));

let vrm: VRM | null = null;
let mixer: THREE.AnimationMixer | null = null;
const face = new FaceTracker();

interface ClipSource { id: number; name: string; kind: 'vrma' | 'fbx'; vrma?: VRMAnimation; fbx?: THREE.Group; clip?: THREE.AnimationClip }
const clips: ClipSource[] = [];
let clipSeq = 0;
const slots: Record<LocoState, number | null> = { idle: null, walk: null, run: null, jump: null };
let previewClip: number | null = null; // manual playback while idle
let activeAction: THREE.AnimationAction | null = null;
let activeKey = '';

const sliderValues: Record<string, number> = {};

function toast(msg: string, ms = 2600) {
  const t = document.querySelector('#toast')!;
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout((t as any)._h);
  (t as any)._h = setTimeout(() => t.classList.remove('show'), ms);
}

async function loadVRM(url: string, name: string) {
  const gltf = await loader.loadAsync(url);
  const next = gltf.userData.vrm as VRM | undefined;
  if (!next) throw new Error('這不是 VRM 檔（找不到 VRM 擴充）');
  if (vrm) {
    loco.root.remove(vrm.scene);
    VRMUtils.deepDispose(vrm.scene);
  }
  VRMUtils.removeUnnecessaryVertices(gltf.scene);
  VRMUtils.combineSkeletons(gltf.scene);
  VRMUtils.rotateVRM0(next);
  next.scene.traverse((o) => { o.frustumCulled = false; });
  if (next.lookAt) {
    next.lookAt.target = lookTarget;
    const proxy = new VRMLookAtQuaternionProxy(next.lookAt);
    proxy.name = 'lookAtQuaternionProxy';
    next.scene.add(proxy);
  }
  vrm = next;
  loco.root.add(vrm.scene);
  mixer = new THREE.AnimationMixer(vrm.scene);
  activeAction = null;
  activeKey = '';
  for (const c of clips) c.clip = undefined; // rebuild per-model
  for (const k of Object.keys(sliderValues)) delete sliderValues[k];

  // frame the camera on the model
  vrm.scene.updateMatrixWorld(true);
  const head = vrm.humanoid.getNormalizedBoneNode('head')?.getWorldPosition(new THREE.Vector3());
  const h = head ? head.y + 0.15 : 1.6;
  const p = loco.root.position;
  controls.target.set(p.x, p.y + h * 0.52, p.z);
  camera.position.set(p.x, p.y + h * 0.62, p.z + h * 3.1);

  document.querySelector('#drop-hint')!.setAttribute('hidden', '');
  document.querySelector('#model-name')!.textContent = name;
  renderChecks();
  renderExprSliders();
  renderSyncSliders();
  renderClips();
  toast(`已載入 ${name}`);
}

async function addClip(url: string, name: string, kind: 'vrma' | 'fbx') {
  const src: ClipSource = { id: ++clipSeq, name, kind };
  if (kind === 'vrma') {
    const gltf = await loader.loadAsync(url);
    src.vrma = gltf.userData.vrmAnimations?.[0];
    if (!src.vrma) throw new Error('這不是 VRMA 檔');
  } else {
    src.fbx = await loadMixamoFBX(url);
  }
  clips.push(src);
  // auto-assign by filename
  const n = name.toLowerCase();
  const guess: LocoState | null = /jump/.test(n) ? 'jump' : /run|sprint/.test(n) ? 'run' : /walk/.test(n) ? 'walk' : /idle|stand|breath/.test(n) ? 'idle' : null;
  if (guess && slots[guess] == null) slots[guess] = src.id;
  else previewClip = src.id;
  renderClips();
  toast(guess && slots[guess] === src.id ? `已載入 ${name} → 指定為「${SLOT_LABEL[guess]}」` : `已載入 ${name}，正在播放`);
}

function clipFor(id: number): THREE.AnimationClip | null {
  const src = clips.find((c) => c.id === id);
  if (!src || !vrm) return null;
  if (!src.clip) {
    try {
      src.clip = src.kind === 'vrma' ? createVRMAnimationClip(src.vrma!, vrm) : retargetMixamo(src.fbx!, vrm);
      if (src.kind === 'fbx') stripRootMotion(src.clip);
    } catch (e) {
      toast(`動作套用失敗：${(e as Error).message}`);
      return null;
    }
  }
  return src.clip;
}

/** Keep locomotion in place: drop horizontal hips translation (the controller moves the root). */
function stripRootMotion(clip: THREE.AnimationClip) {
  for (const t of clip.tracks) {
    if (t instanceof THREE.VectorKeyframeTrack && t.name.endsWith('.position')) {
      const x0 = t.values[0], z0 = t.values[2];
      for (let i = 0; i < t.values.length; i += 3) { t.values[i] = x0; t.values[i + 2] = z0; }
    }
  }
}

async function handleFiles(files: FileList | File[]) {
  const list = Array.from(files).sort((a) => (/\.vrm$|\.glb$/i.test(a.name) ? -1 : 1));
  for (const f of list) {
    const url = URL.createObjectURL(f);
    try {
      if (/\.(png|jpe?g|webp)$/i.test(f.name)) await photoToVRM(f);
      else if (/\.(vrm|glb)$/i.test(f.name)) await loadVRM(url, f.name);
      else if (/\.vrma$/i.test(f.name)) await addClip(url, f.name, 'vrma');
      else if (/\.fbx$/i.test(f.name)) await addClip(url, f.name, 'fbx');
      else toast(`不支援的檔案：${f.name}`);
    } catch (e) {
      console.error(e);
      toast(`${f.name}：${(e as Error).message}`, 5000);
    } finally {
      URL.revokeObjectURL(url);
    }
  }
}

// ---------- photo → VRM (local Python pipeline via /api) ----------
const genStatus = document.querySelector('#gen-status')!;
const genLog = document.querySelector('#gen-log')!;
const genLinks = document.querySelector('#gen-links')!;
const genImages = document.querySelector('#gen-images')!;
document.querySelector('#gen-pick')!.addEventListener('click', () => fileInput.click());

async function photoToVRM(file: File) {
  document.querySelector<HTMLButtonElement>('[data-tab="gen"]')!.click();
  const gender = document.querySelector<HTMLSelectElement>('#gen-gender')!.value;
  const aiBack = document.querySelector<HTMLInputElement>('#gen-ai-back')!.checked;
  genStatus.textContent = `上傳 ${file.name}…`;
  genLog.textContent = '';
  genLinks.innerHTML = '';
  genImages.innerHTML = '';
  let res: Response;
  try {
    const q = new URLSearchParams({ ...(gender ? { gender } : {}), ...(aiBack ? { ai_backview: '1' } : {}) });
    res = await fetch(`/api/photo2vrm?${q}`, {
      method: 'POST', body: file, headers: { 'X-Filename': file.name },
    });
  } catch {
    genStatus.textContent = '連不上本機 API，請先執行 template/.venv/bin/python template/server.py';
    return;
  }
  if (!res.ok) { genStatus.textContent = `API 錯誤 ${res.status}（server.py 有在跑嗎？）`; return; }
  const { id } = await res.json();
  const t0 = performance.now();
  for (;;) {
    await new Promise((r) => setTimeout(r, 1000));
    const job = await (await fetch(`/api/jobs/${id}`)).json();
    genLog.textContent = job.log.join('\n');
    genStatus.textContent = `${job.status === 'queued' ? '排隊中' : job.status === 'running' ? '處理中' : job.status === 'done' ? '完成' : '失敗'} · ${((performance.now() - t0) / 1000).toFixed(0)}s`;
    for (const k of ['detections', 'body_fit', 'face_fit', 'back', 'texture']) {
      if (job.outputs?.includes(k) && !genImages.querySelector(`[data-k="${k}"]`)) {
        genImages.insertAdjacentHTML('beforeend', `<img data-k="${k}" src="/api/files/${id}/${k}" alt="${k}">`);
      }
    }
    if (job.status === 'done') {
      genLinks.innerHTML = `<a href="/api/files/${id}/vrm0" download="${file.name.replace(/\.[^.]+$/, '')}.vrm0.vrm">下載 VRM 0.x（VSeeFace）</a>`
        + `<a href="/api/files/${id}/vrm1" download="${file.name.replace(/\.[^.]+$/, '')}.vrm1.vrm">下載 VRM 1.0</a>`;
      for (const k of ['detections', 'body_fit', 'face_fit', 'back', 'texture']) {
        if (!genImages.querySelector(`[data-k="${k}"]`)) genImages.insertAdjacentHTML('beforeend', `<img data-k="${k}" src="/api/files/${id}/${k}" alt="" onerror="this.remove()">`);
      }
      await loadVRM(`/api/files/${id}/vrm0`, file.name.replace(/\.[^.]+$/, '') + ' (生成)');
      document.querySelector<HTMLButtonElement>('[data-tab="gen"]')!.click();
      return;
    }
    if (job.status === 'error' || job.status === 'unknown') return;
  }
}

// ---------- drag & drop ----------
let dragDepth = 0;
window.addEventListener('dragenter', (e) => { e.preventDefault(); dragDepth++; document.body.classList.add('dragging'); });
window.addEventListener('dragleave', () => { if (--dragDepth <= 0) { dragDepth = 0; document.body.classList.remove('dragging'); } });
window.addEventListener('dragover', (e) => e.preventDefault());
window.addEventListener('drop', (e) => {
  e.preventDefault();
  dragDepth = 0;
  document.body.classList.remove('dragging');
  if (e.dataTransfer?.files.length) handleFiles(e.dataTransfer.files);
});
const fileInput = document.querySelector<HTMLInputElement>('#file')!;
document.querySelector('#open-btn')!.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => { if (fileInput.files) handleFiles(fileInput.files); fileInput.value = ''; });

// optional local sample (public/samples/, not committed)
fetch('./samples/index.json').then((r) => (r.ok ? r.json() : null)).then((list: string[] | null) => {
  if (!list?.length) return;
  const btn = document.querySelector<HTMLButtonElement>('#sample-btn')!;
  btn.hidden = false;
  btn.onclick = () => loadVRM(`./samples/${list[0]}`, list[0]).catch((e) => toast(e.message));
}).catch(() => {});
const q = new URLSearchParams(location.search).get('model');
if (q) loadVRM(q, q.split('/').pop()!).catch((e) => toast(e.message, 5000));

// ---------- tabs ----------
document.querySelectorAll<HTMLButtonElement>('#tabs button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('#tabs button, section').forEach((x) => x.classList.remove('on'));
  b.classList.add('on');
  document.querySelector(`section[data-pane="${b.dataset.tab}"]`)!.classList.add('on');
}));

// ---------- panels ----------
function renderChecks() {
  if (!vrm) return;
  document.querySelector('#checks')!.innerHTML = runChecks(vrm).map((r) =>
    `<tr><td>${r.label}</td><td><span class="st ${r.status}">${r.status === 'ok' ? '✓' : r.status === 'warn' ? '!' : '✗'}</span> ${r.detail}</td></tr>`).join('');
  document.querySelector('#meta')!.innerHTML = metaSummary(vrm).map(([k, v]) => `<tr><td>${k}</td><td>${escapeHTML(v)}</td></tr>`).join('');
}

const escapeHTML = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!));

function slider(name: string, dot: string, missing: boolean) {
  const row = document.createElement('div');
  row.className = `slider${missing ? ' missing' : ''}`;
  row.innerHTML = `<span class="dot ${dot}"></span><span class="name" title="${name}">${name}</span>
    <input type="range" min="0" max="1" step="0.01" value="${sliderValues[name] ?? 0}" ${missing ? 'disabled' : ''}/><span class="val">${(sliderValues[name] ?? 0).toFixed(2)}</span>`;
  const input = row.querySelector('input')!;
  const val = row.querySelector<HTMLSpanElement>('.val')!;
  input.addEventListener('input', () => { sliderValues[name] = +input.value; val.textContent = (+input.value).toFixed(2); });
  return row;
}

function renderExprSliders() {
  const box = document.querySelector('#expr-sliders')!;
  box.innerHTML = '';
  if (!vrm?.expressionManager) return;
  const arkitLower = new Set(ARKIT_52.map((n) => n.toLowerCase()));
  const names = vrm.expressionManager.expressions.map((e) => e.expressionName).filter((n) => !arkitLower.has(n.toLowerCase()));
  if (!names.length) box.innerHTML = '<p class="note">此模型沒有表情</p>';
  for (const n of names) box.append(slider(n, 'ok', false));
}

let arkitRows: ArkitRow[] = [];
function renderSyncSliders() {
  const box = document.querySelector('#sync-sliders')!;
  box.innerHTML = '';
  if (!vrm) return;
  arkitRows = arkitReport(vrm);
  for (const r of arkitRows) {
    const dot = r.pascalClip && r.meshMorph ? 'half' : r.pascalClip ? 'ok' : r.meshMorph ? 'ok2' : r.expression ? 'ok' : 'miss';
    box.append(slider(r.name, dot, !r.expression && !r.meshMorph));
  }
}

document.querySelectorAll('.bar .zero').forEach((b) => b.addEventListener('click', () => {
  for (const k of Object.keys(sliderValues)) sliderValues[k] = 0;
  renderExprSliders();
  renderSyncSliders();
}));

const SLOT_LABEL: Record<LocoState, string> = { idle: '待機', walk: '走', run: '跑', jump: '跳' };
function renderClips() {
  const slotBox = document.querySelector('#slots')!;
  slotBox.innerHTML = '';
  for (const s of Object.keys(SLOT_LABEL) as LocoState[]) {
    const row = document.createElement('div');
    row.className = 'slot';
    row.innerHTML = `<span>${SLOT_LABEL[s]}</span><select><option value="">內建（程序式）</option>${clips.map((c) =>
      `<option value="${c.id}" ${slots[s] === c.id ? 'selected' : ''}>${escapeHTML(c.name)}</option>`).join('')}</select>`;
    const sel = row.querySelector('select')!;
    sel.addEventListener('change', () => { slots[s] = sel.value ? +sel.value : null; activeKey = ''; });
    slotBox.append(row);
  }
  const box = document.querySelector('#clips')!;
  if (!clips.length) return;
  box.innerHTML = '';
  for (const c of clips) {
    const row = document.createElement('div');
    row.className = `clip${previewClip === c.id ? ' playing' : ''}`;
    row.innerHTML = `<span class="n" title="${escapeHTML(c.name)}">${escapeHTML(c.name)}</span><button>${previewClip === c.id ? '■ 停止' : '▶ 播放'}</button>`;
    row.querySelector('button')!.addEventListener('click', () => {
      previewClip = previewClip === c.id ? null : c.id;
      activeKey = '';
      renderClips();
    });
    box.append(row);
  }
}

document.querySelector('#reset-pos')!.addEventListener('click', () => {
  const d = loco.root.position.clone();
  loco.root.position.set(0, 0, 0);
  controls.target.sub(d);
  camera.position.sub(d);
});
document.querySelector('#shot')!.addEventListener('click', () => {
  const a = document.createElement('a');
  a.href = canvas.toDataURL('image/png');
  a.download = `vrm-${Date.now()}.png`;
  a.click();
});
const lookAtCam = document.querySelector<HTMLInputElement>('#lookat-mouse')!;
const springOn = document.querySelector<HTMLInputElement>('#spring')!;

// ---------- webcam ----------
const camBtn = document.querySelector<HTMLButtonElement>('#cam-toggle')!;
const camHead = document.querySelector<HTMLInputElement>('#cam-head')!;
document.querySelector<HTMLInputElement>('#cam-mirror')!.addEventListener('change', (e) => { face.mirror = (e.target as HTMLInputElement).checked; });
camBtn.addEventListener('click', async () => {
  if (face.running) {
    face.stop();
    camBtn.textContent = '開啟 Webcam';
    document.querySelector('#cam-preview')!.innerHTML = '';
    return;
  }
  camBtn.disabled = true;
  camBtn.textContent = '載入 MediaPipe…';
  try {
    await face.start();
    document.querySelector('#cam-preview')!.append(face.videoElement);
    camBtn.textContent = '關閉 Webcam';
  } catch (e) {
    toast(`Webcam 失敗：${(e as Error).message}`, 5000);
    camBtn.textContent = '開啟 Webcam';
  } finally {
    camBtn.disabled = false;
  }
});

// ---------- per-frame ----------
function playSlot(key: string, clipId: number | null) {
  if (!mixer || key === activeKey) return;
  activeKey = key;
  const clip = clipId != null ? clipFor(clipId) : null;
  const next = clip ? mixer.clipAction(clip) : null;
  if (next) {
    next.reset().setLoop(key === 'jump' ? THREE.LoopOnce : THREE.LoopRepeat, Infinity);
    next.clampWhenFinished = true;
    next.play();
    if (activeAction && activeAction !== next) next.crossFadeFrom(activeAction, 0.2, false);
  } else if (activeAction) {
    activeAction.fadeOut(0.15);
  }
  activeAction = next;
}

let camValuesFrame = 0;
let drivenLastFrame = new Set<string>();
function applyExpressions() {
  if (!vrm) return;
  const em = vrm.expressionManager;
  const values: Record<string, number> = { ...sliderValues };
  const tracking = face.running && Object.keys(face.values).length > 0;
  if (tracking) {
    const hasSync = arkitRows.some((r) => r.expression || r.meshMorph);
    Object.assign(values, hasSync ? face.values : arkitToPresets(face.values));
    if (hasSync) Object.assign(values, arkitToPresets({})); // don't double-drive presets
  }
  if (em) {
    // Only override expressions that a slider or the webcam drives, so VRMA expression tracks still play.
    const drivenNow = new Set<string>();
    for (const e of em.expressions) {
      const n = e.expressionName;
      const row = arkitRows.find((r) => r.expression === n);
      const v = row ? values[row.name] : values[n];
      if (v != null) { em.setValue(n, v); drivenNow.add(n); }
      else if (drivenLastFrame.has(n)) em.setValue(n, 0);
    }
    drivenLastFrame = drivenNow;
  }
  // Perfect Sync shapes that exist only as mesh morph targets (no VRM expression bound).
  for (const r of arkitRows) {
    if (r.expression || !r.meshMorph) continue;
    const v = values[r.name] ?? 0;
    vrm.scene.traverse((o) => {
      const m = o as THREE.Mesh;
      const i = m.morphTargetDictionary?.[r.name];
      if (i != null && m.morphTargetInfluences) m.morphTargetInfluences[i] = v;
    });
  }
  if (tracking && ++camValuesFrame % 10 === 0) {
    document.querySelector('#cam-values')!.innerHTML =
      ARKIT_52.map((n) => `${n} ${(face.values[n] ?? 0).toFixed(2)}`).join('<br>');
  }
}

const clock = new THREE.Clock();
const stateEl = document.querySelector('#state')!;
function tick() {
  requestAnimationFrame(tick);
  frame(Math.min(clock.getDelta(), 1 / 20));
}
function frame(dt: number) {
  const moved = loco.update(dt);
  camera.position.add(moved.clone().setY(0));
  controls.target.add(moved.clone().setY(0));
  controls.update();
  shadow.position.set(loco.root.position.x, 0.002, loco.root.position.z);

  if (vrm && mixer) {
    const st = loco.state;
    const slotClip = slots[st];
    const usePreview = st === 'idle' && previewClip != null;
    const clipId = usePreview ? previewClip : slotClip;
    playSlot(usePreview ? `preview:${previewClip}` : `${st}:${slotClip ?? 'proc'}`, clipId);
    stateEl.textContent = usePreview ? '播放中' : SLOT_LABEL[st];

    // Procedural pose is the base layer; clips override only the bones they animate.
    vrm.humanoid.resetNormalizedPose();
    loco.applyPose(vrm);
    mixer.update(dt);

    face.update();
    if (face.running && camHead.checked) {
      const neck = vrm.humanoid.getNormalizedBoneNode('neck');
      const head = vrm.humanoid.getNormalizedBoneNode('head');
      const half = new THREE.Quaternion().slerp(face.headRotation, 0.5);
      neck?.quaternion.multiply(half);
      head?.quaternion.multiply(half);
    }

    if (vrm.lookAt) {
      vrm.lookAt.autoUpdate = lookAtCam.checked;
      if (!lookAtCam.checked) { vrm.lookAt.yaw = 0; vrm.lookAt.pitch = 0; }
    }
    applyExpressions();
    if (springOn.checked) vrm.update(dt);
    else { vrm.humanoid.update(); vrm.lookAt?.update(dt); vrm.expressionManager?.update(); }
  }
  renderer.render(scene, camera);
}
resize();
tick();

// Expose for automated testing.
Object.assign(window, { __bench: { get vrm() { return vrm; }, get mixer() { return mixer; }, get action() { return activeAction; }, clips, loco, face, sliderValues, handleFiles, frame } });
