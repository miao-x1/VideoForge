import { useEffect, useLayoutEffect, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { useAnimations, useGLTF } from '@react-three/drei';
import * as SkeletonUtils from 'three/examples/jsm/utils/SkeletonUtils.js';
import type { AnimationClip, Group, Object3D } from 'three';
import type { SceneObject } from '../types';
import type { CharacterAsset, ClipId } from '../characters/types';
import { applyCharacterAppearance } from '../characters/appearance';
import { clipsForSet } from '../characters/animations';
import { applyBonePose, lerpBonePose } from '../characters/bones';
import { getPosePreset } from '../characters/poses';
import { useDirectorStore } from '../store/useDirectorStore';
import { useCharacterLibrary } from '../characters/useCharacterLibrary';

function renameClip(clip: AnimationClip | undefined, name: string): AnimationClip | null {
  if (!clip) return null;
  const next = clip.clone();
  next.name = name;
  return next;
}

function useAppearance(root: Object3D, asset: CharacterAsset) {
  const key = `${asset.id}:${asset.modelUrl}:${asset.heightCm}:${asset.bodyType}:${JSON.stringify(asset.appearance)}`;
  useLayoutEffect(() => {
    applyCharacterAppearance(root, asset);
  }, [root, key, asset]);
}

function usePlay(
  object: SceneObject,
  actions: Record<string, { reset: () => { fadeIn: (n: number) => { play: () => void } }; fadeOut: (n: number) => void; paused: boolean; stop: () => void } | null>,
  names: string[],
  clipMode: boolean,
) {
  const setAnimationNames = useDirectorStore((s) => s.setAnimationNames);
  useEffect(() => {
    if (names.length) setAnimationNames(object.id, names);
  }, [names, object.id, setAnimationNames]);

  useEffect(() => {
    if (!clipMode) {
      Object.values(actions).forEach((action) => action?.stop());
      return;
    }
    const wanted = (object.animation as ClipId | null) ?? 'idle';
    Object.entries(actions).forEach(([key, action]) => {
      if (!action) return;
      if (key === wanted) {
        action.reset().fadeIn(0.15).play();
        action.paused = object.animationPlaying === false;
      } else {
        action.fadeOut(0.12);
      }
    });
  }, [actions, object.animation, object.animationPlaying, clipMode]);
}

function useInstanceMotion(root: Object3D, object: SceneObject, asset: CharacterAsset, clipMode: boolean) {
  const customAnimations = useCharacterLibrary((s) => s.customAnimations);
  const anim = customAnimations.find((a) => a.id === object.customAnimationId) ?? null;
  const timeRef = useRef(object.customAnimationTime ?? 0);

  useLayoutEffect(() => {
    if (clipMode || object.customAnimationId) return;
    const preset = getPosePreset(object.pose);
    const bones = object.bonePose ?? preset?.bones ?? null;
    applyBonePose(root, asset.skeletonType, bones);
  }, [root, clipMode, object.pose, object.bonePose, object.customAnimationId, asset.skeletonType]);

  useLayoutEffect(() => {
    timeRef.current = object.customAnimationTime ?? 0;
  }, [object.customAnimationTime]);

  useFrame((_, delta) => {
    if (!anim || !object.customAnimationId) return;
    if (object.customAnimationPlaying) {
      timeRef.current = (timeRef.current + delta) % Math.max(0.05, anim.duration);
    }
    const keys = [...anim.keys].sort((a, b) => a.time - b.time);
    if (!keys.length) return;
    const time = timeRef.current;
    const next = keys.find((k) => k.time >= time) ?? keys[keys.length - 1];
    const prev = [...keys].reverse().find((k) => k.time <= time) ?? keys[0];
    const span = Math.max(0.0001, next.time - prev.time);
    const t = next === prev ? 0 : (time - prev.time) / span;
    applyBonePose(root, asset.skeletonType, lerpBonePose(prev.bones, next.bones, t));
  });
}

function activeBoneMap(object: SceneObject) {
  const custom = object.bonePose;
  if (custom && Object.keys(custom).length > 0) return custom;
  return getPosePreset(object.pose)?.bones ?? null;
}

function isClipMode(object: SceneObject, asset: CharacterAsset): boolean {
  if (object.customAnimationId) return false;
  const preset = getPosePreset(object.pose);
  if (preset?.kind === 'bones') return false;
  if (activeBoneMap(object)) return false;
  const wanted = (object.animation as ClipId | null) ?? 'idle';
  const clip = clipsForSet(asset.animationSetId, asset.skeletonType).find((c) => c.id === wanted);
  return clip?.kind === 'clip' && clip.implemented;
}

function HumanRpmActor({ object, asset }: { object: SceneObject; asset: CharacterAsset }) {
  const feminine = asset.skeletonType === 'rpm-feminine';
  const { scene } = useGLTF(asset.modelUrl);
  const idle = useGLTF(feminine ? '/director/models/anims/F_Idle.glb' : '/director/models/anims/M_Idle.glb');
  const walk = useGLTF(feminine ? '/director/models/anims/F_Walk.glb' : '/director/models/anims/M_Walk.glb');
  const run = useGLTF(feminine ? '/director/models/anims/F_Run.glb' : '/director/models/anims/M_Run.glb');
  const talk = useGLTF(feminine ? '/director/models/anims/F_Talk.glb' : '/director/models/anims/M_Talk.glb');
  const look = useGLTF('/director/models/anims/M_Look.glb');
  const root = useMemo(() => SkeletonUtils.clone(scene) as Object3D, [scene]);
  const group = useRef<Group>(null);
  const clips = useMemo(() => {
    const out: AnimationClip[] = [];
    const add = (src: AnimationClip[] | undefined, name: string) => {
      const renamed = renameClip(src?.[0], name);
      if (renamed) out.push(renamed);
    };
    add(idle.animations, 'idle');
    add(idle.animations, 'stand');
    add(walk.animations, 'walk');
    add(run.animations, 'run');
    add(talk.animations, 'talk');
    add(look.animations, 'look');
    return out;
  }, [idle.animations, walk.animations, run.animations, talk.animations, look.animations]);
  const { actions, names } = useAnimations(clips, group);
  const clipMode = isClipMode(object, asset);
  useAppearance(root, asset);
  usePlay(object, actions, names, clipMode);
  useInstanceMotion(root, object, asset, clipMode);
  return (
    <group ref={group}>
      <primitive object={root} />
    </group>
  );
}

function EmbeddedActor({ object, asset }: { object: SceneObject; asset: CharacterAsset }) {
  const { scene, animations } = useGLTF(asset.modelUrl);
  const root = useMemo(() => SkeletonUtils.clone(scene) as Object3D, [scene]);
  const group = useRef<Group>(null);
  const clips = useMemo(() => {
    if (asset.animationSetId === 'three-horse' || asset.animationSetId === 'three-bird' || asset.animationSetId === 'embedded') {
      const first = animations[0];
      if (!first) return [];
      const names = animations.length >= 3
        ? ['idle', 'walk', 'run']
        : ['idle', 'walk', 'run'];
      return names.map((name, i) => {
        const src = animations[i] ?? first;
        const c = src.clone();
        c.name = name;
        return c;
      });
    }
    return clipsForSet(asset.animationSetId, asset.skeletonType)
      .filter((d) => d.implemented && d.embeddedName)
      .map((d) => {
        const found =
          d.embeddedName === '*'
            ? animations[0]
            : animations.find((c) => c.name === d.embeddedName) ?? animations[0];
        return renameClip(found, d.id);
      })
      .filter((c): c is AnimationClip => !!c);
  }, [animations, asset.animationSetId, asset.skeletonType]);
  const { actions, names } = useAnimations(clips, group);
  const clipMode = isClipMode(object, asset);
  useAppearance(root, asset);
  usePlay(object, actions, names, clipMode);
  useInstanceMotion(root, object, asset, clipMode);
  return (
    <group ref={group}>
      <primitive object={root} />
    </group>
  );
}

export function CharacterActor({ object, asset }: { object: SceneObject; asset: CharacterAsset }) {
  const rpm = asset.skeletonType === 'rpm-masculine' || asset.skeletonType === 'rpm-feminine';
  if (rpm) return <HumanRpmActor object={object} asset={asset} />;
  return <EmbeddedActor object={object} asset={asset} />;
}
