// Webcam → MediaPipe Face Landmarker → 52 ARKit blendshape values + head rotation.
import * as THREE from 'three';
import { FaceLandmarker, FilesetResolver } from '@mediapipe/tasks-vision';

const WASM = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm';
const MODEL = 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task';

export class FaceTracker {
  values: Record<string, number> = {};
  headRotation = new THREE.Quaternion();
  running = false;
  /** swap Left/Right so the avatar mirrors the user like a mirror */
  mirror = true;
  private landmarker?: FaceLandmarker;
  private video = document.createElement('video');
  private stream?: MediaStream;
  private lastTime = -1;

  constructor() {
    this.video.playsInline = true;
    this.video.muted = true;
  }

  get videoElement() { return this.video; }

  async start() {
    if (!this.landmarker) {
      const fileset = await FilesetResolver.forVisionTasks(WASM);
      this.landmarker = await FaceLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: MODEL, delegate: 'GPU' },
        runningMode: 'VIDEO',
        numFaces: 1,
        outputFaceBlendshapes: true,
        outputFacialTransformationMatrixes: true,
      });
    }
    this.stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: 'user' } });
    this.video.srcObject = this.stream;
    await this.video.play();
    this.running = true;
  }

  stop() {
    this.running = false;
    this.stream?.getTracks().forEach((t) => t.stop());
    this.values = {};
    this.headRotation.identity();
  }

  update() {
    if (!this.running || !this.landmarker || this.video.readyState < 2) return;
    if (this.video.currentTime === this.lastTime) return;
    this.lastTime = this.video.currentTime;
    const res = this.landmarker.detectForVideo(this.video, performance.now());
    const shapes = res.faceBlendshapes?.[0]?.categories;
    if (!shapes) return;
    const out: Record<string, number> = {};
    for (const c of shapes) {
      if (c.categoryName === '_neutral') continue;
      let name = c.categoryName;
      if (this.mirror) name = name.replace(/Left$/, '__R').replace(/Right$/, 'Left').replace(/__R$/, 'Right');
      out[name] = c.score;
    }
    // MediaPipe's jawLeft/Right and mouthLeft/Right describe screen-space direction; mirror them too.
    this.values = out;

    const m = res.facialTransformationMatrixes?.[0]?.data;
    if (m) {
      const mat = new THREE.Matrix4().fromArray(m);
      const q = new THREE.Quaternion().setFromRotationMatrix(mat);
      const e = new THREE.Euler().setFromQuaternion(q, 'YXZ');
      // Camera faces the user; avatar faces the camera → mirror yaw/roll when mirroring.
      const yaw = this.mirror ? -e.y : e.y;
      const roll = this.mirror ? -e.z : e.z;
      this.headRotation.setFromEuler(new THREE.Euler(e.x, yaw, roll, 'YXZ'));
    }
  }
}
