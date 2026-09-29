// Retarget a Mixamo FBX animation onto a VRM's normalized humanoid bones.
// Adapted from the three-vrm "humanoidAnimation" example (MIT).
import * as THREE from 'three';
import { FBXLoader } from 'three/examples/jsm/loaders/FBXLoader.js';
import type { VRM, VRMHumanBoneName } from '@pixiv/three-vrm';

const SIDES = ['Left', 'Right'] as const;
const FINGERS: [string, string][] = [['Thumb', 'Thumb'], ['Index', 'Index'], ['Middle', 'Middle'], ['Ring', 'Ring'], ['Pinky', 'Little']];

export const MIXAMO_VRM_MAP: Record<string, VRMHumanBoneName> = (() => {
  const m: Record<string, string> = {
    mixamorigHips: 'hips', mixamorigSpine: 'spine', mixamorigSpine1: 'chest', mixamorigSpine2: 'upperChest',
    mixamorigNeck: 'neck', mixamorigHead: 'head',
  };
  for (const s of SIDES) {
    const l = s.toLowerCase();
    Object.assign(m, {
      [`mixamorig${s}Shoulder`]: `${l}Shoulder`, [`mixamorig${s}Arm`]: `${l}UpperArm`,
      [`mixamorig${s}ForeArm`]: `${l}LowerArm`, [`mixamorig${s}Hand`]: `${l}Hand`,
      [`mixamorig${s}UpLeg`]: `${l}UpperLeg`, [`mixamorig${s}Leg`]: `${l}LowerLeg`,
      [`mixamorig${s}Foot`]: `${l}Foot`, [`mixamorig${s}ToeBase`]: `${l}Toes`,
    });
    for (const [mx, vr] of FINGERS) {
      const segs = vr === 'Thumb' ? ['Metacarpal', 'Proximal', 'Distal'] : ['Proximal', 'Intermediate', 'Distal'];
      segs.forEach((seg, i) => { m[`mixamorig${s}Hand${mx}${i + 1}`] = `${l}${vr}${seg}`; });
    }
  }
  return m as Record<string, VRMHumanBoneName>;
})();

export async function loadMixamoFBX(url: string): Promise<THREE.Group> {
  return new FBXLoader().loadAsync(url);
}

export function retargetMixamo(asset: THREE.Group, vrm: VRM): THREE.AnimationClip {
  const clip = THREE.AnimationClip.findByName(asset.animations, 'mixamo.com') ?? asset.animations[0];
  if (!clip) throw new Error('FBX 裡沒有動畫');
  const tracks: THREE.KeyframeTrack[] = [];
  const restRotationInverse = new THREE.Quaternion();
  const parentRestWorldRotation = new THREE.Quaternion();
  const q = new THREE.Quaternion();
  const v = new THREE.Vector3();

  const hipsNode = asset.getObjectByName('mixamorigHips');
  const motionHipsHeight = hipsNode ? hipsNode.position.y : 1;
  const vrmHipsY = vrm.humanoid.getNormalizedBoneNode('hips')!.getWorldPosition(v).y;
  const vrmRootY = vrm.scene.getWorldPosition(v).y;
  const hipsScale = Math.abs(vrmHipsY - vrmRootY) / motionHipsHeight;
  const isVRM0 = vrm.meta?.metaVersion === '0';

  for (const track of clip.tracks) {
    const [rigName, prop] = track.name.split('.');
    const boneName = MIXAMO_VRM_MAP[rigName];
    const vrmNode = boneName ? vrm.humanoid.getNormalizedBoneNode(boneName) : null;
    const rigNode = asset.getObjectByName(rigName);
    if (!vrmNode || !rigNode || !rigNode.parent) continue;

    rigNode.getWorldQuaternion(restRotationInverse).invert();
    rigNode.parent.getWorldQuaternion(parentRestWorldRotation);

    if (track instanceof THREE.QuaternionKeyframeTrack) {
      const values = track.values.slice();
      for (let i = 0; i < values.length; i += 4) {
        q.fromArray(values, i).premultiply(parentRestWorldRotation).multiply(restRotationInverse).toArray(values, i);
      }
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${vrmNode.name}.${prop}`, track.times,
        values.map((x, i) => (isVRM0 && i % 2 === 0 ? -x : x)),
      ));
    } else if (track instanceof THREE.VectorKeyframeTrack && boneName === 'hips') {
      tracks.push(new THREE.VectorKeyframeTrack(
        `${vrmNode.name}.${prop}`, track.times,
        Array.from(track.values).map((x, i) => (isVRM0 && i % 3 !== 1 ? -x : x) * hipsScale),
      ));
    }
  }
  return new THREE.AnimationClip(clip.name || 'mixamo', clip.duration, tracks);
}
