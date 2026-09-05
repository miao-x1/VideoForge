export type CharacterType = 'human' | 'animal' | 'special';
export type CharacterKind = CharacterType;

export type SourceType = 'official' | 'ai_generated' | 'image_to_3d' | 'uploaded_3d' | 'duplicated';

export type Gender = 'male' | 'female' | 'neutral';

export type AgeGroup = 'child' | 'teen' | 'young' | 'adult' | 'middle' | 'elder';

export type BodyType = 'slim' | 'regular' | 'heavy';

export type Species =
  | 'human'
  | 'dog'
  | 'cat'
  | 'horse'
  | 'bird'
  | 'eagle'
  | 'wolf'
  | 'fox'
  | 'rabbit'
  | 'bear'
  | 'tiger'
  | 'lion'
  | 'monkey'
  | 'special';

export type SkeletonType =
  | 'rpm-masculine'
  | 'rpm-feminine'
  | 'mixamo'
  | 'quadruped'
  | 'avian'
  | 'embedded'
  | 'unknown'
  | 'none';

/** @deprecated use SkeletonType */
export type SkeletonId = SkeletonType;

export type RigStatus = 'none' | 'detected' | 'ready' | 'failed';

export type AnimationStatus = 'none' | 'ready' | 'partial' | 'failed';

export type PoseId =
  | 'stand'
  | 'sit'
  | 'walk'
  | 'run'
  | 'lie'
  | 'look_left'
  | 'look_right'
  | 'nod'
  | 'wave'
  | 'custom';

export type ClipId =
  | 'idle'
  | 'stand'
  | 'walk'
  | 'run'
  | 'sit'
  | 'stand_up'
  | 'turn'
  | 'look'
  | 'look_left'
  | 'look_right'
  | 'nod'
  | 'shake'
  | 'wave'
  | 'point'
  | 'talk'
  | 'phone'
  | 'pick_up'
  | 'put_down'
  | 'hug'
  | 'fight'
  | 'fall'
  | 'jump'
  | 'lie';

export type ClipKind = 'clip' | 'pose' | 'unavailable';

export interface CharacterAppearance {
  skinColor: string;
  hairColor: string;
  outfitColor: string;
  glassesVisible: boolean;
  hairStyleId: string;
  outfitId: string;
}

export interface CharacterBody {
  heightCm: number;
  bodyType: BodyType;
  ageGroup: AgeGroup;
  gender: Gender;
}

export interface CharacterClothing {
  outfitId: string;
  outfitColor: string;
}

export interface CharacterAccessories {
  glassesVisible: boolean;
}

export interface MarketplaceMeta {
  listed: boolean;
  visibility: 'private' | 'unlisted' | 'public';
  price: number | null;
}

export type BonePoseMap = Record<string, [number, number, number]>;

export interface SavedPose {
  id: string;
  name: string;
  characterId: string;
  bones: BonePoseMap;
  createdAt: number;
}

export interface CustomAnimationKey {
  time: number;
  bones: BonePoseMap;
}

export interface CustomAnimation {
  id: string;
  name: string;
  characterId: string | null;
  skeletonType: SkeletonType;
  duration: number;
  keys: CustomAnimationKey[];
  createdAt: number;
  updatedAt: number;
}

export interface CharacterAsset {
  id: string;
  name: string;
  characterType: CharacterType;
  sourceType: SourceType;
  species: Species;
  templateId: string;
  modelUrl: string;
  thumbnailUrl: string | null;
  skeletonType: SkeletonType;
  rigStatus: RigStatus;
  animationStatus: AnimationStatus;
  animationSetId: string;
  appearance: CharacterAppearance;
  body: CharacterBody;
  clothing: CharacterClothing;
  accessories: CharacterAccessories;
  defaultPose: PoseId;
  defaultBonePose: BonePoseMap | null;
  createdAt: number;
  updatedAt: number;
  ownerId: string | null;
  marketplace: MarketplaceMeta;
  note?: string;
  /** compat aliases used by existing UI */
  kind: CharacterType;
  gender: Gender;
  ageGroup: AgeGroup;
  heightCm: number;
  bodyType: BodyType;
  skeletonId: SkeletonType;
}

export interface CharacterTemplate {
  id: string;
  name: string;
  characterType: CharacterType;
  species: Species;
  gender: Gender;
  ageGroup: AgeGroup;
  heightCm: number;
  bodyType: BodyType;
  appearance: CharacterAppearance;
  modelUrl: string;
  thumbnailUrl: string | null;
  skeletonType: SkeletonType;
  animationSetId: string;
  defaultScale: [number, number, number];
  available: boolean;
  featured?: boolean;
  note?: string;
  kind: CharacterType;
  skeletonId: SkeletonType;
}

export const DEFAULT_APPEARANCE: CharacterAppearance = {
  skinColor: '',
  hairColor: '',
  outfitColor: '',
  glassesVisible: true,
  hairStyleId: '',
  outfitId: '',
};

export const DEFAULT_MARKETPLACE: MarketplaceMeta = {
  listed: false,
  visibility: 'private',
  price: null,
};

export function newCharacterId(prefix = 'Character'): string {
  const safe = prefix.replace(/[^A-Za-z]/g, '') || 'Character';
  return `${safe}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
}

export function newPoseId(): string {
  return `Pose_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 5)}`;
}

export function newAnimId(): string {
  return `Anim_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 5)}`;
}
