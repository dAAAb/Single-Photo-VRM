// Apple ARKit 52 face blendshape names (lowerCamel, as ARKit / MediaPipe / Warudo use them).
export const ARKIT_52 = [
  'browDownLeft', 'browDownRight', 'browInnerUp', 'browOuterUpLeft', 'browOuterUpRight',
  'cheekPuff', 'cheekSquintLeft', 'cheekSquintRight',
  'eyeBlinkLeft', 'eyeBlinkRight', 'eyeLookDownLeft', 'eyeLookDownRight',
  'eyeLookInLeft', 'eyeLookInRight', 'eyeLookOutLeft', 'eyeLookOutRight',
  'eyeLookUpLeft', 'eyeLookUpRight', 'eyeSquintLeft', 'eyeSquintRight',
  'eyeWideLeft', 'eyeWideRight',
  'jawForward', 'jawLeft', 'jawOpen', 'jawRight',
  'mouthClose', 'mouthDimpleLeft', 'mouthDimpleRight', 'mouthFrownLeft', 'mouthFrownRight',
  'mouthFunnel', 'mouthLeft', 'mouthLowerDownLeft', 'mouthLowerDownRight',
  'mouthPressLeft', 'mouthPressRight', 'mouthPucker', 'mouthRight',
  'mouthRollLower', 'mouthRollUpper', 'mouthShrugLower', 'mouthShrugUpper',
  'mouthSmileLeft', 'mouthSmileRight', 'mouthStretchLeft', 'mouthStretchRight',
  'mouthUpperUpLeft', 'mouthUpperUpRight',
  'noseSneerLeft', 'noseSneerRight',
  'tongueOut',
] as const;

export type ArkitName = (typeof ARKIT_52)[number];

export const pascal = (s: string) => s[0].toUpperCase() + s.slice(1);

export const VRM_PRESETS = [
  'aa', 'ih', 'ou', 'ee', 'oh',
  'blink', 'blinkLeft', 'blinkRight',
  'happy', 'angry', 'sad', 'relaxed', 'surprised', 'neutral',
  'lookUp', 'lookDown', 'lookLeft', 'lookRight',
] as const;

/** Fallback when a model has no Perfect Sync: approximate VRM presets from ARKit values. */
export function arkitToPresets(v: Record<string, number>): Record<string, number> {
  const g = (k: string) => v[k] ?? 0;
  const smile = (g('mouthSmileLeft') + g('mouthSmileRight')) / 2;
  return {
    blinkLeft: g('eyeBlinkLeft'),
    blinkRight: g('eyeBlinkRight'),
    aa: Math.min(1, g('jawOpen') * 1.4),
    ou: g('mouthPucker'),
    oh: g('mouthFunnel'),
    ih: Math.max(0, (g('mouthStretchLeft') + g('mouthStretchRight')) / 2 - g('jawOpen') * 0.3),
    happy: smile,
    angry: (g('browDownLeft') + g('browDownRight')) / 2,
    surprised: Math.max(0, g('browInnerUp') - 0.2),
    sad: (g('mouthFrownLeft') + g('mouthFrownRight')) / 2,
  };
}
