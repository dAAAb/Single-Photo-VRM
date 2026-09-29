// Third-person controller + procedural locomotion (no animation files needed).
// Drives VRM normalized humanoid bones; any slot can be overridden with a loaded clip.
import * as THREE from 'three';
import type { VRM } from '@pixiv/three-vrm';

export type LocoState = 'idle' | 'walk' | 'run' | 'jump';

const WALK_SPEED = 1.6;
const RUN_SPEED = 4.5;
const JUMP_VELOCITY = 4.2;
const GRAVITY = 12;

export class Locomotion {
  readonly root = new THREE.Group();
  state: LocoState = 'idle';
  private keys = new Set<string>();
  private velY = 0;
  private phase = 0;
  private time = 0;
  private yaw = 0;
  private blend = 0; // 0 = idle, 1 = full stride; smooths start/stop

  constructor(private camera: THREE.Camera) {
    window.addEventListener('keydown', (e) => this.onKey(e, true));
    window.addEventListener('keyup', (e) => this.onKey(e, false));
    window.addEventListener('blur', () => this.keys.clear());
  }

  private onKey(e: KeyboardEvent, down: boolean) {
    const t = e.target as HTMLElement | null;
    if (t && (t.tagName === 'INPUT' && (t as HTMLInputElement).type === 'text')) return;
    const k = e.code;
    if (!['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ShiftLeft', 'ShiftRight', 'Space', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(k)) return;
    if (t && t.tagName !== 'BODY' && t.tagName !== 'CANVAS') (t as HTMLElement).blur();
    e.preventDefault();
    if (down) {
      if (k === 'Space' && !this.keys.has('Space') && this.onGround()) this.velY = JUMP_VELOCITY;
      this.keys.add(k);
    } else this.keys.delete(k);
  }

  private onGround() { return this.root.position.y <= 1e-4; }

  /** Moves the root; returns the world-space displacement (for the camera to follow). */
  update(dt: number): THREE.Vector3 {
    this.time += dt;
    const k = this.keys;
    const f = (k.has('KeyW') || k.has('ArrowUp') ? 1 : 0) - (k.has('KeyS') || k.has('ArrowDown') ? 1 : 0);
    const r = (k.has('KeyD') || k.has('ArrowRight') ? 1 : 0) - (k.has('KeyA') || k.has('ArrowLeft') ? 1 : 0);
    const running = k.has('ShiftLeft') || k.has('ShiftRight');

    const fwd = new THREE.Vector3();
    this.camera.getWorldDirection(fwd);
    fwd.y = 0;
    fwd.normalize();
    const right = new THREE.Vector3().crossVectors(fwd, new THREE.Vector3(0, 1, 0));
    const dir = fwd.multiplyScalar(f).add(right.multiplyScalar(r));
    const moving = dir.lengthSq() > 0;

    const before = this.root.position.clone();
    if (moving) {
      dir.normalize();
      const speed = running ? RUN_SPEED : WALK_SPEED;
      this.root.position.addScaledVector(dir, speed * dt);
      const target = Math.atan2(dir.x, dir.z);
      let d = target - this.yaw;
      d = Math.atan2(Math.sin(d), Math.cos(d));
      this.yaw += d * Math.min(1, dt * 12);
      this.root.rotation.y = this.yaw;
    }

    this.velY -= GRAVITY * dt;
    this.root.position.y = Math.max(0, this.root.position.y + this.velY * dt);
    if (this.onGround()) this.velY = 0;

    this.state = !this.onGround() ? 'jump' : moving ? (running ? 'run' : 'walk') : 'idle';
    this.blend = THREE.MathUtils.damp(this.blend, moving ? 1 : 0, 10, dt);
    if (moving) this.phase += dt * Math.PI * 2 * (running ? 1.45 : 0.95);
    return this.root.position.clone().sub(before);
  }

  /** Procedural pose for the current state. Call after humanoid.resetNormalizedPose(). */
  applyPose(vrm: VRM) {
    const h = vrm.humanoid;
    const b = (n: Parameters<typeof h.getNormalizedBoneNode>[0]) => h.getNormalizedBoneNode(n);
    const run = this.state === 'run';
    const s = Math.sin(this.phase);
    const c = Math.cos(this.phase);
    const amp = (run ? 0.85 : 0.45) * this.blend;
    const breathe = Math.sin(this.time * 2) * 0.02;
    // VRM0 normalized space faces -Z (three-vrm rotates the scene 180°), which mirrors X and Z rotations.
    const m = vrm.meta?.metaVersion === '0' ? -1 : 1;

    // Arms down from T-pose (+X is the model's left when facing +Z).
    const armDown = 1.2;
    const lua = b('leftUpperArm'); const rua = b('rightUpperArm');
    const lla = b('leftLowerArm'); const rla = b('rightLowerArm');
    if (lua) { lua.rotation.z = -armDown + breathe; lua.rotation.x = s * amp * 0.8; }
    if (rua) { rua.rotation.z = armDown - breathe; rua.rotation.x = -s * amp * 0.8; }
    const elbow = run ? 1.3 * this.blend + 0.15 : 0.15 + 0.2 * this.blend;
    if (lla) lla.rotation.y = -elbow;
    if (rla) rla.rotation.y = elbow;

    // Legs: negative X swings the foot forward.
    const lul = b('leftUpperLeg'); const rul = b('rightUpperLeg');
    const lll = b('leftLowerLeg'); const rll = b('rightLowerLeg');
    if (lul) lul.rotation.x = -s * amp;
    if (rul) rul.rotation.x = s * amp;
    const knee = (run ? 1.3 : 0.7) * this.blend;
    if (lll) lll.rotation.x = Math.max(0, -c) * knee + 0.05 * this.blend;
    if (rll) rll.rotation.x = Math.max(0, c) * knee + 0.05 * this.blend;

    const spine = b('spine');
    if (spine) { spine.rotation.x = (run ? 0.18 : 0.04) * this.blend + breathe; spine.rotation.y = s * 0.12 * this.blend; }
    const hips = b('hips');
    if (hips) hips.position.y += Math.abs(c) * (run ? 0.05 : 0.025) * this.blend - (run ? 0.03 : 0.01) * this.blend;

    if (this.state === 'jump') {
      const up = this.velY > 0;
      if (lul) lul.rotation.x = up ? -0.9 : -0.4;
      if (rul) rul.rotation.x = up ? -0.2 : -0.5;
      if (lll) lll.rotation.x = up ? 1.4 : 0.6;
      if (rll) rll.rotation.x = up ? 0.4 : 0.7;
      if (lua) { lua.rotation.z = -0.5; lua.rotation.x = -0.3; }
      if (rua) { rua.rotation.z = 0.5; rua.rotation.x = -0.3; }
    }
    if (m < 0) {
      for (const n of [lua, rua, lla, rla, lul, rul, lll, rll, spine]) {
        if (n) { n.rotation.x *= -1; n.rotation.z *= -1; }
      }
    }
  }
}
