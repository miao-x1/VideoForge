import { useDirectorStore } from '../store/useDirectorStore';
import { useCharacterLibrary } from './useCharacterLibrary';
import type { DirectorSceneState } from '../types';

export interface CharacterControlRecord {
  character_id: string;
  instance_id: string;
  name: string;
  position: [number, number, number];
  rotation: [number, number, number];
  scale: [number, number, number];
  pose: string | null;
  animation: string | null;
  animation_playing: boolean;
  skeleton_pose: Record<string, [number, number, number]> | null;
  custom_animation_id: string | null;
}

export interface SceneControlData {
  scene_id: string;
  scene_name: string;
  aspect_ratio: string;
  camera_position: [number, number, number];
  camera_rotation: [number, number, number];
  camera_fov: number;
  characters: CharacterControlRecord[];
  depth: null;
  segmentation: null;
  normal: null;
  motion: null;
}

export function buildControlData(state?: DirectorSceneState): SceneControlData {
  const snap = state ?? useDirectorStore.getState().getSceneState();
  const camera = snap.cameras.find((c) => c.id === snap.activeCamera) ?? snap.cameras[0];
  const lib = useCharacterLibrary.getState();
  const characters = snap.objects
    .filter((o) => o.characterId)
    .map((o) => {
      const asset = lib.getById(o.characterId!);
      return {
        character_id: o.characterId!,
        instance_id: o.id,
        name: asset?.name ?? o.name,
        position: o.position,
        rotation: o.rotation,
        scale: o.scale,
        pose: o.pose ?? null,
        animation: o.animation,
        animation_playing: o.animationPlaying !== false,
        skeleton_pose: o.bonePose ?? null,
        custom_animation_id: o.customAnimationId ?? null,
      };
    });
  return {
    scene_id: snap.sceneId,
    scene_name: snap.sceneName ?? '',
    aspect_ratio: snap.aspectRatio,
    camera_position: camera?.position ?? [0, 1.6, 5],
    camera_rotation: camera?.rotation ?? [0, 0, 0],
    camera_fov: camera?.fov ?? 45,
    characters,
    depth: null,
    segmentation: null,
    normal: null,
    motion: null,
  };
}

export function downloadControlData(data: SceneControlData = buildControlData()): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${data.scene_id}.control.json`;
  a.click();
  URL.revokeObjectURL(url);
}
