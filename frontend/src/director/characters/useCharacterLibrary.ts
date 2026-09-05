import { create } from 'zustand';
import type {
  AgeGroup,
  BodyType,
  CharacterAppearance,
  CharacterAsset,
  CustomAnimation,
  SavedPose,
  SourceType,
} from './types';
import { DEFAULT_APPEARANCE, DEFAULT_MARKETPLACE, newAnimId, newCharacterId, newPoseId } from './types';
import { getTemplate } from './templates';
import { loadCharacterLibrary, saveCharacterLibrary } from './persistLibrary';
import { scheduleLibrarySync } from '../syncSchedule';

interface CharacterLibraryStore {
  characters: CharacterAsset[];
  favorites: string[];
  recentIds: string[];
  savedPoses: SavedPose[];
  customAnimations: CustomAnimation[];
  createFromTemplate: (templateId: string, name?: string) => CharacterAsset | null;
  createFromRiggedModel: (input: {
    name: string;
    modelUrl: string;
    sourceType: SourceType;
    skeletonType: CharacterAsset['skeletonType'];
    animationSetId: string;
    rigStatus: CharacterAsset['rigStatus'];
    animationStatus: CharacterAsset['animationStatus'];
    characterType?: CharacterAsset['characterType'];
    note?: string;
  }) => CharacterAsset;
  updateCharacter: (id: string, patch: Partial<Omit<CharacterAsset, 'id' | 'createdAt'>>) => void;
  updateAppearance: (id: string, patch: Partial<CharacterAppearance>) => void;
  setBody: (id: string, patch: { heightCm?: number; bodyType?: BodyType; ageGroup?: AgeGroup }) => void;
  rename: (id: string, name: string) => void;
  duplicate: (id: string) => CharacterAsset | null;
  remove: (id: string) => void;
  toggleFavorite: (id: string) => void;
  touchRecent: (id: string) => void;
  getById: (id: string) => CharacterAsset | undefined;
  savePose: (characterId: string, name: string, bones: SavedPose['bones']) => SavedPose;
  removePose: (poseId: string) => void;
  saveCustomAnimation: (anim: Omit<CustomAnimation, 'id' | 'createdAt' | 'updatedAt'> & { id?: string }) => CustomAnimation;
  removeCustomAnimation: (id: string) => void;
}

function persist(get: () => CharacterLibraryStore): void {
  const s = get();
  const state = {
    characters: s.characters,
    favorites: s.favorites,
    recentIds: s.recentIds,
    savedPoses: s.savedPoses,
    customAnimations: s.customAnimations,
  };
  saveCharacterLibrary(state);
  scheduleLibrarySync(state);
}

function syncAliases(asset: CharacterAsset): CharacterAsset {
  return {
    ...asset,
    kind: asset.characterType,
    gender: asset.body.gender,
    ageGroup: asset.body.ageGroup,
    heightCm: asset.body.heightCm,
    bodyType: asset.body.bodyType,
    skeletonId: asset.skeletonType,
    clothing: { outfitId: asset.appearance.outfitId, outfitColor: asset.appearance.outfitColor },
    accessories: { glassesVisible: asset.appearance.glassesVisible },
  };
}

const loaded = loadCharacterLibrary();

export const useCharacterLibrary = create<CharacterLibraryStore>((set, get) => ({
  characters: loaded.characters,
  favorites: loaded.favorites,
  recentIds: loaded.recentIds,
  savedPoses: loaded.savedPoses,
  customAnimations: loaded.customAnimations,

  getById: (id) => get().characters.find((c) => c.id === id),

  createFromTemplate: (templateId, name) => {
    const template = getTemplate(templateId);
    if (!template || !template.available) return null;
    const now = Date.now();
    const prefix = template.characterType === 'animal'
      ? template.species[0].toUpperCase() + template.species.slice(1)
      : 'Character';
    const asset = syncAliases({
      id: newCharacterId(prefix),
      name: name?.trim() || template.name,
      characterType: template.characterType,
      sourceType: 'official',
      species: template.species,
      templateId: template.id,
      modelUrl: template.modelUrl,
      thumbnailUrl: template.thumbnailUrl,
      skeletonType: template.skeletonType,
      rigStatus: 'ready',
      animationStatus: 'ready',
      animationSetId: template.animationSetId,
      appearance: { ...template.appearance },
      body: {
        heightCm: template.heightCm,
        bodyType: template.bodyType,
        ageGroup: template.ageGroup,
        gender: template.gender,
      },
      clothing: { outfitId: template.appearance.outfitId, outfitColor: template.appearance.outfitColor },
      accessories: { glassesVisible: template.appearance.glassesVisible },
      defaultPose: 'stand',
      defaultBonePose: null,
      createdAt: now,
      updatedAt: now,
      ownerId: null,
      marketplace: { ...DEFAULT_MARKETPLACE },
      note: template.note,
      kind: template.characterType,
      gender: template.gender,
      ageGroup: template.ageGroup,
      heightCm: template.heightCm,
      bodyType: template.bodyType,
      skeletonId: template.skeletonType,
    });
    set((s) => ({ characters: [...s.characters, asset], recentIds: [asset.id, ...s.recentIds.filter((id) => id !== asset.id)].slice(0, 12) }));
    persist(get);
    return asset;
  },

  createFromRiggedModel: (input) => {
    const now = Date.now();
    const characterType = input.characterType ?? 'human';
    const asset = syncAliases({
      id: newCharacterId('Character'),
      name: input.name,
      characterType,
      sourceType: input.sourceType,
      species: characterType === 'animal' ? 'special' : characterType === 'special' ? 'special' : 'human',
      templateId: '',
      modelUrl: input.modelUrl,
      thumbnailUrl: null,
      skeletonType: input.skeletonType,
      rigStatus: input.rigStatus,
      animationStatus: input.animationStatus,
      animationSetId: input.animationSetId,
      appearance: { ...DEFAULT_APPEARANCE },
      body: { heightCm: 170, bodyType: 'regular', ageGroup: 'adult', gender: 'neutral' },
      clothing: { outfitId: '', outfitColor: '' },
      accessories: { glassesVisible: true },
      defaultPose: 'stand',
      defaultBonePose: null,
      createdAt: now,
      updatedAt: now,
      ownerId: null,
      marketplace: { ...DEFAULT_MARKETPLACE },
      note: input.note,
      kind: characterType,
      gender: 'neutral',
      ageGroup: 'adult',
      heightCm: 170,
      bodyType: 'regular',
      skeletonId: input.skeletonType,
    });
    set((s) => ({ characters: [...s.characters, asset], recentIds: [asset.id, ...s.recentIds].slice(0, 12) }));
    persist(get);
    return asset;
  },

  updateCharacter: (id, patch) => {
    set((s) => ({
      characters: s.characters.map((c) => (c.id === id ? syncAliases({ ...c, ...patch, updatedAt: Date.now() }) : c)),
    }));
    persist(get);
  },

  updateAppearance: (id, patch) => {
    set((s) => ({
      characters: s.characters.map((c) =>
        c.id === id ? syncAliases({ ...c, appearance: { ...c.appearance, ...patch }, updatedAt: Date.now() }) : c,
      ),
    }));
    persist(get);
  },

  setBody: (id, patch) => {
    set((s) => ({
      characters: s.characters.map((c) =>
        c.id === id
          ? syncAliases({
              ...c,
              body: { ...c.body, ...patch },
              heightCm: patch.heightCm ?? c.heightCm,
              bodyType: patch.bodyType ?? c.bodyType,
              ageGroup: patch.ageGroup ?? c.ageGroup,
              updatedAt: Date.now(),
            })
          : c,
      ),
    }));
    persist(get);
  },

  rename: (id, name) => get().updateCharacter(id, { name }),

  duplicate: (id) => {
    const src = get().getById(id);
    if (!src) return null;
    const copy = syncAliases({
      ...src,
      appearance: { ...src.appearance },
      body: { ...src.body },
      clothing: { ...src.clothing },
      accessories: { ...src.accessories },
      marketplace: { ...DEFAULT_MARKETPLACE },
      id: newCharacterId(src.characterType === 'animal' ? src.species : 'Character'),
      name: `${src.name} 副本`,
      sourceType: 'duplicated',
      createdAt: Date.now(),
      updatedAt: Date.now(),
    });
    set((s) => ({ characters: [...s.characters, copy] }));
    persist(get);
    return copy;
  },

  remove: (id) => {
    set((s) => ({
      characters: s.characters.filter((c) => c.id !== id),
      favorites: s.favorites.filter((f) => f !== id),
      recentIds: s.recentIds.filter((f) => f !== id),
      savedPoses: s.savedPoses.filter((p) => p.characterId !== id),
    }));
    persist(get);
  },

  toggleFavorite: (id) => {
    set((s) => ({
      favorites: s.favorites.includes(id) ? s.favorites.filter((f) => f !== id) : [...s.favorites, id],
    }));
    persist(get);
  },

  touchRecent: (id) => {
    set((s) => ({ recentIds: [id, ...s.recentIds.filter((x) => x !== id)].slice(0, 12) }));
    persist(get);
  },

  savePose: (characterId, name, bones) => {
    const pose: SavedPose = { id: newPoseId(), name, characterId, bones, createdAt: Date.now() };
    set((s) => ({ savedPoses: [...s.savedPoses, pose] }));
    persist(get);
    return pose;
  },

  removePose: (poseId) => {
    set((s) => ({ savedPoses: s.savedPoses.filter((p) => p.id !== poseId) }));
    persist(get);
  },

  saveCustomAnimation: (anim) => {
    const now = Date.now();
    const saved: CustomAnimation = {
      id: anim.id ?? newAnimId(),
      name: anim.name,
      characterId: anim.characterId,
      skeletonType: anim.skeletonType,
      duration: anim.duration,
      keys: anim.keys,
      createdAt: anim.id ? get().customAnimations.find((a) => a.id === anim.id)?.createdAt ?? now : now,
      updatedAt: now,
    };
    set((s) => ({
      customAnimations: s.customAnimations.some((a) => a.id === saved.id)
        ? s.customAnimations.map((a) => (a.id === saved.id ? saved : a))
        : [...s.customAnimations, saved],
    }));
    persist(get);
    return saved;
  },

  removeCustomAnimation: (id) => {
    set((s) => ({ customAnimations: s.customAnimations.filter((a) => a.id !== id) }));
    persist(get);
  },
}));
