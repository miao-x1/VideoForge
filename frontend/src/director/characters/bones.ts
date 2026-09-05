import * as THREE from 'three';
import type { BonePoseMap, SkeletonType } from './types';

export interface BoneControl {
  id: string;
  label: string;
  aliases: string[];
}

export const HUMANOID_CONTROLS: BoneControl[] = [
  { id: 'head', label: '头', aliases: ['head', 'mixamorighead', 'mixamorig:head'] },
  { id: 'neck', label: '颈', aliases: ['neck', 'mixamorigneck', 'mixamorig:neck'] },
  { id: 'spine', label: '身体', aliases: ['spine', 'spine1', 'mixamorigspine', 'mixamorigspine1', 'mixamorig:spine'] },
  { id: 'hips', label: '髋', aliases: ['hips', 'mixamorighips', 'mixamorig:hips', 'pelvis'] },
  { id: 'leftShoulder', label: '左肩', aliases: ['leftshoulder', 'mixamorigleftshoulder'] },
  { id: 'rightShoulder', label: '右肩', aliases: ['rightshoulder', 'mixamorigrightshoulder'] },
  { id: 'leftArm', label: '左臂', aliases: ['leftarm', 'leftupperarm', 'mixamorigleftarm'] },
  { id: 'rightArm', label: '右臂', aliases: ['rightarm', 'rightupperarm', 'mixamorigrightarm'] },
  { id: 'leftForeArm', label: '左肘', aliases: ['leftforearm', 'leftlowerarm', 'mixamorigleftforearm'] },
  { id: 'rightForeArm', label: '右肘', aliases: ['rightforearm', 'rightlowerarm', 'mixamorigrightforearm'] },
  { id: 'leftHand', label: '左手', aliases: ['lefthand', 'mixamoriglefthand'] },
  { id: 'rightHand', label: '右手', aliases: ['righthand', 'mixamorigrighthand'] },
  { id: 'leftUpLeg', label: '左腿', aliases: ['leftupleg', 'leftupperleg', 'leftthigh', 'mixamorigleftupleg'] },
  { id: 'rightUpLeg', label: '右腿', aliases: ['rightupleg', 'rightupperleg', 'rightthigh', 'mixamorigrightupleg'] },
  { id: 'leftLeg', label: '左膝', aliases: ['leftleg', 'leftlowerleg', 'leftshin', 'mixamorigleftleg'] },
  { id: 'rightLeg', label: '右膝', aliases: ['rightleg', 'rightlowerleg', 'rightshin', 'mixamorigrightleg'] },
  { id: 'leftFoot', label: '左脚', aliases: ['leftfoot', 'mixamorigleftfoot'] },
  { id: 'rightFoot', label: '右脚', aliases: ['rightfoot', 'mixamorigrightfoot'] },
];

export const QUAD_CONTROLS: BoneControl[] = [
  { id: 'head', label: '头', aliases: ['head', 'fox_head', 'neck'] },
  { id: 'spine', label: '躯干', aliases: ['spine', 'body', 'chest', 'torso'] },
  { id: 'tail', label: '尾巴', aliases: ['tail', 'tail1'] },
  { id: 'frontLeft', label: '前左腿', aliases: ['frontleft', 'legfrontleft', 'front_left'] },
  { id: 'frontRight', label: '前右腿', aliases: ['frontright', 'legfrontright', 'front_right'] },
  { id: 'backLeft', label: '后左腿', aliases: ['backleft', 'legbackleft', 'hind_left'] },
  { id: 'backRight', label: '后右腿', aliases: ['backright', 'legbackright', 'hind_right'] },
];

export function controlsForSkeleton(skeleton: SkeletonType): BoneControl[] {
  if (skeleton === 'quadruped' || skeleton === 'avian') return QUAD_CONTROLS;
  if (skeleton === 'none') return [];
  return HUMANOID_CONTROLS;
}

function norm(name: string): string {
  return name.toLowerCase().replace(/[\s_\-:]/g, '');
}

export function listBones(root: THREE.Object3D): THREE.Bone[] {
  const bones: THREE.Bone[] = [];
  root.traverse((child) => {
    if (child instanceof THREE.Bone) bones.push(child);
  });
  return bones;
}

export function findBone(root: THREE.Object3D, aliases: string[]): THREE.Bone | null {
  const wanted = aliases.map(norm);
  let found: THREE.Bone | null = null;
  root.traverse((child) => {
    if (found || !(child instanceof THREE.Bone)) return;
    const n = norm(child.name);
    if (wanted.some((a) => n === a || n.endsWith(a))) found = child;
  });
  return found;
}

export function captureBonePose(root: THREE.Object3D, skeleton: SkeletonType): BonePoseMap {
  const pose: BonePoseMap = {};
  controlsForSkeleton(skeleton).forEach((control) => {
    const bone = findBone(root, control.aliases);
    if (!bone) return;
    pose[control.id] = [bone.rotation.x, bone.rotation.y, bone.rotation.z];
  });
  return pose;
}

function ensureRest(bone: THREE.Bone): void {
  if (!bone.userData.restQuat) {
    bone.userData.restQuat = bone.quaternion.clone();
  }
}

export function applyBonePose(root: THREE.Object3D, skeleton: SkeletonType, pose: BonePoseMap | null): void {
  const controls = controlsForSkeleton(skeleton);
  controls.forEach((control) => {
    const bone = findBone(root, control.aliases);
    if (!bone) return;
    ensureRest(bone);
    const euler = pose?.[control.id];
    if (!euler) {
      bone.quaternion.copy(bone.userData.restQuat as THREE.Quaternion);
      return;
    }
    bone.rotation.set(euler[0], euler[1], euler[2]);
  });
}

export function resetBonePose(root: THREE.Object3D, skeleton: SkeletonType): void {
  applyBonePose(root, skeleton, null);
}

export function lerpBonePose(a: BonePoseMap, b: BonePoseMap, t: number): BonePoseMap {
  const out: BonePoseMap = {};
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  keys.forEach((key) => {
    const av = a[key] ?? [0, 0, 0];
    const bv = b[key] ?? [0, 0, 0];
    out[key] = [
      av[0] + (bv[0] - av[0]) * t,
      av[1] + (bv[1] - av[1]) * t,
      av[2] + (bv[2] - av[2]) * t,
    ];
  });
  return out;
}

/** Analytic two-bone IK. target is in the root's world space. */
export function solveTwoBoneIK(
  root: THREE.Bone,
  mid: THREE.Bone,
  end: THREE.Bone,
  target: THREE.Vector3,
): void {
  const rootPos = new THREE.Vector3();
  const midPos = new THREE.Vector3();
  const endPos = new THREE.Vector3();
  root.getWorldPosition(rootPos);
  mid.getWorldPosition(midPos);
  end.getWorldPosition(endPos);

  const upperLen = rootPos.distanceTo(midPos);
  const lowerLen = midPos.distanceTo(endPos);
  const maxLen = upperLen + lowerLen;
  const toTarget = target.clone().sub(rootPos);
  const dist = Math.min(maxLen * 0.999, Math.max(0.01, toTarget.length()));
  const dir = toTarget.normalize();

  const cosA = THREE.MathUtils.clamp(
    (upperLen * upperLen + dist * dist - lowerLen * lowerLen) / (2 * upperLen * dist),
    -1,
    1,
  );
  const angleA = Math.acos(cosA);
  const cosB = THREE.MathUtils.clamp(
    (upperLen * upperLen + lowerLen * lowerLen - dist * dist) / (2 * upperLen * lowerLen),
    -1,
    1,
  );
  const angleB = Math.acos(cosB);

  const parent = root.parent;
  const localDir = dir.clone();
  if (parent) parent.worldToLocal(localDir.add(rootPos)).sub(root.position).normalize();
  else localDir.copy(dir);

  const axis = new THREE.Vector3(1, 0, 0);
  root.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), localDir);
  root.rotateOnAxis(axis, -angleA);
  mid.rotation.set(Math.PI - angleB, 0, 0);
  void end;
}
