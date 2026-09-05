import { scopedStorageKey } from '../scope';
import type { CharacterAsset, CustomAnimation, SavedPose } from './types';
import { DEFAULT_APPEARANCE, DEFAULT_MARKETPLACE } from './types';

export const CHARACTER_LIB_KEY = 'wedeo-forge.director.characters.v2';

function characterLibKey(): string {
  return scopedStorageKey('characters.v2');
}

export interface CharacterLibraryState {
  characters: CharacterAsset[];
  favorites: string[];
  recentIds: string[];
  savedPoses: SavedPose[];
  customAnimations: CustomAnimation[];
}

export function loadCharacterLibrary(): CharacterLibraryState {
  try {
    const raw = localStorage.getItem(characterLibKey());
    if (!raw) return emptyLibrary();
    const parsed = JSON.parse(raw) as Partial<CharacterLibraryState> & { characters?: unknown[] };
    return {
      characters: (parsed.characters ?? []).map((c) => normalizeAsset(c as Partial<CharacterAsset> & { id: string; name: string })),
      favorites: parsed.favorites ?? [],
      recentIds: parsed.recentIds ?? [],
      savedPoses: parsed.savedPoses ?? [],
      customAnimations: parsed.customAnimations ?? [],
    };
  } catch {
    return emptyLibrary();
  }
}

export function saveCharacterLibrary(state: CharacterLibraryState): void {
  localStorage.setItem(characterLibKey(), JSON.stringify(state));
}

function emptyLibrary(): CharacterLibraryState {
  return { characters: [], favorites: [], recentIds: [], savedPoses: [], customAnimations: [] };
}

export function normalizeAsset(raw: Partial<CharacterAsset> & { id: string; name: string }): CharacterAsset {
  const characterType = raw.characterType ?? raw.kind ?? 'human';
  const gender = raw.body?.gender ?? raw.gender ?? 'neutral';
  const ageGroup = raw.body?.ageGroup ?? raw.ageGroup ?? 'adult';
  const heightCm = raw.body?.heightCm ?? raw.heightCm ?? 170;
  const bodyType = raw.body?.bodyType ?? raw.bodyType ?? 'regular';
  const skeletonType = raw.skeletonType ?? raw.skeletonId ?? 'embedded';
  const appearance = { ...DEFAULT_APPEARANCE, ...raw.appearance };
  return {
    id: raw.id,
    name: raw.name,
    characterType,
    sourceType: raw.sourceType ?? (raw.templateId ? 'official' : 'uploaded_3d'),
    species: raw.species ?? (characterType === 'animal' ? 'wolf' : characterType === 'special' ? 'special' : 'human'),
    templateId: raw.templateId ?? '',
    modelUrl: raw.modelUrl ?? '',
    thumbnailUrl: raw.thumbnailUrl ?? null,
    skeletonType,
    rigStatus: raw.rigStatus ?? (raw.modelUrl ? 'ready' : 'none'),
    animationStatus: raw.animationStatus ?? (raw.animationSetId && raw.animationSetId !== 'none' ? 'ready' : 'none'),
    animationSetId: raw.animationSetId ?? 'none',
    appearance,
    body: raw.body ?? { heightCm, bodyType, ageGroup, gender },
    clothing: raw.clothing ?? { outfitId: appearance.outfitId, outfitColor: appearance.outfitColor },
    accessories: raw.accessories ?? { glassesVisible: appearance.glassesVisible },
    defaultPose: raw.defaultPose ?? 'stand',
    defaultBonePose: raw.defaultBonePose ?? null,
    createdAt: raw.createdAt ?? Date.now(),
    updatedAt: raw.updatedAt ?? Date.now(),
    ownerId: raw.ownerId ?? null,
    marketplace: { ...DEFAULT_MARKETPLACE, ...raw.marketplace },
    note: raw.note,
    kind: characterType,
    gender,
    ageGroup,
    heightCm,
    bodyType,
    skeletonId: skeletonType,
  };
}
