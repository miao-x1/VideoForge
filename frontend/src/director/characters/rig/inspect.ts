import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import type { SkeletonType } from '../types';

export interface RigInspection {
  hasMesh: boolean;
  meshCount: number;
  hasSkinnedMesh: boolean;
  hasSkeleton: boolean;
  boneCount: number;
  boneNames: string[];
  skeletonType: SkeletonType;
  embeddedClipNames: string[];
  canPlayClips: boolean;
  message: string;
}

function classifySkeleton(boneNames: string[]): SkeletonType {
  const joined = boneNames.join(' ').toLowerCase();
  if (!boneNames.length) return 'none';
  if (joined.includes('mixamorig')) return 'mixamo';
  if (joined.includes('wolf3d') || joined.includes('armature')) {
    if (joined.includes('hips') && joined.includes('head')) return 'rpm-masculine';
  }
  if (joined.includes('hips') && (joined.includes('leftarm') || joined.includes('left_arm') || joined.includes('lefthand'))) {
    return 'rpm-masculine';
  }
  if (joined.includes('tail') && (joined.includes('leg') || joined.includes('spine'))) return 'quadruped';
  if (joined.includes('wing') || joined.includes('wingl')) return 'avian';
  return 'unknown';
}

export async function inspectGltf(url: string): Promise<RigInspection> {
  const loader = new GLTFLoader();
  const gltf = await loader.loadAsync(url);
  const boneNames: string[] = [];
  let meshCount = 0;
  let hasSkinnedMesh = false;
  gltf.scene.traverse((child) => {
    if (child instanceof THREE.Mesh) meshCount += 1;
    if (child instanceof THREE.SkinnedMesh) hasSkinnedMesh = true;
    if (child instanceof THREE.Bone) boneNames.push(child.name);
  });
  const uniqueBones = [...new Set(boneNames)];
  const skeletonType = classifySkeleton(uniqueBones);
  const clips = (gltf.animations ?? []).map((c) => c.name);
  const hasSkeleton = uniqueBones.length > 0 && hasSkinnedMesh;
  const canPlayClips = clips.length > 0 || skeletonType === 'rpm-masculine' || skeletonType === 'rpm-feminine' || skeletonType === 'mixamo';

  let message = '';
  if (!meshCount) message = '文件里没有可用网格。';
  else if (!hasSkeleton) message = '该模型没有骨骼，无法自动绑定。请上传带 Skeleton 的 GLB，或使用官方基础角色。';
  else if (clips.length) message = `已检测到骨骼（${uniqueBones.length}）和 ${clips.length} 段内嵌动作。`;
  else if (canPlayClips) message = `已检测到兼容人形骨骼（${skeletonType}），可套用系统动作库。`;
  else message = `已检测到骨骼（${uniqueBones.length}），可调姿势，但没有可播放的动作片段。`;

  return {
    hasMesh: meshCount > 0,
    meshCount,
    hasSkinnedMesh,
    hasSkeleton,
    boneCount: uniqueBones.length,
    boneNames: uniqueBones,
    skeletonType,
    embeddedClipNames: clips,
    canPlayClips,
    message,
  };
}
