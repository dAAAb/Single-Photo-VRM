import * as THREE from 'three';
import type { VRM, VRMHumanBoneName } from '@pixiv/three-vrm';
import { ARKIT_52, VRM_PRESETS, pascal } from './arkit';

export const REQUIRED_BONES: VRMHumanBoneName[] = [
  'hips', 'spine', 'head',
  'leftUpperLeg', 'leftLowerLeg', 'leftFoot', 'rightUpperLeg', 'rightLowerLeg', 'rightFoot',
  'leftUpperArm', 'leftLowerArm', 'leftHand', 'rightUpperArm', 'rightLowerArm', 'rightHand',
];
const OPTIONAL_BONES: VRMHumanBoneName[] = ['chest', 'upperChest', 'neck', 'leftShoulder', 'rightShoulder', 'leftEye', 'rightEye', 'jaw', 'leftToes', 'rightToes'];
const FINGER_BONES = (['left', 'right'] as const).flatMap((s) =>
  ['Thumb', 'Index', 'Middle', 'Ring', 'Little'].flatMap((f) =>
    (f === 'Thumb' ? ['Metacarpal', 'Proximal', 'Distal'] : ['Proximal', 'Intermediate', 'Distal'])
      .map((seg) => `${s}${f}${seg}` as VRMHumanBoneName)));

export type Status = 'ok' | 'warn' | 'fail';
export interface CheckRow { label: string; status: Status; detail: string }

export interface ArkitRow {
  name: string;
  /** expression name in the VRM matching case-insensitively, if any */
  expression: string | null;
  /** exact PascalCase clip (VSeeFace / VMagicMirror, VRM0) */
  pascalClip: boolean;
  /** exact lowerCamel mesh morph target (Warudo) */
  meshMorph: boolean;
}

export function meshMorphNames(vrm: VRM): Set<string> {
  const names = new Set<string>();
  vrm.scene.traverse((o) => {
    const m = o as THREE.Mesh;
    if (m.isMesh && m.morphTargetDictionary) Object.keys(m.morphTargetDictionary).forEach((k) => names.add(k));
  });
  return names;
}

export function arkitReport(vrm: VRM): ArkitRow[] {
  const exprNames = (vrm.expressionManager?.expressions ?? []).map((e) => e.expressionName);
  const lower = new Map(exprNames.map((n) => [n.toLowerCase(), n]));
  const morphs = meshMorphNames(vrm);
  return ARKIT_52.map((name) => ({
    name,
    expression: lower.get(name.toLowerCase()) ?? null,
    pascalClip: exprNames.includes(pascal(name)),
    meshMorph: morphs.has(name),
  }));
}

export function runChecks(vrm: VRM): CheckRow[] {
  const rows: CheckRow[] = [];
  const h = vrm.humanoid;
  const isVRM0 = vrm.meta?.metaVersion === '0';
  rows.push({ label: 'VRM 版本', status: 'ok', detail: isVRM0 ? '0.x（VSeeFace 可用）' : '1.0（VSeeFace 不支援，需另出 0.x）' });

  const missing = REQUIRED_BONES.filter((b) => !h.getRawBoneNode(b));
  rows.push({ label: '必要骨 15 根', status: missing.length ? 'fail' : 'ok', detail: missing.length ? `缺：${missing.join(', ')}` : '齊全' });

  const optMissing = OPTIONAL_BONES.filter((b) => !h.getRawBoneNode(b));
  rows.push({ label: '選配骨', status: optMissing.length ? 'warn' : 'ok', detail: optMissing.length ? `缺：${optMissing.join(', ')}` : '齊全' });

  const fingers = FINGER_BONES.filter((b) => h.getRawBoneNode(b)).length;
  rows.push({ label: '手指骨', status: fingers === 30 ? 'ok' : fingers ? 'warn' : 'fail', detail: `${fingers} / 30` });

  const exprs = new Set((vrm.expressionManager?.expressions ?? []).map((e) => e.expressionName));
  // VRM0 has no 'surprised' preset (three-vrm keeps VRM0 custom clips under their own names).
  const presetMissing = VRM_PRESETS.filter((p) => !exprs.has(p) && !(isVRM0 && p === 'surprised'));
  rows.push({ label: 'VRM 表情 preset', status: presetMissing.length > 4 ? 'fail' : presetMissing.length ? 'warn' : 'ok', detail: presetMissing.length ? `缺：${presetMissing.join(', ')}` : '齊全' });

  const ar = arkitReport(vrm);
  const anyCount = ar.filter((r) => r.expression || r.meshMorph).length;
  const pascalCount = ar.filter((r) => r.pascalClip).length;
  const morphCount = ar.filter((r) => r.meshMorph).length;
  rows.push({ label: 'Perfect Sync（任一形式）', status: anyCount === 52 ? 'ok' : anyCount ? 'warn' : 'fail', detail: `${anyCount} / 52` });
  rows.push({ label: '  VSeeFace / VMM（VRM0 PascalCase clip）', status: isVRM0 && pascalCount === 52 ? 'ok' : pascalCount ? 'warn' : 'fail', detail: `${pascalCount} / 52${isVRM0 ? '' : '（且需 VRM0）'}` });
  rows.push({ label: '  Warudo（lowerCamel mesh morph）', status: morphCount === 52 ? 'ok' : morphCount ? 'warn' : 'fail', detail: `${morphCount} / 52` });

  rows.push({ label: 'lookAt', status: vrm.lookAt ? 'ok' : 'warn', detail: vrm.lookAt ? (vrm.lookAt.applier?.constructor?.name ?? '有') : '無' });
  const joints = vrm.springBoneManager?.joints.size ?? 0;
  rows.push({ label: 'Spring bone joints', status: joints ? 'ok' : 'warn', detail: String(joints) });
  rows.push({ label: 'firstPerson', status: vrm.firstPerson ? 'ok' : 'warn', detail: vrm.firstPerson ? '有' : '無' });
  return rows;
}

export function metaSummary(vrm: VRM): [string, string][] {
  const m = vrm.meta as unknown as Record<string, unknown>;
  if (!m) return [];
  if (m.metaVersion === '0') {
    return [['名稱', String(m.title ?? '')], ['作者', String(m.author ?? '')], ['版本', String(m.version ?? '')],
      ['授權', String(m.licenseName ?? '')], ['商用', String(m.commercialUssageName ?? '')]];
  }
  return [['名稱', String(m.name ?? '')], ['作者', ((m.authors as string[]) ?? []).join(', ')], ['版本', String(m.version ?? '')],
    ['授權 URL', String(m.licenseUrl ?? '')], ['商用', String(m.commercialUsage ?? '')]];
}
