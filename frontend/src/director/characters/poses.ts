import type { BonePoseMap, PoseId, SkeletonType } from './types';

export interface PosePreset {
  id: PoseId;
  label: string;
  playing: boolean;
  clipId: string | null;
  implemented: boolean;
  kind: 'clip' | 'bones';
  bones?: BonePoseMap;
  humanOnly?: boolean;
}

const SIT: BonePoseMap = {
  spine: [0.18, 0, 0],
  hips: [0.08, 0, 0],
  leftUpLeg: [1.4, 0.05, 0.08],
  rightUpLeg: [1.4, -0.05, -0.08],
  leftLeg: [-1.5, 0, 0],
  rightLeg: [-1.5, 0, 0],
  leftArm: [0.2, 0, 0.25],
  rightArm: [0.2, 0, -0.25],
};

const LIE: BonePoseMap = {
  hips: [1.45, 0, 0],
  spine: [0.1, 0, 0],
  leftUpLeg: [0.15, 0.08, 0],
  rightUpLeg: [0.15, -0.08, 0],
  leftArm: [-0.4, 0, 0.5],
  rightArm: [-0.4, 0, -0.5],
};

const LOOK_LEFT: BonePoseMap = {
  head: [0, 0.72, 0],
  neck: [0, 0.22, 0],
};

const LOOK_RIGHT: BonePoseMap = {
  head: [0, -0.72, 0],
  neck: [0, -0.22, 0],
};

const NOD: BonePoseMap = {
  head: [0.45, 0, 0],
  neck: [0.12, 0, 0],
};

const WAVE: BonePoseMap = {
  rightShoulder: [0, 0, -0.25],
  rightArm: [-2.35, 0.15, -0.2],
  rightForeArm: [0, 0, -0.55],
  rightHand: [0, 0, -0.2],
};

export const POSE_PRESETS: PosePreset[] = [
  { id: 'stand', label: '站立', playing: true, clipId: 'idle', implemented: true, kind: 'clip' },
  { id: 'walk', label: '行走', playing: true, clipId: 'walk', implemented: true, kind: 'clip' },
  { id: 'run', label: '跑步', playing: true, clipId: 'run', implemented: true, kind: 'clip' },
  { id: 'sit', label: '坐下', playing: false, clipId: null, implemented: true, kind: 'bones', bones: SIT, humanOnly: true },
  { id: 'lie', label: '躺下', playing: false, clipId: null, implemented: true, kind: 'bones', bones: LIE, humanOnly: true },
  { id: 'look_left', label: '看左', playing: false, clipId: null, implemented: true, kind: 'bones', bones: LOOK_LEFT, humanOnly: true },
  { id: 'look_right', label: '看右', playing: false, clipId: null, implemented: true, kind: 'bones', bones: LOOK_RIGHT, humanOnly: true },
  { id: 'nod', label: '点头', playing: false, clipId: null, implemented: true, kind: 'bones', bones: NOD, humanOnly: true },
  { id: 'wave', label: '挥手', playing: false, clipId: null, implemented: true, kind: 'bones', bones: WAVE, humanOnly: true },
  { id: 'custom', label: '自定义姿势', playing: false, clipId: null, implemented: true, kind: 'bones' },
];

export function posesForCharacter(kind: 'human' | 'animal' | 'special', skeleton: SkeletonType): PosePreset[] {
  return POSE_PRESETS.filter((pose) => {
    if (pose.humanOnly && kind === 'animal') return false;
    if (pose.kind === 'bones' && (skeleton === 'none' || skeleton === 'avian')) return pose.id === 'stand';
    return true;
  });
}

export function getPosePreset(id: string | null | undefined): PosePreset | undefined {
  return POSE_PRESETS.find((p) => p.id === id);
}
