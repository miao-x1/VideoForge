import { getCatalogItem } from '../catalog';
import { clipsForSet } from '../characters/animations';
import { getPosePreset } from '../characters/poses';
import { useCharacterLibrary } from '../characters/useCharacterLibrary';
import { SCENE_PRESETS } from '../scenePresets';
import { useDirectorStore } from '../store/useDirectorStore';
import type { CameraMotion, Vec3 } from '../types';
import type { AgentFocus, DirectorContext } from './context';
import { generatePromptFromContext, type PromptKind } from './prompts';

export interface ToolResult {
  ok: boolean;
  message: string;
  suggestion?: string;
  data?: Record<string, unknown>;
}

export interface ToolRuntime {
  focus: AgentFocus;
  setFocus: (patch: Partial<AgentFocus>) => void;
  lastCreatedCharacterId: string | null;
  setLastCreatedCharacterId: (id: string | null) => void;
  undoAgent: () => ToolResult;
  redoAgent: () => ToolResult;
}

const ALLOWED = new Set([
  'create_character',
  'add_character_to_scene',
  'remove_character_from_scene',
  'move_character',
  'rotate_character',
  'scale_character',
  'set_character_action',
  'set_character_pose',
  'set_character_expression',
  'create_scene',
  'rename_scene',
  'delete_scene',
  'add_prop',
  'remove_prop',
  'move_prop',
  'rotate_prop',
  'scale_prop',
  'change_environment',
  'place_room_preset',
  'create_camera',
  'select_camera',
  'move_camera',
  'rotate_camera',
  'set_camera_fov',
  'set_camera_target',
  'set_camera_motion',
  'set_camera_position',
  'set_camera_type',
  'create_shot',
  'delete_shot',
  'duplicate_shot',
  'update_shot',
  'set_shot_duration',
  'set_shot_description',
  'set_shot_camera',
  'set_shot_characters',
  'set_shot_action',
  'create_keyframe',
  'update_keyframe',
  'delete_keyframe',
  'set_animation_duration',
  'set_action_start',
  'set_action_end',
  'generate_prompt',
  'set_shot_type',
  'send_composition',
  'generate_image',
  'generate_video',
  'set_camera',
  'restore_generation',
  'update_storyboard',
  'update_timeline',
  'undo_last',
  'redo_last',
]);

const ACTION_CLIPS = new Set(['walk', 'run', 'idle', 'stand', 'talk', 'look', 'wave']);
const IMPLEMENTED_POSES = new Set(['stand', 'walk', 'run', 'sit', 'lie', 'look_left', 'look_right', 'nod', 'wave']);

function asVec3(value: unknown, fallback: Vec3 = [0, 0, 0]): Vec3 {
  if (Array.isArray(value) && value.length >= 3) {
    return [Number(value[0]) || 0, Number(value[1]) || 0, Number(value[2]) || 0];
  }
  if (value && typeof value === 'object') {
    const v = value as { x?: number; y?: number; z?: number };
    if (v.x !== undefined || v.y !== undefined || v.z !== undefined) {
      return [Number(v.x) || 0, Number(v.y) || 0, Number(v.z) || 0];
    }
  }
  return fallback;
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function lerp(a: Vec3, b: Vec3, t: number): Vec3 {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}

function dist(a: Vec3, b: Vec3) {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const dz = b[2] - a[2];
  return Math.hypot(dx, dy, dz);
}

async function tweenPosition(objectId: string, to: Vec3, ms: number) {
  const store = useDirectorStore.getState();
  const obj = store.objects.find((o) => o.id === objectId);
  if (!obj) return;
  const from = obj.position;
  const start = performance.now();
  await new Promise<void>((resolve) => {
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / ms);
      useDirectorStore.getState().patchObjectLive(objectId, { position: lerp(from, to, t) });
      if (t < 1) requestAnimationFrame(step);
      else resolve();
    };
    requestAnimationFrame(step);
  });
  useDirectorStore.getState().updateTransform(objectId, { position: to });
}

async function tweenCamera(cameraId: string, to: Vec3, ms: number) {
  const cam = useDirectorStore.getState().cameras.find((c) => c.id === cameraId);
  if (!cam) return;
  const from = cam.position;
  const start = performance.now();
  await new Promise<void>((resolve) => {
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / ms);
      useDirectorStore.getState().patchCameraLive(cameraId, { position: lerp(from, to, t) });
      if (t < 1) requestAnimationFrame(step);
      else resolve();
    };
    requestAnimationFrame(step);
  });
  useDirectorStore.getState().updateCamera(cameraId, { position: to });
}

function resolveCharacter(ref: unknown, runtime: ToolRuntime) {
  const store = useDirectorStore.getState();
  const lib = useCharacterLibrary.getState();
  const text = String(ref ?? '').trim();
  const objects = store.objects.filter((o) => o.characterId);

  const byInstance = store.objects.find((o) => o.id === text);
  if (byInstance?.characterId) return { instance: byInstance, assetId: byInstance.characterId };

  const byAsset = objects.find((o) => o.characterId === text);
  if (byAsset) return { instance: byAsset, assetId: byAsset.characterId! };

  const asset = lib.getById(text);
  if (asset) {
    const inst = objects.find((o) => o.characterId === asset.id);
    return { instance: inst ?? null, assetId: asset.id };
  }

  const aliases = ['女主角', '女主', '女生', '女孩', '__pending_female__'];
  if (!text || aliases.includes(text) || /女/.test(text)) {
    const named = objects.find((o) => /女/.test(o.name));
    if (named) return { instance: named, assetId: named.characterId! };
    const libHit = lib.characters.find((c) => /女/.test(c.name) || c.templateId?.includes('female'));
    if (libHit) {
      const inst = objects.find((o) => o.characterId === libHit.id);
      return { instance: inst ?? null, assetId: libHit.id };
    }
  }
  if (/男/.test(text)) {
    const named = objects.find((o) => /男/.test(o.name));
    if (named) return { instance: named, assetId: named.characterId! };
  }

  if (runtime.focus.character_id) {
    const inst = objects.find((o) => o.characterId === runtime.focus.character_id || o.id === runtime.focus.character_id);
    if (inst) return { instance: inst, assetId: inst.characterId! };
    if (lib.getById(runtime.focus.character_id)) {
      return { instance: null, assetId: runtime.focus.character_id };
    }
  }
  if (runtime.lastCreatedCharacterId) {
    const inst = objects.find((o) => o.characterId === runtime.lastCreatedCharacterId);
    if (inst) return { instance: inst, assetId: runtime.lastCreatedCharacterId };
    return { instance: null, assetId: runtime.lastCreatedCharacterId };
  }
  if (objects.length === 1) return { instance: objects[0], assetId: objects[0].characterId! };
  return { instance: null, assetId: null };
}

function resolveProp(ref: unknown, catalogHint?: string) {
  const store = useDirectorStore.getState();
  const text = String(ref ?? catalogHint ?? '');
  const byId = store.objects.find((o) => o.id === text);
  if (byId) return byId;
  const catalog = catalogHint || text;
  const byCatalog = store.objects.find((o) => o.catalogId === catalog || o.primitive === catalog);
  if (byCatalog) return byCatalog;
  const names: Record<string, string[]> = {
    table: ['桌子', '桌'],
    sofa: ['沙发'],
    chair: ['椅子', '椅'],
    door: ['门'],
  };
  for (const [id, aliases] of Object.entries(names)) {
    if (catalog === id || aliases.some((a) => text.includes(a))) {
      return store.objects.find((o) => o.catalogId === id || aliases.some((a) => o.name.includes(a))) ?? null;
    }
  }
  return store.objects.find((o) => o.name.includes(text)) ?? null;
}

function beside(obj: { position: Vec3 } | null, offset: Vec3 = [0.75, 0, 0.1]): Vec3 {
  if (!obj) return [0.75, 0, 0.15];
  return [obj.position[0] + offset[0], obj.position[1] + offset[1], obj.position[2] + offset[2]];
}

function fail(message: string, suggestion?: string): ToolResult {
  return { ok: false, message, suggestion };
}

function ok(message: string, data?: Record<string, unknown>): ToolResult {
  return { ok: true, message, data };
}

async function ensureProp(catalogId: string, position?: Vec3) {
  const existing = resolveProp(catalogId, catalogId);
  if (existing) return existing;
  if (!getCatalogItem(catalogId)) return null;
  const id = useDirectorStore.getState().addFromCatalog(catalogId, position);
  if (!id) return null;
  return useDirectorStore.getState().objects.find((o) => o.id === id) ?? null;
}

export async function executeTool(
  name: string,
  args: Record<string, unknown>,
  runtime: ToolRuntime,
  ctx: DirectorContext,
): Promise<ToolResult> {
  if (!ALLOWED.has(name)) {
    return fail(`拒绝未注册 Tool：${name}`, 'Agent 只能调用白名单 Tool。');
  }
  switch (name) {
    case 'create_character':
      return createCharacter(args, runtime);
    case 'add_character_to_scene':
      return addCharacterToScene(args, runtime);
    case 'remove_character_from_scene':
      return removeCharacter(args, runtime);
    case 'move_character':
      return moveCharacter(args, runtime);
    case 'rotate_character':
      return rotateCharacter(args, runtime);
    case 'scale_character':
      return scaleCharacter(args, runtime);
    case 'set_character_action':
      return setCharacterAction(args, runtime);
    case 'set_character_pose':
      return setCharacterPose(args, runtime);
    case 'set_character_expression':
      return fail('当前角色系统没有独立表情通道。', '请用 Pose（点头/看左/看右）或说话动作代替。');
    case 'create_scene':
      return createScene(args);
    case 'rename_scene':
      return renameScene(args);
    case 'delete_scene':
      return deleteScene(args);
    case 'add_prop':
      return addProp(args);
    case 'remove_prop':
      return removeProp(args);
    case 'move_prop':
    case 'rotate_prop':
    case 'scale_prop':
      return transformProp(name, args);
    case 'change_environment':
      return changeEnvironment(args);
    case 'place_room_preset':
      return placeRoomPreset(args);
    case 'create_camera':
      return createCamera();
    case 'select_camera':
      return selectCamera(args);
    case 'move_camera':
    case 'set_camera_position':
      return moveCamera(args);
    case 'rotate_camera':
      return rotateCamera(args);
    case 'set_camera_fov':
      return setCameraFov(args);
    case 'set_camera_target':
      return setCameraTarget(args, runtime);
    case 'set_camera_motion':
      return setCameraMotion(args, runtime);
    case 'set_camera_type':
      return fail('当前只有透视机位，没有机位类型可切换。', '可用推进/拉远/对准来改变构图。');
    case 'create_shot':
      return createShot(args);
    case 'delete_shot':
      return deleteShot(args);
    case 'duplicate_shot':
      return duplicateShot();
    case 'update_shot':
    case 'set_shot_duration':
    case 'set_shot_description':
      return updateShot(args);
    case 'set_shot_camera':
      return selectCamera(args);
    case 'set_shot_characters':
      return addCharacterToScene(args, runtime);
    case 'set_shot_action':
      return setCharacterAction(args, runtime);
    case 'create_keyframe':
      return createKeyframe(args, runtime);
    case 'update_keyframe':
      return updateKeyframe(args);
    case 'delete_keyframe':
      return deleteKeyframe(args);
    case 'set_animation_duration':
    case 'set_action_start':
    case 'set_action_end':
      return setTimelineMeta(name, args);
    case 'generate_prompt':
      return generatePrompt(args, ctx);
    case 'set_shot_type':
      return setShotType(args);
    case 'send_composition':
      return sendComposition();
    case 'generate_image':
      return generateImage(args, ctx);
    case 'generate_video':
      return generateVideo(args, ctx);
    case 'set_camera':
      return setCamera(args, runtime);
    case 'restore_generation':
      return restoreGenerationTool(args);
    case 'update_storyboard':
      return updateShot({ description: args.description ?? args.storyboard });
    case 'update_timeline':
      return setTimelineMeta('update_timeline', args);
    case 'undo_last':
      return undoLast(runtime);
    case 'redo_last':
      return redoLast(runtime);
    default:
      return fail(`Tool ${name} 尚未实现`);
  }
}

function createCharacter(args: Record<string, unknown>, runtime: ToolRuntime): ToolResult {
  const template = String(args.template_id || args.source || 'human_female_young_01');
  const name = String(args.name || (template.includes('female') ? '女主角' : '角色'));
  const add = args.add_to_scene !== false;
  const store = useDirectorStore.getState();
  const lib = useCharacterLibrary.getState();
  const existing = lib.characters.find((c) => c.name === name && c.templateId === template);
  let instanceId: string | null = null;
  let assetId: string | null = existing?.id ?? null;
  if (existing && add) {
    const already = store.objects.find((o) => o.characterId === existing.id);
    if (already) {
      runtime.setFocus({ character_id: existing.id, object_id: already.id });
      runtime.setLastCreatedCharacterId(existing.id);
      return ok(`角色「${name}」已在当前分镜中`, { character_id: existing.id, object_id: already.id });
    }
    instanceId = store.instanceCharacter(existing.id);
  } else if (add) {
    instanceId = store.createCharacterFromTemplate(template, name);
    const obj = store.objects.find((o) => o.id === instanceId);
    assetId = obj?.characterId ?? lib.characters.find((c) => c.name === name)?.id ?? null;
  } else {
    const asset = lib.createFromTemplate(template, name);
    assetId = asset?.id ?? null;
  }
  if (!assetId && !instanceId) return fail('创建角色失败：官方模板不可用。');
  const obj = instanceId ? useDirectorStore.getState().objects.find((o) => o.id === instanceId) : null;
  const cid = obj?.characterId ?? assetId;
  runtime.setLastCreatedCharacterId(cid);
  runtime.setFocus({ character_id: cid, object_id: obj?.id ?? null });
  if (obj) useDirectorStore.getState().selectObject(obj.id);
  return ok(add ? `已创建「${name}」并加入当前分镜` : `已创建角色资产「${name}」`, {
    character_id: cid,
    object_id: obj?.id ?? null,
  });
}

function addCharacterToScene(args: Record<string, unknown>, runtime: ToolRuntime): ToolResult {
  const hit = resolveCharacter(args.character_id ?? args.character_ref, runtime);
  if (!hit.assetId) return fail('没有可加入的角色。', '请先创建角色，或说明角色名称。');
  const store = useDirectorStore.getState();
  if (hit.instance) {
    runtime.setFocus({ character_id: hit.assetId, object_id: hit.instance.id });
    return ok(`「${hit.instance.name}」已在当前分镜中`, { object_id: hit.instance.id, character_id: hit.assetId });
  }
  const id = store.instanceCharacter(hit.assetId);
  if (!id) return fail('加入分镜失败：角色资产不存在。');
  runtime.setFocus({ character_id: hit.assetId, object_id: id });
  store.selectObject(id);
  return ok('已把角色加入当前分镜', { object_id: id, character_id: hit.assetId });
}

function removeCharacter(args: Record<string, unknown>, runtime: ToolRuntime): ToolResult {
  const hit = resolveCharacter(args.character_id ?? args.character_ref, runtime);
  if (!hit.instance) return fail('当前分镜里没有这个角色。');
  useDirectorStore.getState().removeObject(hit.instance.id);
  return ok(`已从分镜移除「${hit.instance.name}」`);
}

async function moveCharacter(args: Record<string, unknown>, runtime: ToolRuntime): Promise<ToolResult> {
  let hit = resolveCharacter(args.character_id ?? args.character_ref, runtime);
  if (!hit.instance && hit.assetId) {
    const id = useDirectorStore.getState().instanceCharacter(hit.assetId);
    if (id) hit = { instance: useDirectorStore.getState().objects.find((o) => o.id === id) ?? null, assetId: hit.assetId };
  }
  if (!hit.instance) return fail('找不到要移动的角色。', '请先创建或加入角色。');

  let target: Vec3 | null = null;
  if (args.near) {
    const prop = await ensureProp(String(args.near), String(args.near) === 'sofa' ? [0, 0, 1.15] : [0, 0, 0.15]);
    if (!prop) return fail(`找不到目标「${args.near}」，目录里也没有该物件。`);
    target = beside(prop);
  } else if (args.position !== undefined) {
    if (args.position === '__table_beside__') {
      const table = await ensureProp('table', [0, 0, 0.15]);
      target = beside(table);
    } else if (args.position === '__sofa_beside__') {
      const sofa = await ensureProp('sofa', [0, 0, 1.15]);
      target = beside(sofa);
    } else {
      target = asVec3(args.position, hit.instance.position);
    }
  }
  if (!target) return fail('没有目标位置。');

  const animate = args.animate === true || args.animate === 'walk';
  if (animate) {
    const clipOk = applyAction(hit.instance.id, 'walk');
    if (!clipOk.ok) return clipOk;
    await tweenPosition(hit.instance.id, target, 1400);
  } else {
    useDirectorStore.getState().updateTransform(hit.instance.id, { position: target });
  }
  runtime.setFocus({ character_id: hit.assetId, object_id: hit.instance.id });
  return ok(`已把「${hit.instance.name}」移到 (${target.map((n) => n.toFixed(2)).join(', ')})`, {
    object_id: hit.instance.id,
    position: target,
  });
}

function rotateCharacter(args: Record<string, unknown>, runtime: ToolRuntime): ToolResult {
  const hit = resolveCharacter(args.character_id ?? args.character_ref, runtime);
  if (!hit.instance) return fail('找不到要旋转的角色。');
  useDirectorStore.getState().updateTransform(hit.instance.id, { rotation: asVec3(args.rotation, hit.instance.rotation) });
  return ok(`已旋转「${hit.instance.name}」`);
}

function scaleCharacter(args: Record<string, unknown>, runtime: ToolRuntime): ToolResult {
  const hit = resolveCharacter(args.character_id ?? args.character_ref, runtime);
  if (!hit.instance) return fail('找不到要缩放的角色。');
  useDirectorStore.getState().updateTransform(hit.instance.id, { scale: asVec3(args.scale, hit.instance.scale) });
  return ok(`已缩放「${hit.instance.name}」`);
}

function applyAction(instanceId: string, action: string): ToolResult {
  const store = useDirectorStore.getState();
  const obj = store.objects.find((o) => o.id === instanceId);
  if (!obj?.characterId) return fail('目标不是角色。');
  const asset = useCharacterLibrary.getState().getById(obj.characterId);
  if (!asset) return fail('角色资产丢失。');
  const mapped = action === 'stand' ? 'idle' : action;
  if (mapped === 'sit') return setPoseOn(instanceId, 'sit');
  const clip = clipsForSet(asset.animationSetId, asset.skeletonType).find((c) => c.id === mapped);
  if (!clip || !clip.implemented || clip.kind === 'unavailable') {
    return fail(`当前角色没有可用的 ${action} 动画。`, '请先给该角色绑定已实现的动画（walk / run / talk）。');
  }
  if (clip.kind === 'pose' && clip.poseId) return setPoseOn(instanceId, clip.poseId);
  store.updateObject(instanceId, {
    animation: mapped,
    pose: mapped === 'walk' || mapped === 'run' ? mapped : 'stand',
    animationPlaying: true,
    bonePose: null,
    customAnimationId: null,
  });
  return ok(`已设置动作 ${mapped}`, { action: mapped });
}

function setCharacterAction(args: Record<string, unknown>, runtime: ToolRuntime): ToolResult {
  const hit = resolveCharacter(args.character_id ?? args.character_ref, runtime);
  if (!hit.instance) return fail('找不到角色，无法设置动作。');
  const action = String(args.action || 'walk').toLowerCase();
  if (action === 'fight' || action === 'jump') {
    return applyAction(hit.instance.id, action);
  }
  if (!ACTION_CLIPS.has(action) && action !== 'sit' && action !== 'wave') {
    return fail(`不支持的动作：${action}`, '当前可用：walk / run / idle / talk / sit / wave。');
  }
  return applyAction(hit.instance.id, action);
}

function setPoseOn(instanceId: string, poseId: string): ToolResult {
  if (!IMPLEMENTED_POSES.has(poseId)) {
    return fail(`姿势 ${poseId} 未实现。`, '可用：stand / sit / lie / wave / nod / look_left / look_right。');
  }
  const preset = getPosePreset(poseId);
  const store = useDirectorStore.getState();
  if (preset?.kind === 'clip') {
    store.updateObject(instanceId, {
      pose: poseId,
      animation: preset.clipId,
      animationPlaying: true,
      bonePose: null,
      customAnimationId: null,
    });
  } else {
    store.updateObject(instanceId, {
      pose: poseId,
      animation: null,
      animationPlaying: false,
      bonePose: preset?.bones ?? null,
      customAnimationId: null,
    });
  }
  return ok(`已设置姿势 ${poseId}`, { pose: poseId });
}

function setCharacterPose(args: Record<string, unknown>, runtime: ToolRuntime): ToolResult {
  const hit = resolveCharacter(args.character_id ?? args.character_ref, runtime);
  if (!hit.instance) return fail('找不到角色，无法设置 Pose。');
  return setPoseOn(hit.instance.id, String(args.pose || 'sit'));
}

function createScene(args: Record<string, unknown>): ToolResult {
  const name = String(args.name || '').trim();
  const id = useDirectorStore.getState().createShotScene(name || undefined);
  if (args.preset) placeRoomPreset({ preset: args.preset });
  return ok(`已创建分镜「${useDirectorStore.getState().sceneName}」`, { scene_id: id });
}

function renameScene(args: Record<string, unknown>): ToolResult {
  const store = useDirectorStore.getState();
  const id = String(args.scene_id || store.sceneId);
  const name = String(args.name || '').trim();
  if (!name) return fail('缺少新名称。');
  store.renameScene(id, name);
  return ok(`已重命名为「${name}」`);
}

function deleteScene(args: Record<string, unknown>): ToolResult {
  const store = useDirectorStore.getState();
  if (store.scenes.length <= 1) return fail('只剩一个分镜，不能删除。');
  const id = String(args.scene_id || store.sceneId);
  store.deleteScene(id);
  return ok('已删除分镜');
}

function addProp(args: Record<string, unknown>): ToolResult {
  const catalogId = String(args.catalog_id || args.prop || 'table');
  if (!getCatalogItem(catalogId)) return fail(`目录里没有「${catalogId}」。`);
  const position = args.position ? asVec3(args.position) : undefined;
  const id = useDirectorStore.getState().addFromCatalog(catalogId, position);
  if (!id) return fail('添加物件失败。');
  return ok(`已添加「${getCatalogItem(catalogId)?.name}」`, { object_id: id });
}

function removeProp(args: Record<string, unknown>): ToolResult {
  const obj = resolveProp(args.object_id ?? args.prop);
  if (!obj) return fail('找不到要删除的物件。');
  useDirectorStore.getState().removeObject(obj.id);
  return ok(`已删除「${obj.name}」`);
}

function transformProp(name: string, args: Record<string, unknown>): ToolResult {
  const obj = resolveProp(args.object_id ?? args.prop);
  if (!obj) return fail('找不到物件。');
  if (name === 'move_prop') useDirectorStore.getState().updateTransform(obj.id, { position: asVec3(args.position, obj.position) });
  if (name === 'rotate_prop') useDirectorStore.getState().updateTransform(obj.id, { rotation: asVec3(args.rotation, obj.rotation) });
  if (name === 'scale_prop') useDirectorStore.getState().updateTransform(obj.id, { scale: asVec3(args.scale, obj.scale) });
  return ok(`已更新「${obj.name}」`);
}

function changeEnvironment(args: Record<string, unknown>): ToolResult {
  const patch: Record<string, unknown> = {};
  if (args.sky) patch.sky = String(args.sky);
  if (args.ambientIntensity !== undefined) patch.ambientIntensity = Number(args.ambientIntensity);
  if (args.showGrid !== undefined) patch.showGrid = Boolean(args.showGrid);
  useDirectorStore.getState().setEnvironment(patch);
  return ok('已更新环境');
}

function placeRoomPreset(args: Record<string, unknown>): ToolResult {
  const presetId = String(args.preset || 'room');
  const preset = SCENE_PRESETS.find((p) => p.id === presetId) ?? SCENE_PRESETS[0];
  const store = useDirectorStore.getState();
  const added: string[] = [];
  for (const item of preset.items) {
    const exists = store.objects.some((o) => o.catalogId === item.id);
    if (exists) continue;
    const id = store.addFromCatalog(item.id, item.position);
    if (id) added.push(id);
  }
  return ok(added.length ? `已布置「${preset.name}」` : `「${preset.name}」已在场景中`, { added });
}

function createCamera(): ToolResult {
  const id = useDirectorStore.getState().addCamera();
  return ok('已添加机位', { camera_id: id });
}

function selectCamera(args: Record<string, unknown>): ToolResult {
  const store = useDirectorStore.getState();
  const id = String(args.camera_id || store.activeCamera);
  const cam = store.cameras.find((c) => c.id === id);
  if (!cam) return fail('找不到机位。');
  store.selectCamera(id);
  store.setViewMode('shot');
  return ok(`已切到「${cam.name}」机位视角`);
}

function moveCamera(args: Record<string, unknown>): ToolResult {
  const store = useDirectorStore.getState();
  const id = String(args.camera_id || store.activeCamera);
  const cam = store.cameras.find((c) => c.id === id);
  if (!cam) return fail('找不到机位。');
  store.updateCamera(id, { position: asVec3(args.position, cam.position) });
  return ok('已移动机位');
}

function rotateCamera(args: Record<string, unknown>): ToolResult {
  const store = useDirectorStore.getState();
  const id = String(args.camera_id || store.activeCamera);
  const cam = store.cameras.find((c) => c.id === id);
  if (!cam) return fail('找不到机位。');
  store.updateCamera(id, { rotation: asVec3(args.rotation, cam.rotation) });
  return ok('已旋转机位');
}

function setCameraFov(args: Record<string, unknown>): ToolResult {
  const store = useDirectorStore.getState();
  const id = String(args.camera_id || store.activeCamera);
  store.updateCamera(id, { fov: Number(args.fov) || 45 });
  return ok(`已设置焦距 ${Number(args.fov) || 45}`);
}

function setCameraTarget(args: Record<string, unknown>, runtime: ToolRuntime): ToolResult {
  const store = useDirectorStore.getState();
  const camId = String(args.camera_id || store.activeCamera);
  const hit = resolveCharacter(args.target_ref ?? args.character_ref, runtime);
  const target = hit.instance
    ? [hit.instance.position[0], hit.instance.position[1] + 1.3, hit.instance.position[2]] as Vec3
    : asVec3(args.target, [0, 1.2, 0]);
  store.lookAt(camId, target);
  store.setViewMode('shot');
  return ok(hit.instance ? `摄像机已对准「${hit.instance.name}」` : '摄像机已对准目标', { target });
}

async function setCameraMotion(args: Record<string, unknown>, runtime: ToolRuntime): Promise<ToolResult> {
  const store = useDirectorStore.getState();
  const camId = String(args.camera_id || store.activeCamera);
  const cam = store.cameras.find((c) => c.id === camId);
  if (!cam) return fail('找不到机位。');
  const motion = String(args.motion || 'push_in') as CameraMotion;
  const amount = Number(args.amount) || 1.4;
  const hit = resolveCharacter(args.target_ref ?? args.character_ref, runtime);
  const look = (cam.target as Vec3 | null | undefined)
    ?? (hit.instance ? [hit.instance.position[0], hit.instance.position[1] + 1.3, hit.instance.position[2]] as Vec3 : [0, 1.2, 0]);
  let next: Vec3 = [...cam.position];
  const d = dist(cam.position, look) || 1;
  const dir: Vec3 = [
    (look[0] - cam.position[0]) / d,
    (look[1] - cam.position[1]) / d,
    (look[2] - cam.position[2]) / d,
  ];
  if (motion === 'push_in') {
    const remain = Math.max(0.7, d - amount);
    next = [look[0] - dir[0] * remain, look[1] - dir[1] * remain, look[2] - dir[2] * remain];
  } else if (motion === 'pull_out') {
    const remain = d + amount;
    next = [look[0] - dir[0] * remain, look[1] - dir[1] * remain, look[2] - dir[2] * remain];
  } else if (motion === 'pan') {
    next = [cam.position[0] + amount, cam.position[1], cam.position[2]];
  } else if (motion === 'tilt') {
    store.updateCamera(camId, { rotation: [cam.rotation[0] + 0.15, cam.rotation[1], cam.rotation[2]], motion });
    store.setViewMode('shot');
    return ok('已倾斜机位');
  } else if (motion === 'orbit') {
    const radius = d;
    const angle = 0.45;
    const x = look[0] + Math.sin(angle) * radius;
    const z = look[2] + Math.cos(angle) * radius;
    next = [x, cam.position[1], z];
  } else if (motion === 'tracking' && hit.instance) {
    next = [hit.instance.position[0], cam.position[1], hit.instance.position[2] + 3.2];
  } else if (motion === 'static') {
    store.updateCamera(camId, { motion: 'static' });
    return ok('机位已设为静止');
  }
  store.updateCamera(camId, { motion, target: look });
  await tweenCamera(camId, next, 900);
  store.lookAt(camId, look);
  store.setViewMode('shot');
  return ok(`已执行镜头 ${motion}`, { motion, position: next });
}

function setCamera(args: Record<string, unknown>, runtime: ToolRuntime): ToolResult {
  if (args.fov !== undefined) setCameraFov(args);
  if (args.position !== undefined) moveCamera(args);
  if (args.target_ref || args.character_ref || args.target) setCameraTarget(args, runtime);
  if (args.motion) void setCameraMotion(args, runtime);
  return ok('已更新机位', { camera: args });
}

async function restoreGenerationTool(args: Record<string, unknown>): Promise<ToolResult> {
  const id = String(args.generation_id || '');
  if (!id) return fail('缺少 generation_id');
  const { restoreGeneration } = await import('../generationApi');
  const row = await restoreGeneration(id);
  useDirectorStore.getState().updateShotMeta({
    generationId: row.generation_id,
    imageUrl: row.kind === 'image' ? row.url ?? null : undefined,
    videoUrl: row.kind === 'video' ? row.url ?? null : undefined,
  });
  return ok(`已恢复生成 ${row.generation_id}`, { generation_id: row.generation_id });
}

function createShot(args: Record<string, unknown>): ToolResult {
  const duration = Number(args.duration) || 4;
  const name = String(args.name || '').trim() || undefined;
  const copy = args.copy_current === true;
  const store = useDirectorStore.getState();
  const id = copy && store.objects.length ? store.duplicateShotScene() : store.createShotScene(name);
  if (copy && name) store.renameScene(id, name);
  store.updateShotMeta({
    sceneName: name,
    shotDuration: duration,
    shotDescription: String(args.description || ''),
    shotType: args.shot_type ? String(args.shot_type) : undefined,
    cameraMovement: args.camera_movement ? String(args.camera_movement) : undefined,
    emotion: args.emotion ? String(args.emotion) : undefined,
    timeOfDay: args.time_of_day ? String(args.time_of_day) : undefined,
  });
  return ok(`已创建 ${duration} 秒分镜「${store.sceneName}」`, { scene_id: id, duration });
}

function deleteShot(args: Record<string, unknown>): ToolResult {
  return deleteScene(args);
}

function duplicateShot(): ToolResult {
  const id = useDirectorStore.getState().duplicateShotScene();
  return ok(`已复制分镜「${useDirectorStore.getState().sceneName}」`, { scene_id: id });
}

function updateShot(args: Record<string, unknown>): ToolResult {
  const patch: Parameters<ReturnType<typeof useDirectorStore.getState>['updateShotMeta']>[0] = {};
  if (args.name) patch.sceneName = String(args.name);
  if (args.duration !== undefined) patch.shotDuration = Number(args.duration);
  if (args.description !== undefined) patch.shotDescription = String(args.description);
  if (args.shot_type) patch.shotType = String(args.shot_type);
  if (args.camera_movement) patch.cameraMovement = String(args.camera_movement);
  if (args.emotion) patch.emotion = String(args.emotion);
  useDirectorStore.getState().updateShotMeta(patch);
  return ok('已更新分镜', patch);
}

function setShotType(args: Record<string, unknown>): ToolResult {
  const shotType = String(args.shot_type || 'close-up');
  const fov = Number(args.fov) || (shotType.includes('close') ? 28 : shotType.includes('wide') ? 58 : 45);
  const store = useDirectorStore.getState();
  store.updateShotMeta({ shotType });
  store.updateCamera(store.activeCamera, { fov });
  if (shotType.includes('close')) {
    const hit = store.objects.find((o) => o.characterId);
    if (hit) store.lookAt(store.activeCamera, [hit.position[0], hit.position[1] + 1.45, hit.position[2]]);
    store.setViewMode('shot');
  }
  return ok(`已将镜头改为 ${shotType}，FOV ${fov}`, { shot_type: shotType, fov });
}

async function authFetch(url: string, body: unknown): Promise<Record<string, unknown>> {
  const token = localStorage.getItem('vf_token');
  const { ensureDirectorProject, withDirectorProject } = await import('../scope');
  const project_id = await ensureDirectorProject();
  const res = await fetch(withDirectorProject(url), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ ...(body as Record<string, unknown>), project_id }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (data as { detail?: string }).detail || res.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return data as Record<string, unknown>;
}

async function sendComposition(): Promise<ToolResult> {
  try {
    const { sendCompositionToCanvas } = await import('../workspace');
    const url = await sendCompositionToCanvas();
    return ok('构图已发回画布，可作为生成参考', { url });
  } catch (err) {
    return fail(
      `发送构图失败：${err instanceof Error ? err.message : String(err)}`,
      '请先打开 3D 导演台，等视口就绪后再发送构图。',
    );
  }
}

async function generateImage(_args: Record<string, unknown>, ctx: DirectorContext): Promise<ToolResult> {
  const store = useDirectorStore.getState();
  try {
    const data = await authFetch('/api/director/generate/image', {
      kind: 'image',
      scene_id: store.sceneId,
      shot_id: store.sceneId,
      parent_generation_id: store.generationId || undefined,
      aspect_ratio: store.aspectRatio,
      context: ctx,
      shot: {
        duration: store.shotDuration,
        shot_type: store.shotType,
        camera_movement: store.cameraMovement,
        visual_description: store.shotDescription,
        emotion: store.emotion,
        time_of_day: store.timeOfDay,
      },
    });
    const url = String(data.url || '');
    store.updateShotMeta({
      imageUrl: url,
      imagePrompt: String(data.prompt || ''),
      generationId: String(data.generation_id || ''),
    });
    return ok('已生成参考画面并绑定当前镜头', { url, prompt: data.prompt, generation_id: data.generation_id });
  } catch (err) {
    return fail(
      `图片生成失败：${err instanceof Error ? err.message : String(err)}`,
      '可更换模型、修改提示词后重试。不会假装成功。',
    );
  }
}

async function generateVideo(args: Record<string, unknown>, ctx: DirectorContext): Promise<ToolResult> {
  const store = useDirectorStore.getState();
  let imageUrl = store.imageUrl || store.compositionUrl || store.environment.backdropUrl || undefined;
  let imageDataUrl: string | undefined;
  if (!imageUrl) {
    try {
      const { captureScene } = await import('../sceneApi');
      const shot = await captureScene();
      imageDataUrl = shot.dataUrl;
    } catch (err) {
      return fail(
        `当前镜头没有参考图，截图也失败：${err instanceof Error ? err.message : String(err)}`,
        '请先说「生成这个镜头的画面」，或等 3D 视口就绪后再生成视频。Qwen I2V 必须有首帧。',
      );
    }
  }
  try {
    const data = await authFetch('/api/director/generate/video', {
      kind: 'video',
      scene_id: store.sceneId,
      shot_id: store.sceneId,
      parent_generation_id: store.generationId || undefined,
      duration: Number(args.duration) || store.shotDuration || 5,
      aspect_ratio: store.aspectRatio,
      image_url: imageUrl,
      image_data_url: imageDataUrl,
      context: ctx,
      shot: {
        duration: store.shotDuration,
        shot_type: store.shotType,
        camera_movement: store.cameraMovement,
        visual_description: store.shotDescription,
        emotion: store.emotion,
      },
    });
    store.updateShotMeta({
      videoUrl: String(data.url || ''),
      videoPrompt: String(data.prompt || ''),
      generationId: String(data.generation_id || ''),
    });
    return ok('已生成视频并绑定当前镜头', { url: data.url, prompt: data.prompt, generation_id: data.generation_id });
  } catch (err) {
    return fail(
      `视频生成失败：${err instanceof Error ? err.message : String(err)}`,
      '可先生成参考图，或更换视频模型后重试。',
    );
  }
}

function createKeyframe(args: Record<string, unknown>, runtime: ToolRuntime): ToolResult {
  const hit = resolveCharacter(args.object_ref ?? args.character_ref, runtime);
  const obj = hit.instance ?? useDirectorStore.getState().objects.find((o) => o.id === args.object_id);
  const time = Number(args.time) || 0;
  const id = useDirectorStore.getState().addTimelineKey({
    time,
    objectId: obj?.id,
    position: obj?.position,
    rotation: obj?.rotation,
    pose: args.pose ? String(args.pose) : obj?.pose ?? null,
    animation: args.animation ? String(args.animation) : obj?.animation ?? null,
  });
  return ok(`已记录 ${time}s 关键帧`, { key_id: id });
}

function updateKeyframe(args: Record<string, unknown>): ToolResult {
  const id = String(args.key_id || '');
  if (!id) return fail('缺少 key_id');
  useDirectorStore.getState().updateTimelineKey(id, {
    time: args.time !== undefined ? Number(args.time) : undefined,
    pose: args.pose !== undefined ? String(args.pose) : undefined,
    animation: args.animation !== undefined ? String(args.animation) : undefined,
  });
  return ok('已更新关键帧');
}

function deleteKeyframe(args: Record<string, unknown>): ToolResult {
  const id = String(args.key_id || '');
  if (!id) return fail('缺少 key_id');
  useDirectorStore.getState().removeTimelineKey(id);
  return ok('已删除关键帧');
}

function setTimelineMeta(name: string, args: Record<string, unknown>): ToolResult {
  const store = useDirectorStore.getState();
  const timeline = store.timeline ?? { duration: store.shotDuration ?? 4, keys: [] };
  if (name === 'set_animation_duration') {
    const duration = Number(args.duration) || timeline.duration;
    store.setTimeline({ ...timeline, duration });
    store.updateShotMeta({ shotDuration: duration });
    return ok(`时间线时长 ${duration}s`);
  }
  const objectId = String(args.object_id || '');
  const keys = timeline.keys.filter((k) => !objectId || k.objectId === objectId);
  if (!keys.length) return fail('没有可修改的动作关键帧。', '请先创建关键帧。');
  if (name === 'set_action_start') {
    store.updateTimelineKey(keys[0].id, { time: Number(args.time) || 0 });
    return ok('已设置动作起点');
  }
  store.updateTimelineKey(keys[keys.length - 1].id, { time: Number(args.time) || timeline.duration });
  return ok('已设置动作终点');
}

function generatePrompt(args: Record<string, unknown>, ctx: DirectorContext): ToolResult {
  const kind = String(args.kind || 'video') as PromptKind;
  const built = generatePromptFromContext(kind, ctx);
  return ok(`已根据当前导演台生成${kind}提示词`, { prompt: built.prompt, kind });
}

function undoLast(runtime: ToolRuntime): ToolResult {
  return runtime.undoAgent();
}

function redoLast(runtime: ToolRuntime): ToolResult {
  return runtime.redoAgent();
}

export { sleep, ALLOWED as ALLOWED_TOOLS };
