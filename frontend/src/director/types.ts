/** 3D Director Desk — Scene State is the source of truth. Three.js only renders it. */

export type Vec3 = [number, number, number];

export type SceneObjectType =
  | 'character'
  | 'animal'
  | 'shape'
  | 'furniture'
  | 'architecture'
  | 'nature'
  | 'vehicle'
  | 'prop'
  | 'light'
  | 'effect'
  | 'primitive';

export type ShapeKind =
  | 'box'
  | 'sphere'
  | 'cylinder'
  | 'cone'
  | 'plane'
  | 'torus'
  | 'capsule'
  | 'pyramid'
  | 'ring'
  | 'dodecahedron'
  | 'icosahedron'
  | 'octahedron'
  | 'tetrahedron'
  | 'torusKnot'
  | 'human_male'
  | 'human_female'
  | 'human_child'
  | 'human_elder'
  | 'human_teen'
  | 'human_baby'
  | 'human_sit'
  | 'mannequin'
  | 'robot'
  | 'crowd'
  | 'dog'
  | 'cat'
  | 'bird'
  | 'horse'
  | 'rabbit'
  | 'cow'
  | 'sheep'
  | 'chicken'
  | 'fish'
  | 'snake'
  | 'deer'
  | 'bear'
  | 'table'
  | 'chair'
  | 'sofa'
  | 'bed'
  | 'lamp'
  | 'desk'
  | 'bookshelf'
  | 'cabinet'
  | 'stool'
  | 'bench'
  | 'fridge'
  | 'tvstand'
  | 'plantpot'
  | 'mirror'
  | 'wall'
  | 'door'
  | 'window'
  | 'column'
  | 'stairs'
  | 'fence'
  | 'floor'
  | 'roof'
  | 'house'
  | 'arch'
  | 'road'
  | 'streetlamp'
  | 'stage'
  | 'tent'
  | 'platform'
  | 'tree'
  | 'bush'
  | 'rock'
  | 'flower'
  | 'pine'
  | 'palm'
  | 'cactus'
  | 'grass'
  | 'mountain'
  | 'water'
  | 'cloud'
  | 'mushroom'
  | 'car'
  | 'bike'
  | 'truck'
  | 'bus'
  | 'motorcycle'
  | 'boat'
  | 'airplane'
  | 'crate'
  | 'barrel'
  | 'bottle'
  | 'book'
  | 'cup'
  | 'phone'
  | 'laptop'
  | 'bag'
  | 'suitcase'
  | 'plate'
  | 'vase'
  | 'trash'
  | 'sign'
  | 'ball'
  | 'camera_prop'
  | 'umbrella'
  | 'screen'
  | 'marker'
  | 'flag'
  | 'fire'
  | 'smoke'
  | 'hologram'
  | 'hemisphere'
  | 'tube'
  | 'star'
  | 'arrow'
  | 'roundedBox'
  | 'light_point'
  | 'light_spot'
  | 'light_directional'
  | 'light_area';

/** @deprecated use ShapeKind */
export type PrimitiveKind = ShapeKind;

export type TransformMode = 'translate' | 'rotate' | 'scale';

export type ViewMode = 'director' | 'shot' | 'final';

export type Weather = 'clear' | 'cloudy' | 'rain' | 'snow' | 'fog';
export type Atmosphere = 'neutral' | 'tense' | 'romantic' | 'oppressive' | 'joyful' | 'melancholy';
export type ShotSize = 'extreme_long' | 'long' | 'full' | 'medium' | 'close' | 'extreme_close';
export type CameraAngle = 'eye' | 'high' | 'low' | 'side';
export type CharacterRelationKind = 'ally' | 'hostile' | 'romantic' | 'stranger' | 'family';

export interface CharacterRelation {
  fromId: string;
  toId: string;
  kind: CharacterRelationKind;
}

export type AspectRatio = '9:16' | '16:9' | '1:1';

export interface ObjectMaterial {
  color: string;
  metalness: number;
  roughness: number;
  opacity: number;
  emissive: string;
}

export interface SceneObject {
  id: string;
  type: SceneObjectType;
  name: string;
  catalogId?: string;
  /** Independent character/animal asset. Scene only stores a reference. */
  characterId?: string | null;
  modelUrl: string | null;
  primitive?: ShapeKind;
  position: Vec3;
  rotation: Vec3;
  scale: Vec3;
  pose?: string | null;
  animation: string | null;
  animationPlaying?: boolean;
  animations: string[];
  /** Instance-only FK pose. Does not copy the Character Asset. */
  bonePose?: Record<string, [number, number, number]> | null;
  customAnimationId?: string | null;
  customAnimationTime?: number;
  customAnimationPlaying?: boolean;
  color: string;
  metalness: number;
  roughness: number;
  opacity: number;
  emissive: string;
  visible: boolean;
  locked: boolean;
  lightIntensity?: number;
}

export type CameraMotion =
  | 'static'
  | 'push_in'
  | 'pull_out'
  | 'pan'
  | 'tilt'
  | 'orbit'
  | 'tracking';

export interface SceneCamera {
  id: string;
  name: string;
  position: Vec3;
  rotation: Vec3;
  fov: number;
  target?: Vec3 | null;
  motion?: CameraMotion | null;
  focalLength?: number;
  shotSize?: ShotSize;
  angle?: CameraAngle;
}

export interface TimelineKey {
  id: string;
  time: number;
  objectId?: string;
  cameraId?: string;
  position?: Vec3;
  rotation?: Vec3;
  pose?: string | null;
  animation?: string | null;
}

export interface SceneTimeline {
  duration: number;
  keys: TimelineKey[];
}

export interface SceneEnvironment {
  sky: string;
  ambientIntensity: number;
  showGrid: boolean;
  weather?: Weather;
  timeOfDay?: string;
  atmosphere?: Atmosphere;
  backdropUrl?: string | null;
}

export interface DirectorSceneState {
  sceneId: string;
  sceneName?: string;
  version: 1;
  aspectRatio: AspectRatio;
  objects: SceneObject[];
  cameras: SceneCamera[];
  activeCamera: string;
  selectedId: string | null;
  transformMode: TransformMode;
  viewMode: ViewMode;
  environment: SceneEnvironment;
  shotDuration?: number;
  shotDescription?: string;
  timeline?: SceneTimeline;
  shotType?: string;
  cameraMovement?: string;
  emotion?: string;
  timeOfDay?: string;
  imagePrompt?: string;
  videoPrompt?: string;
  negativePrompt?: string;
  imageUrl?: string | null;
  videoUrl?: string | null;
  generationId?: string | null;
  currentGenerationId?: string | null;
  /** 3D 导演台发送到画布的构图参考 */
  compositionUrl?: string | null;
  canvasX?: number;
  canvasY?: number;
  projectName?: string;
  chapterName?: string;
  locationName?: string;
  relations?: CharacterRelation[];
}

export const DEFAULT_SHOT_CAMERA: SceneCamera = {
  id: 'camera_001',
  name: '机位1',
  position: [0, 1.6, 5],
  rotation: [0, 0, 0],
  fov: 45,
  shotSize: 'medium',
  angle: 'eye',
  focalLength: 35,
};

export const DEFAULT_ENVIRONMENT: SceneEnvironment = {
  sky: '#141428',
  ambientIntensity: 0.55,
  showGrid: true,
  weather: 'clear',
  timeOfDay: 'day',
  atmosphere: 'neutral',
  backdropUrl: null,
};

export const DEFAULT_MATERIAL: ObjectMaterial = {
  color: '#8892b0',
  metalness: 0.1,
  roughness: 0.65,
  opacity: 1,
  emissive: '#000000',
};

export function createEmptyScene(): DirectorSceneState {
  return {
    sceneId: `scene_${Date.now().toString(36)}`,
    sceneName: '镜头 1',
    version: 1,
    aspectRatio: '9:16',
    objects: [],
    cameras: [{ ...DEFAULT_SHOT_CAMERA }],
    activeCamera: DEFAULT_SHOT_CAMERA.id,
    selectedId: null,
    transformMode: 'translate',
    viewMode: 'director',
    environment: { ...DEFAULT_ENVIRONMENT },
    shotDuration: 4,
    shotDescription: '',
    timeline: { duration: 4, keys: [] },
    shotType: 'medium shot',
    cameraMovement: 'static',
    emotion: '',
    timeOfDay: '',
    imagePrompt: '',
    videoPrompt: '',
    negativePrompt: '',
    imageUrl: null,
    videoUrl: null,
    generationId: null,
    compositionUrl: null,
    canvasX: undefined,
    canvasY: undefined,
    projectName: '未命名项目',
    chapterName: '第1集',
    locationName: '',
    relations: [],
  };
}

export function lookAtRotation(from: Vec3, to: Vec3): Vec3 {
  const dx = to[0] - from[0];
  const dy = to[1] - from[1];
  const dz = to[2] - from[2];
  return [-Math.atan2(dy, Math.hypot(dx, dz)), Math.atan2(dx, dz), 0];
}

export function parseAspect(ratio: AspectRatio): number {
  if (ratio === '9:16') return 9 / 16;
  if (ratio === '1:1') return 1;
  return 16 / 9;
}

export function capturePixelSize(ratio: AspectRatio): { width: number; height: number } {
  if (ratio === '9:16') return { width: 720, height: 1280 };
  if (ratio === '1:1') return { width: 1080, height: 1080 };
  return { width: 1280, height: 720 };
}

export function newId(prefix: string): string {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export function normalizeObject(raw: Partial<SceneObject> & { id?: string; name?: string }): SceneObject {
  const src = raw && typeof raw === 'object' ? raw : {};
  const type = src.type ?? 'prop';
  return {
    id: src.id || newId('obj'),
    type,
    name: src.name || '物体',
    catalogId: src.catalogId,
    characterId: src.characterId ?? null,
    modelUrl: src.modelUrl ?? null,
    primitive: src.primitive ?? (type === 'character' ? 'capsule' : 'box'),
    position: Array.isArray(src.position) ? src.position : [0, 0, 0],
    rotation: Array.isArray(src.rotation) ? src.rotation : [0, 0, 0],
    scale: Array.isArray(src.scale) ? src.scale : [1, 1, 1],
    pose: src.pose ?? (src.characterId ? 'stand' : null),
    animation: src.animation ?? (src.characterId ? 'idle' : null),
    animationPlaying: src.animationPlaying !== false,
    animations: src.animations ?? [],
    bonePose: src.bonePose ?? null,
    customAnimationId: src.customAnimationId ?? null,
    customAnimationTime: src.customAnimationTime ?? 0,
    customAnimationPlaying: src.customAnimationPlaying === true,
    color: src.color ?? DEFAULT_MATERIAL.color,
    metalness: src.metalness ?? DEFAULT_MATERIAL.metalness,
    roughness: src.roughness ?? DEFAULT_MATERIAL.roughness,
    opacity: src.opacity ?? DEFAULT_MATERIAL.opacity,
    emissive: src.emissive ?? DEFAULT_MATERIAL.emissive,
    visible: src.visible !== false,
    locked: !!src.locked,
    lightIntensity: src.lightIntensity,
  };
}

export function normalizeCamera(raw: Partial<SceneCamera> & { id: string }): SceneCamera {
  return {
    id: raw.id,
    name: raw.name ?? '机位',
    position: raw.position ?? [...DEFAULT_SHOT_CAMERA.position],
    rotation: raw.rotation ?? [0, 0, 0],
    fov: raw.fov ?? 45,
    target: raw.target ?? null,
    motion: raw.motion ?? null,
    focalLength: raw.focalLength,
    shotSize: raw.shotSize,
    angle: raw.angle,
  };
}

export function normalizeScene(raw: Partial<DirectorSceneState>): DirectorSceneState {
  const empty = createEmptyScene();
  return {
    ...empty,
    ...raw,
    sceneName: raw.sceneName || empty.sceneName,
    version: 1,
    objects: (raw.objects ?? []).filter(Boolean).map((o) => normalizeObject(o)),
    cameras: (raw.cameras?.length ? raw.cameras : empty.cameras).map((c) => normalizeCamera(c)),
    environment: { ...DEFAULT_ENVIRONMENT, ...raw.environment },
    shotDuration: raw.shotDuration ?? empty.shotDuration,
    shotDescription: raw.shotDescription ?? '',
    timeline: raw.timeline ?? { duration: raw.shotDuration ?? 4, keys: [] },
    shotType: raw.shotType ?? empty.shotType,
    cameraMovement: raw.cameraMovement ?? empty.cameraMovement,
    emotion: raw.emotion ?? '',
    timeOfDay: raw.timeOfDay ?? '',
    imagePrompt: raw.imagePrompt ?? '',
    videoPrompt: raw.videoPrompt ?? '',
    negativePrompt: raw.negativePrompt ?? '',
    imageUrl: raw.imageUrl ?? null,
    videoUrl: raw.videoUrl ?? null,
    generationId: raw.generationId ?? raw.currentGenerationId ?? null,
    compositionUrl: raw.compositionUrl ?? null,
    canvasX: raw.canvasX,
    canvasY: raw.canvasY,
    projectName: raw.projectName ?? empty.projectName,
    chapterName: raw.chapterName ?? empty.chapterName,
    locationName: raw.locationName ?? '',
    relations: raw.relations ?? [],
  };
}
