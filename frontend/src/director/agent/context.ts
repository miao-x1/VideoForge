import { useCharacterLibrary } from '../characters/useCharacterLibrary';
import { getDirectorProjectId, getStoredUserId } from '../scope';
import { useDirectorStore } from '../store/useDirectorStore';
import type { SceneBook } from '../persist';
import type { DirectorSceneState, SceneObject } from '../types';

export interface AgentFocus {
  character_id: string | null;
  object_id: string | null;
  camera_id: string | null;
  shot_id: string | null;
}

export interface DirectorContext {
  user_id?: string;
  project_id?: string;
  scene_id: string;
  scene_name: string;
  objects: Array<{
    id: string;
    name: string;
    type: string;
    catalogId?: string;
    characterId?: string | null;
    position: number[];
    rotation: number[];
    scale: number[];
    animation: string | null;
    pose?: string | null;
  }>;
  cameras: Array<{
    id: string;
    name: string;
    position: number[];
    rotation: number[];
    fov: number;
    target?: number[] | null;
    motion?: string | null;
  }>;
  active_camera: string;
  selected_id: string | null;
  selected_object: string | null;
  selected_character: string | null;
  selected_camera: string | null;
  environment: DirectorSceneState['environment'];
  shot_duration: number;
  shot_description: string;
  shot_type?: string;
  camera_movement?: string;
  emotion?: string;
  time_of_day?: string;
  image_url?: string | null;
  composition_url?: string | null;
  backdrop_url?: string | null;
  attachment_urls?: string[];
  aspect_ratio?: string;
  gen_duration?: number;
  video_url?: string | null;
  user_message?: string;
  timeline: DirectorSceneState['timeline'];
  scenes: Array<{ id: string; name: string; duration?: number }>;
  characters: Array<{ id: string; name: string; type?: string; templateId?: string; sourceType?: string }>;
  focus: AgentFocus;
}

export function slimObject(o: SceneObject) {
  return {
    id: o.id,
    name: o.name,
    type: o.type,
    catalogId: o.catalogId,
    characterId: o.characterId,
    position: [...o.position],
    rotation: [...o.rotation],
    scale: [...o.scale],
    animation: o.animation,
    pose: o.pose ?? null,
  };
}

export function buildDirectorContext(focus: AgentFocus): DirectorContext {
  const s = useDirectorStore.getState();
  const lib = useCharacterLibrary.getState();
  const selectedObj = s.objects.find((o) => o.id === s.selectedId) ?? null;
  const selectedCam = s.cameras.find((c) => c.id === s.selectedId) ?? null;
  return {
    user_id: getStoredUserId() || undefined,
    project_id: getDirectorProjectId() || undefined,
    scene_id: s.sceneId,
    scene_name: s.sceneName || '分镜',
    objects: s.objects.map(slimObject),
    cameras: s.cameras.map((c) => ({
      id: c.id,
      name: c.name,
      position: [...c.position],
      rotation: [...c.rotation],
      fov: c.fov,
      target: c.target ?? null,
      motion: c.motion ?? null,
    })),
    active_camera: s.activeCamera,
    selected_id: s.selectedId,
    selected_object: selectedObj?.id ?? null,
    selected_character: selectedObj?.characterId ?? selectedObj?.id ?? focus.character_id,
    selected_camera: selectedCam?.id ?? s.activeCamera,
    environment: s.environment,
    shot_duration: s.shotDuration ?? 4,
    shot_description: s.shotDescription ?? '',
    shot_type: s.shotType,
    camera_movement: s.cameraMovement,
    emotion: s.emotion,
    time_of_day: s.timeOfDay,
    image_url: s.imageUrl,
    composition_url: s.compositionUrl,
    backdrop_url: s.environment.backdropUrl ?? null,
    attachment_urls: [],
    aspect_ratio: s.aspectRatio,
    gen_duration: s.shotDuration ?? 5,
    video_url: s.videoUrl,
    timeline: s.timeline ?? { duration: s.shotDuration ?? 4, keys: [] },
    scenes: s.scenes.map((sc) => ({
      id: sc.sceneId,
      name: sc.sceneName || '分镜',
      duration: sc.shotDuration,
    })),
    characters: lib.characters.map((c) => ({
      id: c.id,
      name: c.name,
      type: c.characterType,
      templateId: c.templateId,
      sourceType: c.sourceType,
    })),
    focus,
  };
}

export function captureBook(): SceneBook {
  const s = useDirectorStore.getState();
  const current = s.getSceneState();
  return {
    currentId: current.sceneId,
    scenes: s.scenes.map((sc) => (sc.sceneId === current.sceneId ? current : sc)),
    projectName: s.projectName,
    chapterName: s.chapterName,
  };
}
