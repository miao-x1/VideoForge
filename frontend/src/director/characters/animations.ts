import type { ClipId, ClipKind, SkeletonType } from './types';

export interface ClipDef {
  id: ClipId;
  label: string;
  url?: string;
  embeddedName?: string;
  implemented: boolean;
  kind: ClipKind;
  poseId?: string;
}

const ANIM = '/director/models/anims';

const HUMAN_CLIP_META: Array<{ id: ClipId; label: string }> = [
  { id: 'idle', label: 'Idle' },
  { id: 'stand', label: 'Stand' },
  { id: 'walk', label: 'Walk' },
  { id: 'run', label: 'Run' },
  { id: 'sit', label: 'Sit' },
  { id: 'stand_up', label: 'Stand Up' },
  { id: 'turn', label: 'Turn' },
  { id: 'look', label: 'Look Around' },
  { id: 'look_left', label: 'Look Left' },
  { id: 'look_right', label: 'Look Right' },
  { id: 'nod', label: 'Nod' },
  { id: 'shake', label: 'Shake Head' },
  { id: 'wave', label: 'Wave' },
  { id: 'point', label: 'Point' },
  { id: 'talk', label: 'Talk' },
  { id: 'phone', label: 'Phone' },
  { id: 'pick_up', label: 'Pick Up' },
  { id: 'put_down', label: 'Put Down' },
  { id: 'hug', label: 'Hug' },
  { id: 'fight', label: 'Fight' },
  { id: 'fall', label: 'Fall' },
];

const BONE_POSE_CLIPS: Partial<Record<ClipId, string>> = {
  sit: 'sit',
  look_left: 'look_left',
  look_right: 'look_right',
  nod: 'nod',
  wave: 'wave',
};

const RPM_URL: Partial<Record<ClipId, string>> = {
  idle: `${ANIM}/M_Idle.glb`,
  stand: `${ANIM}/M_Idle.glb`,
  walk: `${ANIM}/M_Walk.glb`,
  run: `${ANIM}/M_Run.glb`,
  talk: `${ANIM}/M_Talk.glb`,
  look: `${ANIM}/M_Look.glb`,
};

const RPM_F_URL: Partial<Record<ClipId, string>> = {
  idle: `${ANIM}/F_Idle.glb`,
  stand: `${ANIM}/F_Idle.glb`,
  walk: `${ANIM}/F_Walk.glb`,
  run: `${ANIM}/F_Run.glb`,
  talk: `${ANIM}/F_Talk.glb`,
  look: `${ANIM}/M_Look.glb`,
};

function humanClips(urls: Partial<Record<ClipId, string>>): ClipDef[] {
  return HUMAN_CLIP_META.map((meta) => {
    if (urls[meta.id]) {
      return { ...meta, url: urls[meta.id], implemented: true, kind: 'clip' as const };
    }
    if (BONE_POSE_CLIPS[meta.id]) {
      return { ...meta, implemented: true, kind: 'pose' as const, poseId: BONE_POSE_CLIPS[meta.id] };
    }
    return { ...meta, implemented: false, kind: 'unavailable' as const };
  });
}

function mixamoEmbedded(names: Record<string, string>): ClipDef[] {
  return HUMAN_CLIP_META.map((meta) => {
    if (names[meta.id]) {
      return { ...meta, embeddedName: names[meta.id], implemented: true, kind: 'clip' as const };
    }
    if (BONE_POSE_CLIPS[meta.id]) {
      return { ...meta, implemented: true, kind: 'pose' as const, poseId: BONE_POSE_CLIPS[meta.id] };
    }
    return { ...meta, implemented: false, kind: 'unavailable' as const };
  });
}

export function clipsForSet(animationSetId: string, skeletonId: SkeletonType): ClipDef[] {
  if (animationSetId === 'mixamo-soldier') {
    return mixamoEmbedded({ idle: 'Idle', stand: 'Idle', walk: 'Walk', run: 'Run' });
  }
  if (animationSetId === 'mixamo-xbot') {
    return mixamoEmbedded({ idle: 'idle', stand: 'idle', walk: 'walk', run: 'run' });
  }
  if (animationSetId === 'khronos-fox') {
    return [
      { id: 'idle', label: 'Survey', embeddedName: 'Survey', implemented: true, kind: 'clip' },
      { id: 'walk', label: 'Walk', embeddedName: 'Walk', implemented: true, kind: 'clip' },
      { id: 'run', label: 'Run', embeddedName: 'Run', implemented: true, kind: 'clip' },
      { id: 'jump', label: 'Jump', implemented: false, kind: 'unavailable' },
      { id: 'sit', label: 'Sit', implemented: false, kind: 'unavailable' },
    ];
  }
  if (animationSetId === 'three-horse' || animationSetId === 'three-bird' || animationSetId === 'embedded') {
    return [
      { id: 'idle', label: 'Idle', embeddedName: '*', implemented: true, kind: 'clip' },
      { id: 'walk', label: 'Walk', embeddedName: '*', implemented: true, kind: 'clip' },
      { id: 'run', label: 'Run', embeddedName: '*', implemented: true, kind: 'clip' },
    ];
  }
  if (skeletonId === 'rpm-feminine' || animationSetId === 'rpm-feminine') {
    return humanClips(RPM_F_URL);
  }
  if (skeletonId === 'rpm-masculine' || animationSetId === 'rpm-masculine' || skeletonId === 'mixamo') {
    return humanClips(skeletonId === 'mixamo' ? {} : RPM_URL);
  }
  if (skeletonId === 'none') return [];
  return [
    { id: 'idle', label: 'Idle', embeddedName: '*', implemented: true, kind: 'clip' },
  ];
}

export function clipsForCharacter(kind: 'human' | 'animal' | 'special', animationSetId: string, skeletonId: SkeletonType): ClipDef[] {
  const clips = clipsForSet(animationSetId, skeletonId);
  if (kind === 'animal') {
    return clips.filter((c) => ['idle', 'walk', 'run', 'jump', 'sit'].includes(c.id));
  }
  return clips;
}

export function poseForClip(clipId: ClipId | null): PoseIdLike {
  if (clipId === 'walk') return 'walk';
  if (clipId === 'run') return 'run';
  if (clipId === 'sit') return 'sit';
  if (clipId === 'lie') return 'lie';
  if (clipId === 'look_left') return 'look_left';
  if (clipId === 'look_right') return 'look_right';
  if (clipId === 'nod') return 'nod';
  if (clipId === 'wave') return 'wave';
  return 'stand';
}

type PoseIdLike = 'stand' | 'sit' | 'walk' | 'run' | 'lie' | 'look_left' | 'look_right' | 'nod' | 'wave';
