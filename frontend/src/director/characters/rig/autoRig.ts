import type { AnimationStatus, RigStatus, SkeletonType } from '../types';
import { inspectGltf, type RigInspection } from './inspect';

export interface AutoRigResult {
  ok: boolean;
  inspection: RigInspection;
  skeletonType: SkeletonType;
  animationSetId: string;
  rigStatus: RigStatus;
  animationStatus: AnimationStatus;
  error: string | null;
}

function animationSetFor(inspection: RigInspection): string {
  if (inspection.skeletonType === 'mixamo') {
    return inspection.embeddedClipNames.length ? 'embedded' : 'mixamo-soldier';
  }
  if (inspection.skeletonType === 'rpm-feminine') return 'rpm-feminine';
  if (inspection.skeletonType === 'rpm-masculine') return 'rpm-masculine';
  if (inspection.embeddedClipNames.length) return 'embedded';
  return 'none';
}

export async function autoRigFromUrl(url: string): Promise<AutoRigResult> {
  const inspection = await inspectGltf(url);
  if (!inspection.hasMesh) {
    return {
      ok: false,
      inspection,
      skeletonType: 'none',
      animationSetId: 'none',
      rigStatus: 'failed',
      animationStatus: 'failed',
      error: inspection.message,
    };
  }
  if (!inspection.hasSkeleton) {
    return {
      ok: false,
      inspection,
      skeletonType: 'none',
      animationSetId: 'none',
      rigStatus: 'failed',
      animationStatus: 'none',
      error: '该模型无法自动绑定，请调整模型或上传兼容模型（需要已蒙皮的人形/动物骨骼）。系统不会假装绑定成功。',
    };
  }

  const animationSetId = animationSetFor(inspection);
  const animationStatus: AnimationStatus = inspection.canPlayClips
    ? inspection.embeddedClipNames.length || animationSetId.startsWith('rpm') || animationSetId.startsWith('mixamo')
      ? 'ready'
      : 'partial'
    : 'partial';

  return {
    ok: true,
    inspection,
    skeletonType: inspection.skeletonType,
    animationSetId,
    rigStatus: 'ready',
    animationStatus,
    error: null,
  };
}
