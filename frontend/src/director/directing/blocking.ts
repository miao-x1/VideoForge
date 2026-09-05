import type { Vec3 } from '../types';
import { lookAtRotation } from '../types';

export type BlockingPreset = 'dialogue' | 'conflict' | 'walkby' | 'embrace';

export interface BlockingPose {
  position: Vec3;
  rotation: Vec3;
}

export function computeBlocking(preset: BlockingPreset, count: number): BlockingPose[] {
  const n = Math.max(1, count);
  if (preset === 'dialogue') {
    if (n === 1) return [{ position: [0, 0, 0], rotation: [0, 0, 0] }];
    const a: Vec3 = [-0.85, 0, 0];
    const b: Vec3 = [0.85, 0, 0];
    const poses: BlockingPose[] = [
      { position: a, rotation: lookAtRotation(a, b) },
      { position: b, rotation: lookAtRotation(b, a) },
    ];
    for (let i = 2; i < n; i += 1) {
      poses.push({ position: [(i - 1) * 1.1 - 1.1, 0, 1.2], rotation: [0, Math.PI, 0] });
    }
    return poses;
  }
  if (preset === 'conflict') {
    const a: Vec3 = [-1.65, 0, 0.25];
    const b: Vec3 = [1.65, 0, -0.25];
    const poses: BlockingPose[] = [
      { position: a, rotation: lookAtRotation(a, b) },
      { position: b, rotation: lookAtRotation(b, a) },
    ];
    for (let i = 2; i < n; i += 1) {
      poses.push({ position: [0, 0, -1.4], rotation: [0, 0, 0] });
    }
    return poses.slice(0, n);
  }
  if (preset === 'embrace') {
    const a: Vec3 = [-0.32, 0, 0];
    const b: Vec3 = [0.32, 0, 0];
    return [
      { position: a, rotation: lookAtRotation(a, b) },
      { position: b, rotation: lookAtRotation(b, a) },
    ].slice(0, n);
  }
  return Array.from({ length: n }, (_, i) => ({
    position: [i * 1.4 - ((n - 1) * 1.4) / 2, 0, 0] as Vec3,
    rotation: [0, 0, 0] as Vec3,
  }));
}

export const BLOCKING_LABEL: Record<BlockingPreset, string> = {
  dialogue: '对话场景',
  conflict: '冲突场景',
  walkby: '路过',
  embrace: '靠近',
};
