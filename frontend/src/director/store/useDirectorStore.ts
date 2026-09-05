import { create } from 'zustand';
import type {
  AspectRatio,
  Atmosphere,
  CameraAngle,
  CharacterRelation,
  CharacterRelationKind,
  DirectorSceneState,
  SceneCamera,
  SceneEnvironment,
  SceneObject,
  SceneObjectType,
  SceneTimeline,
  ShotSize,
  TimelineKey,
  TransformMode,
  Vec3,
  ViewMode,
  Weather,
} from '../types';
import {
  createEmptyScene,
  DEFAULT_ENVIRONMENT,
  DEFAULT_MATERIAL,
  DEFAULT_SHOT_CAMERA,
  lookAtRotation,
  newId,
  normalizeObject,
  normalizeScene,
} from '../types';
import { getCatalogItem } from '../catalog';
import { getTemplate } from '../characters/templates';
import { useCharacterLibrary } from '../characters/useCharacterLibrary';
import { loadSceneBook, saveSceneBook, saveSceneToStorage, type SceneBook } from '../persist';
import { flushSceneBookSync, scheduleSceneBookSync } from '../syncSchedule';
import { useSaveStatus } from '../saveStatus';
import { SCENE_PRESETS } from '../scenePresets';
import { computeBlocking, type BlockingPreset } from '../directing/blocking';
import { centroidOf, environmentLook, frameCamera } from '../directing/look';
import { planAutoStage } from '../directing/autoStage';
import { DIRECTOR_ACTIONS } from '../directing/actions';

const SAMPLE_GLB =
  'https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/master/2.0/Duck/glTF-Binary/Duck.glb';

const HISTORY_LIMIT = 80;

function persist(state: DirectorSceneState, immediate = false): void {
  try {
    saveSceneToStorage(state);
    const store = useDirectorStore.getState();
    const scenes = store.scenes.map((s) => (s.sceneId === state.sceneId ? state : s));
    if (!scenes.some((s) => s.sceneId === state.sceneId)) scenes.push(state);
    const book: SceneBook = {
      currentId: state.sceneId,
      scenes,
      projectName: store.projectName,
      chapterName: store.chapterName,
    };
    saveSceneBook(book);
    useSaveStatus.getState().markSaving();
    if (immediate) flushSceneBookSync(book);
    else scheduleSceneBookSync(book);
    if (store.scenes !== scenes) useDirectorStore.setState({ scenes });
  } catch {
    useSaveStatus.getState().markError('本地保存失败');
  }
}

function snapshot(get: () => DirectorStore): DirectorSceneState {
  const s = get();
  return {
    sceneId: s.sceneId,
    sceneName: s.sceneName,
    version: 1,
    aspectRatio: s.aspectRatio,
    objects: s.objects,
    cameras: s.cameras,
    activeCamera: s.activeCamera,
    selectedId: s.selectedId,
    transformMode: s.transformMode,
    viewMode: s.viewMode,
    environment: s.environment,
    shotDuration: s.shotDuration ?? 4,
    shotDescription: s.shotDescription ?? '',
    timeline: s.timeline ?? { duration: s.shotDuration ?? 4, keys: [] },
    shotType: s.shotType,
    cameraMovement: s.cameraMovement,
    emotion: s.emotion,
    timeOfDay: s.timeOfDay,
    imagePrompt: s.imagePrompt,
    videoPrompt: s.videoPrompt,
    negativePrompt: s.negativePrompt,
    imageUrl: s.imageUrl,
    videoUrl: s.videoUrl,
    generationId: s.generationId,
    currentGenerationId: s.generationId,
    compositionUrl: s.compositionUrl,
    canvasX: s.canvasX,
    canvasY: s.canvasY,
    projectName: s.projectName,
    chapterName: s.chapterName,
    locationName: s.locationName,
    relations: s.relations,
  };
}

export interface DirectorStore extends DirectorSceneState {
  getSceneState: () => DirectorSceneState;
  setSceneState: (state: DirectorSceneState) => void;
  resetScene: () => void;
  addObject: (partial: {
    type: SceneObjectType;
    name: string;
    modelUrl?: string | null;
    primitive?: SceneObject['primitive'];
    position?: Vec3;
    color?: string;
    catalogId?: string;
    characterId?: string | null;
    lightIntensity?: number;
    scale?: Vec3;
    pose?: string | null;
    animation?: string | null;
  }) => string;
  addFromCatalog: (catalogId: string, position?: Vec3) => string | null;
  addSampleModel: () => string;
  addCharacter: () => string;
  addOfficialTemplate: (templateId: string) => string | null;
  addProp: () => string;
  instanceCharacter: (characterId: string) => string | null;
  createCharacterFromTemplate: (templateId: string, name?: string) => string | null;
  duplicateInstance: (instanceId: string) => string | null;
  sceneName: string;
  scenes: DirectorSceneState[];
  createShotScene: (name?: string) => string;
  switchScene: (sceneId: string) => void;
  renameScene: (sceneId: string, name: string) => void;
  deleteScene: (sceneId: string) => void;
  removeObject: (id: string) => void;
  selectObject: (id: string | null) => void;
  updateObject: (id: string, patch: Partial<SceneObject>) => void;
  updateTransform: (id: string, transform: Partial<Pick<SceneObject, 'position' | 'rotation' | 'scale'>>) => void;
  setAnimationNames: (id: string, names: string[]) => void;
  addCamera: () => string;
  selectCamera: (id: string) => void;
  updateCamera: (id: string, patch: Partial<SceneCamera>) => void;
  resetActiveCamera: () => void;
  setTransformMode: (mode: TransformMode) => void;
  setViewMode: (mode: ViewMode) => void;
  setAspectRatio: (ratio: AspectRatio) => void;
  setEnvironment: (patch: Partial<SceneEnvironment>) => void;
  persistNow: () => void;
  historyPast: DirectorSceneState[];
  historyFuture: DirectorSceneState[];
  canUndo: () => boolean;
  canRedo: () => boolean;
  undo: () => void;
  redo: () => void;
  focusNonce: number;
  requestFocus: () => void;
  patchObjectLive: (id: string, patch: Partial<SceneObject>) => void;
  patchCameraLive: (id: string, patch: Partial<SceneCamera>) => void;
  loadBook: (book: SceneBook, options?: { record?: boolean }) => void;
  removeCamera: (id: string) => boolean;
  lookAt: (cameraId: string, target: Vec3) => void;
  updateShotMeta: (patch: Partial<{
    sceneName: string;
    shotDuration: number;
    shotDescription: string;
    shotType: string;
    cameraMovement: string;
    emotion: string;
    timeOfDay: string;
    imagePrompt: string;
    videoPrompt: string;
    negativePrompt: string;
    imageUrl: string | null;
    videoUrl: string | null;
    generationId: string | null;
    compositionUrl: string | null;
  }>) => void;
  setCanvasPos: (sceneId: string, x: number, y: number) => void;
  duplicateShotScene: () => string;
  addTimelineKey: (key: Omit<TimelineKey, 'id'> & { id?: string }) => string;
  updateTimelineKey: (id: string, patch: Partial<TimelineKey>) => void;
  removeTimelineKey: (id: string) => void;
  setTimeline: (timeline: SceneTimeline) => void;
  projectName: string;
  chapterName: string;
  locationName: string;
  relations: CharacterRelation[];
  setProjectMeta: (patch: Partial<{ projectName: string; chapterName: string; locationName: string }>) => void;
  setRelation: (fromId: string, toId: string, kind: CharacterRelationKind) => void;
  applyBlocking: (preset: BlockingPreset) => void;
  applyCameraTemplate: (id: 'romance' | 'battle' | 'dialogue') => void;
  applyShotFraming: (size: ShotSize, angle?: CameraAngle) => void;
  applyEnvironmentLook: (weather?: Weather, timeOfDay?: string, atmosphere?: Atmosphere) => void;
  applyScenePreset: (presetId: string) => void;
  applyAction: (actionId: string, objectId?: string | null) => void;
  applyAdvice: (id: string) => void;
  applyAutoStage: (text: string) => string;
}

function loadInitialBook() {
  try {
    const bookLoaded = loadSceneBook();
    const raw = bookLoaded?.scenes.find((s) => s.sceneId === bookLoaded.currentId)
      ?? bookLoaded?.scenes[0]
      ?? createEmptyScene();
    const initial = normalizeScene(raw);
    const initialScenes = bookLoaded?.scenes?.length
      ? bookLoaded.scenes.map((s) => normalizeScene(s))
      : [initial];
    return { bookLoaded, initial, initialScenes };
  } catch {
    const initial = createEmptyScene();
    return { bookLoaded: null, initial, initialScenes: [initial] };
  }
}

const { bookLoaded, initial, initialScenes } = loadInitialBook();

function cloneScene(state: DirectorSceneState): DirectorSceneState {
  return JSON.parse(JSON.stringify(normalizeScene(state))) as DirectorSceneState;
}

function applyScene(get: () => DirectorStore, next: DirectorSceneState) {
  const normalized = normalizeScene(next);
  const scenes = get().scenes.map((s) => (s.sceneId === normalized.sceneId ? normalized : s));
  if (!scenes.some((s) => s.sceneId === normalized.sceneId)) scenes.push(normalized);
  return { ...normalized, scenes };
}

export const useDirectorStore = create<DirectorStore>((set, get) => {
  const record = () => {
    const past = [...get().historyPast, cloneScene(snapshot(get))].slice(-HISTORY_LIMIT);
    set({ historyPast: past, historyFuture: [] });
  };

  return {
  ...initial,
  sceneName: initial.sceneName ?? '镜头 1',
  scenes: initialScenes,
  environment: initial.environment ?? { ...DEFAULT_ENVIRONMENT },
  objects: (initial.objects ?? []).map((o) => normalizeObject(o)),
  historyPast: [] as DirectorSceneState[],
  historyFuture: [] as DirectorSceneState[],
  focusNonce: 0,
  projectName: initial.projectName || bookLoaded?.projectName || '未命名项目',
  chapterName: initial.chapterName || bookLoaded?.chapterName || '第1集',
  locationName: initial.locationName || '',
  relations: initial.relations ?? [],

  getSceneState: () => snapshot(get),
  canUndo: () => get().historyPast.length > 0,
  canRedo: () => get().historyFuture.length > 0,
  undo: () => {
    const past = get().historyPast;
    if (!past.length) return;
    const current = cloneScene(snapshot(get));
    const prev = past[past.length - 1];
    set({
      ...applyScene(get, prev),
      historyPast: past.slice(0, -1),
      historyFuture: [...get().historyFuture, current],
    });
    persist(snapshot(get));
  },
  redo: () => {
    const future = get().historyFuture;
    if (!future.length) return;
    const current = cloneScene(snapshot(get));
    const next = future[future.length - 1];
    set({
      ...applyScene(get, next),
      historyFuture: future.slice(0, -1),
      historyPast: [...get().historyPast, current],
    });
    persist(snapshot(get));
  },
  requestFocus: () => set({ focusNonce: get().focusNonce + 1 }),

  setSceneState: (state) => {
    const next = normalizeScene(state);
    set({ ...next });
    persist(snapshot(get));
  },

  resetScene: () => {
    const empty = createEmptyScene();
    empty.sceneId = get().sceneId;
    empty.sceneName = get().sceneName;
    set({ ...empty, scenes: get().scenes });
    persist(snapshot(get));
  },

  addObject: ({ type, name, modelUrl = null, primitive, position, color, catalogId, characterId, lightIntensity, scale, pose, animation }) => {
    record();
    const id = newId(type);
    const count = get().objects.filter((o) => o.name.startsWith(name)).length;
    const obj = normalizeObject({
      id,
      type,
      name: count === 0 ? name : `${name}${count + 1}`,
      catalogId,
      characterId,
      modelUrl,
      primitive,
      position: position ?? [get().objects.length * 1.6, 0, 0],
      rotation: [0, 0, 0],
      scale: scale ?? [1, 1, 1],
      color: color ?? DEFAULT_MATERIAL.color,
      lightIntensity,
      pose: pose ?? (characterId ? 'stand' : null),
      animation: animation ?? (characterId ? 'idle' : null),
      animationPlaying: true,
    });
    set((s) => ({ objects: [...s.objects, obj], selectedId: id }));
    persist(snapshot(get));
    return id;
  },

  addFromCatalog: (catalogId, position) => {
    const item = getCatalogItem(catalogId);
    if (!item) return null;
    return get().addObject({
      type: item.category,
      name: item.name,
      catalogId: item.id,
      primitive: item.shape,
      color: item.color,
      scale: item.scale,
      lightIntensity: item.lightIntensity,
      position,
    });
  },

  addSampleModel: () =>
    get().addObject({
      type: 'character',
      name: '示例模型',
      modelUrl: SAMPLE_GLB,
      primitive: 'box',
    }),

  addOfficialTemplate: (templateId) => {
    const lib = useCharacterLibrary.getState();
    const official = lib.characters.find((c) => c.templateId === templateId && c.sourceType === 'official');
    if (official) return get().instanceCharacter(official.id);
    return get().createCharacterFromTemplate(templateId);
  },

  addCharacter: () => get().addOfficialTemplate('human_male_young_01') ?? '',

  addProp: () => get().addFromCatalog('crate') ?? '',

  instanceCharacter: (characterId) => {
    const lib = useCharacterLibrary.getState();
    const asset = lib.getById(characterId);
    if (!asset) return null;
    lib.touchRecent(asset.id);
    const template = getTemplate(asset.templateId);
    return get().addObject({
      type: asset.characterType === 'animal' ? 'animal' : 'character',
      name: asset.name,
      characterId: asset.id,
      modelUrl: asset.modelUrl,
      scale: template?.defaultScale ?? [1, 1, 1],
      pose: asset.defaultPose ?? 'stand',
      animation: 'idle',
    });
  },

  createCharacterFromTemplate: (templateId, name) => {
    const asset = useCharacterLibrary.getState().createFromTemplate(templateId, name);
    if (!asset) return null;
    return get().instanceCharacter(asset.id);
  },

  duplicateInstance: (instanceId) => {
    const obj = get().objects.find((o) => o.id === instanceId);
    if (!obj) return null;
    return get().addObject({
      type: obj.type,
      name: obj.name,
      characterId: obj.characterId,
      modelUrl: obj.modelUrl,
      primitive: obj.primitive,
      color: obj.color,
      scale: obj.scale,
      pose: obj.pose,
      animation: obj.animation,
      position: [obj.position[0] + 1.2, obj.position[1], obj.position[2]],
    });
  },

  createShotScene: (name) => {
    persist(snapshot(get));
    const empty = createEmptyScene();
    const n = get().scenes.length;
    empty.sceneName = name?.trim() || `镜头 ${n + 1}`;
    empty.projectName = get().projectName;
    empty.chapterName = get().chapterName;
    empty.canvasX = 248 + (n % 3) * 316;
    empty.canvasY = Math.floor(n / 3) * 304;
    set({
      ...empty,
      projectName: get().projectName,
      chapterName: get().chapterName,
      scenes: [...get().scenes, empty],
    });
    persist(snapshot(get));
    return empty.sceneId;
  },

  switchScene: (sceneId) => {
    persist(snapshot(get));
    const next = get().scenes.find((s) => s.sceneId === sceneId);
    if (!next) return;
    const normalized = normalizeScene(next);
    set({
      ...normalized,
      sceneName: normalized.sceneName ?? next.sceneName,
      projectName: get().projectName,
      chapterName: get().chapterName,
      scenes: get().scenes,
    });
    persist(snapshot(get));
  },

  renameScene: (sceneId, name) => {
    set((s) => ({
      sceneName: s.sceneId === sceneId ? name : s.sceneName,
      scenes: s.scenes.map((sc) => (sc.sceneId === sceneId ? { ...sc, sceneName: name } : sc)),
    }));
    persist(snapshot(get));
  },

  deleteScene: (sceneId) => {
    if (get().scenes.length <= 1) return;
    const remaining = get().scenes.filter((s) => s.sceneId !== sceneId);
    const current = get().sceneId === sceneId ? remaining[0] : get().scenes.find((s) => s.sceneId === get().sceneId);
    if (!current) return;
    const normalized = normalizeScene(current);
    set({
      ...normalized,
      scenes: remaining,
    });
    persist(snapshot(get), true);
  },

  removeObject: (id) => {
    const obj = get().objects.find((o) => o.id === id);
    if (obj?.locked) return;
    record();
    set((s) => ({
      objects: s.objects.filter((o) => o.id !== id),
      selectedId: s.selectedId === id ? null : s.selectedId,
    }));
    persist(snapshot(get));
  },

  selectObject: (id) => set({ selectedId: id }),

  updateObject: (id, patch) => {
    const obj = get().objects.find((o) => o.id === id);
    if (obj?.locked && !('locked' in patch) && !('visible' in patch) && !('name' in patch)) return;
    record();
    set((s) => ({
      objects: s.objects.map((o) => (o.id === id ? { ...o, ...patch } : o)),
    }));
    persist(snapshot(get));
  },

  updateTransform: (id, transform) => {
    const obj = get().objects.find((o) => o.id === id);
    if (obj?.locked) return;
    record();
    set((s) => ({
      objects: s.objects.map((o) => (o.id === id ? { ...o, ...transform } : o)),
    }));
    persist(snapshot(get));
  },

  setAnimationNames: (id, names) => {
    const obj = get().objects.find((o) => o.id === id);
    if (!obj) return;
    const same =
      obj.animations.length === names.length && obj.animations.every((n, i) => n === names[i]);
    if (same) return;
    set((s) => ({
      objects: s.objects.map((o) => (o.id === id ? { ...o, animations: names } : o)),
    }));
    persist(snapshot(get));
  },

  addCamera: () => {
    record();
    const id = newId('camera');
    const n = get().cameras.length + 1;
    const cam: SceneCamera = {
      id,
      name: `机位${n}`,
      position: [0, 1.6, 5 + n],
      rotation: [0, 0, 0],
      fov: 45,
    };
    set((s) => ({ cameras: [...s.cameras, cam], activeCamera: id }));
    persist(snapshot(get));
    return id;
  },

  selectCamera: (id) => {
    set({ activeCamera: id, selectedId: id });
    persist(snapshot(get));
  },

  updateCamera: (id, patch) => {
    record();
    set((s) => ({
      cameras: s.cameras.map((c) => (c.id === id ? { ...c, ...patch } : c)),
    }));
    persist(snapshot(get));
  },

  resetActiveCamera: () => {
    const { viewMode, activeCamera } = get();
    if (viewMode === 'shot') {
      get().updateCamera(activeCamera, {
        position: [...DEFAULT_SHOT_CAMERA.position],
        rotation: [...DEFAULT_SHOT_CAMERA.rotation],
        fov: DEFAULT_SHOT_CAMERA.fov,
      });
    }
  },

  setTransformMode: (mode) => set({ transformMode: mode }),
  setViewMode: (mode) => set({ viewMode: mode }),
  setAspectRatio: (ratio) => {
    set({ aspectRatio: ratio });
    persist(snapshot(get));
  },
  setEnvironment: (patch) => {
    record();
    set((s) => ({ environment: { ...s.environment, ...patch } }));
    persist(snapshot(get));
  },
  persistNow: () => persist(snapshot(get), true),

  removeCamera: (id) => {
    if (get().cameras.length <= 1) return false;
    record();
    const remaining = get().cameras.filter((c) => c.id !== id);
    const active = get().activeCamera === id ? remaining[0].id : get().activeCamera;
    set({
      cameras: remaining,
      activeCamera: active,
      selectedId: get().selectedId === id ? null : get().selectedId,
    });
    persist(snapshot(get));
    return true;
  },

  lookAt: (cameraId, target) => {
    const cam = get().cameras.find((c) => c.id === cameraId);
    if (!cam) return;
    record();
    set((s) => ({
      cameras: s.cameras.map((c) =>
        c.id === cameraId ? { ...c, target, rotation: lookAtRotation(c.position, target) } : c,
      ),
    }));
    persist(snapshot(get));
  },

  updateShotMeta: (patch) => {
    record();
    set((s) => ({
      sceneName: patch.sceneName ?? s.sceneName,
      shotDuration: patch.shotDuration ?? s.shotDuration ?? 4,
      shotDescription: patch.shotDescription ?? s.shotDescription ?? '',
      shotType: patch.shotType ?? s.shotType,
      cameraMovement: patch.cameraMovement ?? s.cameraMovement,
      emotion: patch.emotion ?? s.emotion,
      timeOfDay: patch.timeOfDay ?? s.timeOfDay,
      imagePrompt: patch.imagePrompt ?? s.imagePrompt,
      videoPrompt: patch.videoPrompt ?? s.videoPrompt,
      negativePrompt: patch.negativePrompt ?? s.negativePrompt,
      imageUrl: patch.imageUrl !== undefined ? patch.imageUrl : s.imageUrl,
      videoUrl: patch.videoUrl !== undefined ? patch.videoUrl : s.videoUrl,
      generationId: patch.generationId !== undefined ? patch.generationId : s.generationId,
      compositionUrl: patch.compositionUrl !== undefined ? patch.compositionUrl : s.compositionUrl,
      timeline: {
        duration: patch.shotDuration ?? s.timeline?.duration ?? s.shotDuration ?? 4,
        keys: s.timeline?.keys ?? [],
      },
    }));
    persist(snapshot(get));
  },

  duplicateShotScene: () => {
    persist(snapshot(get));
    const copy = cloneScene(snapshot(get));
    copy.sceneId = newId('scene');
    copy.sceneName = `${get().sceneName || '镜头'} 副本`;
    copy.canvasX = (get().canvasX ?? 248) + 40;
    copy.canvasY = (get().canvasY ?? 0) + 40;
    set({
      ...copy,
      scenes: [...get().scenes, copy],
      historyPast: [],
      historyFuture: [],
    });
    persist(snapshot(get));
    return copy.sceneId;
  },

  addTimelineKey: (key) => {
    record();
    const id = key.id ?? newId('key');
    const next: TimelineKey = { ...key, id };
    set((s) => ({
      timeline: {
        duration: s.timeline?.duration ?? s.shotDuration ?? 4,
        keys: [...(s.timeline?.keys ?? []), next].sort((a, b) => a.time - b.time),
      },
    }));
    persist(snapshot(get));
    return id;
  },

  updateTimelineKey: (id, patch) => {
    record();
    set((s) => ({
      timeline: {
        duration: s.timeline?.duration ?? 4,
        keys: (s.timeline?.keys ?? []).map((k) => (k.id === id ? { ...k, ...patch } : k)),
      },
    }));
    persist(snapshot(get));
  },

  removeTimelineKey: (id) => {
    record();
    set((s) => ({
      timeline: {
        duration: s.timeline?.duration ?? 4,
        keys: (s.timeline?.keys ?? []).filter((k) => k.id !== id),
      },
    }));
    persist(snapshot(get));
  },

  setTimeline: (timeline) => {
    record();
    set({ timeline });
    persist(snapshot(get));
  },

  patchObjectLive: (id, patch) => {
    set((s) => ({
      objects: s.objects.map((o) => (o.id === id ? { ...o, ...patch } : o)),
    }));
  },

  patchCameraLive: (id, patch) => {
    set((s) => ({
      cameras: s.cameras.map((c) => (c.id === id ? { ...c, ...patch } : c)),
    }));
  },

  loadBook: (book, options) => {
    if (!book.scenes.length) return;
    if (options?.record !== false) record();
    const current = book.scenes.find((s) => s.sceneId === book.currentId) ?? book.scenes[0];
    const normalized = normalizeScene(current);
    set({
      ...normalized,
      scenes: book.scenes.map((s) => normalizeScene(s)),
    });
    persist(snapshot(get), true);
  },

  setCanvasPos: (sceneId, x, y) => {
    set((s) => ({
      canvasX: s.sceneId === sceneId ? x : s.canvasX,
      canvasY: s.sceneId === sceneId ? y : s.canvasY,
      scenes: s.scenes.map((sc) => (sc.sceneId === sceneId ? { ...sc, canvasX: x, canvasY: y } : sc)),
    }));
  },

  setProjectMeta: (patch) => {
    set((s) => ({
      projectName: patch.projectName ?? s.projectName,
      chapterName: patch.chapterName ?? s.chapterName,
      locationName: patch.locationName ?? s.locationName,
    }));
    persist(snapshot(get));
  },

  setRelation: (fromId, toId, kind) => {
    record();
    set((s) => ({
      relations: [
        ...s.relations.filter((r) => !(r.fromId === fromId && r.toId === toId)),
        { fromId, toId, kind },
      ],
    }));
    persist(snapshot(get));
  },

  applyBlocking: (preset) => {
    const chars = get().objects.filter((o) => o.characterId);
    if (!chars.length) return;
    record();
    const poses = computeBlocking(preset, chars.length);
    set((s) => ({
      objects: s.objects.map((o) => {
        const idx = chars.findIndex((c) => c.id === o.id);
        if (idx < 0 || !poses[idx]) return o;
        return { ...o, position: poses[idx].position, rotation: poses[idx].rotation };
      }),
    }));
    persist(snapshot(get));
  },

  applyShotFraming: (size, angle) => {
    const chars = get().objects.filter((o) => o.characterId);
    const target = centroidOf(chars.map((c) => c.position));
    const cam = get().cameras.find((c) => c.id === get().activeCamera);
    const next = frameCamera(size, angle ?? cam?.angle ?? 'eye', target);
    record();
    set((s) => ({
      cameras: s.cameras.map((c) => (c.id === s.activeCamera ? { ...c, ...next } : c)),
      shotType: size === 'close' || size === 'extreme_close' ? 'close-up' : size === 'long' || size === 'extreme_long' ? 'wide shot' : 'medium shot',
    }));
    persist(snapshot(get));
  },

  applyCameraTemplate: (id) => {
    if (id === 'romance') {
      get().applyBlocking('embrace');
      get().applyEnvironmentLook(undefined, undefined, 'romantic');
      get().applyShotFraming('close', 'eye');
      get().updateShotMeta({ cameraMovement: 'push_in', emotion: '柔光双人近景', shotType: 'close-up' });
      return;
    }
    if (id === 'battle') {
      get().applyBlocking('conflict');
      get().applyEnvironmentLook(undefined, undefined, 'tense');
      get().applyShotFraming('medium', 'low');
      get().updateShotMeta({ cameraMovement: 'tracking', emotion: '低机位运动感', shotType: 'wide shot' });
      return;
    }
    get().applyBlocking('dialogue');
    get().applyShotFraming('medium', 'eye');
    get().updateShotMeta({ cameraMovement: 'static', shotType: 'medium shot' });
  },

  applyEnvironmentLook: (weather, timeOfDay, atmosphere) => {
    const env = get().environment;
    const look = environmentLook(
      weather ?? env.weather ?? 'clear',
      timeOfDay ?? env.timeOfDay ?? get().timeOfDay ?? 'day',
      atmosphere ?? env.atmosphere ?? 'neutral',
    );
    record();
    set((s) => ({
      environment: { ...s.environment, ...look },
      timeOfDay: look.timeOfDay ?? s.timeOfDay,
    }));
    persist(snapshot(get));
  },

  applyScenePreset: (presetId) => {
    const preset = SCENE_PRESETS.find((p) => p.id === presetId);
    if (!preset) return;
    record();
    preset.items.forEach((item) => {
      get().addFromCatalog(item.id, item.position);
    });
  },

  applyAction: (actionId, objectId) => {
    const action = DIRECTOR_ACTIONS.find((a) => a.id === actionId);
    if (!action) return;
    const targetId = objectId || get().objects.find((o) => o.characterId)?.id;
    if (!targetId) return;
    get().updateObject(targetId, {
      animation: action.clip,
      pose: action.pose ?? 'stand',
      animationPlaying: action.clip !== 'sit',
    });
  },

  applyAdvice: (id) => {
    if (id === 'dialogue' || id === 'too-far') get().applyBlocking('dialogue');
    if (id === 'medium' || id === 'tight-two') get().applyShotFraming('medium', 'eye');
    if (id === 'lookat' || id === 'cam-far') {
      const lead = get().objects.find((o) => o.characterId);
      if (lead) get().lookAt(get().activeCamera, [lead.position[0], lead.position[1] + 1.45, lead.position[2]]);
    }
    if (id === 'sidelight') {
      const has = get().objects.some((o) => o.catalogId === 'light_spot');
      if (!has) get().addFromCatalog('light_spot', [2.2, 2.4, 1.1]);
    }
  },

  applyAutoStage: (text) => {
    const plan = planAutoStage(text);
    record();
    if (plan.presetId) get().applyScenePreset(plan.presetId);
    get().applyEnvironmentLook(plan.weather, plan.timeOfDay, plan.atmosphere);
    const chars = get().objects.filter((o) => o.characterId);
    const missing = plan.needCharacters - chars.length;
    if (missing > 0) {
      const templates = ['human_male_young_01', 'human_female_young_01'];
      for (let i = 0; i < missing; i += 1) {
        get().addOfficialTemplate(templates[i % templates.length]);
      }
    }
    get().applyBlocking(plan.blocking);
    get().applyShotFraming(plan.shotSize, plan.angle);
    const nextChars = get().objects.filter((o) => o.characterId);
    if (nextChars[0]) get().applyAction(plan.action, nextChars[0].id);
    if (nextChars[0] && nextChars[1]) {
      get().setRelation(nextChars[0].id, nextChars[1].id, plan.relation);
    }
    get().setProjectMeta({ locationName: plan.locationName });
    get().updateShotMeta({
      sceneName: plan.locationName,
      shotDescription: text.trim(),
      emotion: plan.atmosphere,
      timeOfDay: plan.timeOfDay,
    });
    return plan.summary;
  },
  } as DirectorStore;
});
