import type { CharacterAppearance, CharacterTemplate, Gender, AgeGroup, BodyType, SkeletonType, Species, CharacterType } from './types';
import { DEFAULT_APPEARANCE } from './types';

const HUMANS = '/director/models/humans';
const ANIMALS = '/director/models/animals';

function appearance(patch: Partial<CharacterAppearance> = {}): CharacterAppearance {
  return { ...DEFAULT_APPEARANCE, ...patch };
}

function official(partial: Omit<CharacterTemplate, 'kind' | 'skeletonId'> & { skeletonType: SkeletonType }): CharacterTemplate {
  return {
    ...partial,
    kind: partial.characterType,
    skeletonId: partial.skeletonType,
  };
}

function human(opts: {
  id: string;
  name: string;
  gender: Gender;
  ageGroup: AgeGroup;
  heightCm: number;
  bodyType?: BodyType;
  modelUrl: string;
  skeletonType: SkeletonType;
  animationSetId: string;
  scale?: [number, number, number];
  appearance?: Partial<CharacterAppearance>;
  featured?: boolean;
  note?: string;
}): CharacterTemplate {
  return official({
    id: opts.id,
    name: opts.name,
    characterType: 'human',
    species: 'human',
    gender: opts.gender,
    ageGroup: opts.ageGroup,
    heightCm: opts.heightCm,
    bodyType: opts.bodyType ?? 'regular',
    appearance: appearance(opts.appearance),
    modelUrl: opts.modelUrl,
    thumbnailUrl: null,
    skeletonType: opts.skeletonType,
    animationSetId: opts.animationSetId,
    defaultScale: opts.scale ?? [1, 1, 1],
    available: true,
    featured: opts.featured,
    note: opts.note,
  });
}

function animal(opts: {
  id: string;
  name: string;
  species: Species;
  heightCm: number;
  modelUrl: string;
  animationSetId: string;
  scale: [number, number, number];
  appearance?: Partial<CharacterAppearance>;
  featured?: boolean;
  note?: string;
}): CharacterTemplate {
  return official({
    id: opts.id,
    name: opts.name,
    characterType: 'animal',
    species: opts.species,
    gender: 'neutral',
    ageGroup: 'adult',
    heightCm: opts.heightCm,
    bodyType: 'regular',
    appearance: appearance(opts.appearance),
    modelUrl: opts.modelUrl,
    thumbnailUrl: null,
    skeletonType: opts.animationSetId === 'three-bird' ? 'avian' : 'quadruped',
    animationSetId: opts.animationSetId,
    defaultScale: opts.scale,
    available: true,
    featured: opts.featured,
    note: opts.note,
  });
}

function unavailable(opts: {
  id: string;
  name: string;
  characterType: CharacterType;
  species: Species;
  note: string;
}): CharacterTemplate {
  return official({
    id: opts.id,
    name: opts.name,
    characterType: opts.characterType,
    species: opts.species,
    gender: 'neutral',
    ageGroup: 'adult',
    heightCm: 100,
    bodyType: 'regular',
    appearance: appearance(),
    modelUrl: '',
    thumbnailUrl: null,
    skeletonType: 'none',
    animationSetId: 'none',
    defaultScale: [1, 1, 1],
    available: false,
    note: opts.note,
  });
}

export const CHARACTER_TEMPLATES: CharacterTemplate[] = [
  human({
    id: 'human_male_young_01',
    name: '青年男性 01',
    gender: 'male',
    ageGroup: 'young',
    heightCm: 172,
    bodyType: 'slim',
    modelUrl: `${HUMANS}/avatar.glb`,
    skeletonType: 'rpm-masculine',
    animationSetId: 'rpm-masculine',
    scale: [0.94, 0.94, 0.94],
    featured: true,
  }),
  human({
    id: 'human_male_adult_01',
    name: '成年男性 01',
    gender: 'male',
    ageGroup: 'adult',
    heightCm: 178,
    modelUrl: `${HUMANS}/soldier.glb`,
    skeletonType: 'mixamo',
    animationSetId: 'mixamo-soldier',
    featured: true,
  }),
  human({
    id: 'human_male_middle_01',
    name: '中年男性 01',
    gender: 'male',
    ageGroup: 'middle',
    heightCm: 176,
    bodyType: 'heavy',
    modelUrl: `${HUMANS}/soldier.glb`,
    skeletonType: 'mixamo',
    animationSetId: 'mixamo-soldier',
    appearance: { outfitColor: '#3d4a5c', hairColor: '#4a3b2a' },
    scale: [1.02, 0.98, 1.04],
  }),
  human({
    id: 'human_male_elder_01',
    name: '老年男性 01',
    gender: 'male',
    ageGroup: 'elder',
    heightCm: 170,
    modelUrl: `${HUMANS}/soldier.glb`,
    skeletonType: 'mixamo',
    animationSetId: 'mixamo-soldier',
    appearance: { hairColor: '#c0c0c0' },
    scale: [0.97, 0.94, 0.97],
  }),
  human({
    id: 'human_male_teen_01',
    name: '少年 01',
    gender: 'male',
    ageGroup: 'teen',
    heightCm: 160,
    bodyType: 'slim',
    modelUrl: `${HUMANS}/avatar.glb`,
    skeletonType: 'rpm-masculine',
    animationSetId: 'rpm-masculine',
    scale: [0.86, 0.86, 0.86],
  }),
  human({
    id: 'human_female_young_01',
    name: '青年女性 01',
    gender: 'female',
    ageGroup: 'young',
    heightCm: 160,
    bodyType: 'slim',
    modelUrl: `${HUMANS}/lyra.glb`,
    skeletonType: 'rpm-feminine',
    animationSetId: 'rpm-feminine',
    scale: [0.9, 0.9, 0.9],
    appearance: { hairStyleId: 'lyra' },
    featured: true,
  }),
  human({
    id: 'human_female_adult_01',
    name: '成年女性 01',
    gender: 'female',
    ageGroup: 'adult',
    heightCm: 168,
    modelUrl: `${HUMANS}/aurora.glb`,
    skeletonType: 'rpm-feminine',
    animationSetId: 'rpm-feminine',
    appearance: { hairStyleId: 'aurora' },
    featured: true,
  }),
  human({
    id: 'human_female_middle_01',
    name: '中年女性 01',
    gender: 'female',
    ageGroup: 'middle',
    heightCm: 164,
    modelUrl: `${HUMANS}/celeste.glb`,
    skeletonType: 'rpm-feminine',
    animationSetId: 'rpm-feminine',
    appearance: { hairStyleId: 'celeste', hairColor: '#5a4030' },
    scale: [0.98, 0.96, 0.98],
  }),
  human({
    id: 'human_female_elder_01',
    name: '老年女性 01',
    gender: 'female',
    ageGroup: 'elder',
    heightCm: 158,
    modelUrl: `${HUMANS}/celeste.glb`,
    skeletonType: 'rpm-feminine',
    animationSetId: 'rpm-feminine',
    appearance: { hairStyleId: 'celeste', hairColor: '#d9d9d9' },
    scale: [0.96, 0.93, 0.96],
  }),
  human({
    id: 'human_child_01',
    name: '儿童 01',
    gender: 'neutral',
    ageGroup: 'child',
    heightCm: 120,
    bodyType: 'slim',
    modelUrl: `${HUMANS}/xbot.glb`,
    skeletonType: 'mixamo',
    animationSetId: 'mixamo-xbot',
    scale: [0.62, 0.62, 0.62],
    note: '标准人形骨架缩放，用于儿童走位预演，不是写实儿童皮肤。',
  }),
  official({
    id: 'special_mannequin_01',
    name: '人体模型',
    characterType: 'special',
    species: 'special',
    gender: 'neutral',
    ageGroup: 'adult',
    heightCm: 175,
    bodyType: 'regular',
    appearance: appearance(),
    modelUrl: `${HUMANS}/xbot.glb`,
    thumbnailUrl: null,
    skeletonType: 'mixamo',
    animationSetId: 'mixamo-xbot',
    defaultScale: [1, 1, 1],
    available: true,
    note: '标准人形骨架，用于动作/走位预演。',
  }),

  animal({
    id: 'animal_wolf_01',
    name: '狼 01',
    species: 'wolf',
    heightCm: 80,
    modelUrl: `${ANIMALS}/fox.glb`,
    animationSetId: 'khronos-fox',
    scale: [0.02, 0.02, 0.02],
    featured: true,
    note: 'Khronos Fox：头、口鼻、耳、躯干、四肢、尾巴，含 Survey/Walk/Run。',
  }),
  animal({
    id: 'animal_fox_01',
    name: '狐狸 01',
    species: 'fox',
    heightCm: 45,
    modelUrl: `${ANIMALS}/fox.glb`,
    animationSetId: 'khronos-fox',
    scale: [0.016, 0.016, 0.016],
    appearance: { outfitColor: '#d2691e' },
    note: '与狼同一套 Animation Ready 网格，体型与着色区分。',
  }),
  animal({
    id: 'animal_horse_01',
    name: '马 01',
    species: 'horse',
    heightCm: 160,
    modelUrl: `${ANIMALS}/horse.glb`,
    animationSetId: 'three-horse',
    scale: [0.01, 0.01, 0.01],
    featured: true,
  }),
  animal({
    id: 'animal_bird_01',
    name: '鸟 01',
    species: 'bird',
    heightCm: 40,
    modelUrl: `${ANIMALS}/parrot.glb`,
    animationSetId: 'three-bird',
    scale: [0.01, 0.01, 0.01],
  }),
  animal({
    id: 'animal_flamingo_01',
    name: '火烈鸟 01',
    species: 'bird',
    heightCm: 110,
    modelUrl: `${ANIMALS}/flamingo.glb`,
    animationSetId: 'three-bird',
    scale: [0.01, 0.01, 0.01],
  }),
  animal({
    id: 'animal_stork_01',
    name: '鹳 01',
    species: 'eagle',
    heightCm: 100,
    modelUrl: `${ANIMALS}/stork.glb`,
    animationSetId: 'three-bird',
    scale: [0.01, 0.01, 0.01],
    note: '带骨骼飞行动画的鸟类网格，不是猛禽扫描件。',
  }),

  unavailable({ id: 'animal_dog_01', name: '狗', characterType: 'animal', species: 'dog', note: 'TODO：没有带骨骼的狗模型，不提供占位几何体。' }),
  unavailable({ id: 'animal_cat_01', name: '猫', characterType: 'animal', species: 'cat', note: 'TODO：没有带骨骼的猫模型。' }),
  unavailable({ id: 'animal_rabbit_01', name: '兔', characterType: 'animal', species: 'rabbit', note: 'TODO：bunny.gltf 无骨骼，不能作为 Animation Ready 角色。' }),
  unavailable({ id: 'animal_bear_01', name: '熊', characterType: 'animal', species: 'bear', note: 'TODO：未接入带骨骼的熊模型。' }),
  unavailable({ id: 'animal_tiger_01', name: '老虎', characterType: 'animal', species: 'tiger', note: 'TODO：未接入带骨骼的虎模型。' }),
  unavailable({ id: 'animal_lion_01', name: '狮子', characterType: 'animal', species: 'lion', note: 'TODO：未接入带骨骼的狮模型。' }),
  unavailable({ id: 'animal_monkey_01', name: '猴子', characterType: 'animal', species: 'monkey', note: 'TODO：未接入带骨骼的猴模型。' }),
  unavailable({ id: 'special_cartoon_01', name: '卡通角色', characterType: 'special', species: 'special', note: 'TODO：没有独立卡通骨骼资产。' }),
  unavailable({ id: 'special_chibi_01', name: 'Q版角色', characterType: 'special', species: 'special', note: 'TODO：没有 Q 版骨骼资产。' }),
  unavailable({ id: 'special_monster_01', name: '怪物', characterType: 'special', species: 'special', note: 'TODO：没有可用怪物骨骼资产。' }),
];

export const HAIR_STYLE_OPTIONS: Array<{ id: string; label: string; gender: 'female' | 'any'; modelUrl: string }> = [
  { id: 'aurora', label: '长发（Aurora）', gender: 'female', modelUrl: `${HUMANS}/aurora.glb` },
  { id: 'celeste', label: '卷发（Celeste）', gender: 'female', modelUrl: `${HUMANS}/celeste.glb` },
  { id: 'lyra', label: '短发（Lyra）', gender: 'female', modelUrl: `${HUMANS}/lyra.glb` },
];

export function getTemplate(id: string): CharacterTemplate | undefined {
  return CHARACTER_TEMPLATES.find((t) => t.id === id);
}

export function templatesByKind(kind: CharacterTemplate['characterType']): CharacterTemplate[] {
  return CHARACTER_TEMPLATES.filter((t) => t.characterType === kind);
}

export function officialReadyCount(): number {
  return CHARACTER_TEMPLATES.filter((t) => t.available).length;
}
