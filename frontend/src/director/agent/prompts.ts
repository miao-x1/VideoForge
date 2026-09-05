import type { DirectorContext } from './context';

export type PromptKind = 'image' | 'video' | 'motion' | 'camera' | 'scene';

export function generatePromptFromContext(kind: PromptKind, ctx: DirectorContext): { kind: PromptKind; prompt: string } {
  const chars = ctx.objects.filter((o) => o.characterId);
  const props = ctx.objects.filter((o) => !o.characterId);
  const cam = ctx.cameras.find((c) => c.id === ctx.active_camera) ?? ctx.cameras[0];
  const charText = chars.map((c) => {
    const bits = [c.name];
    if (c.animation) bits.push(`动作${c.animation}`);
    if (c.pose) bits.push(`姿势${c.pose}`);
    bits.push(`位置(${c.position.map((n) => n.toFixed(2)).join(',')})`);
    return bits.join('，');
  }).join('；') || '无角色';
  const propText = props.map((p) => p.name).join('、') || '空场景';
  const motion = cam?.motion || 'static';
  const fov = cam?.fov ?? 45;
  const desc = ctx.shot_description ? `${ctx.shot_description}。` : '';

  if (kind === 'image') {
    return {
      kind,
      prompt: `电影静帧，${ctx.scene_name}。${desc}角色：${charText}。场景：${propText}。机位 fov ${fov}，${motion}。`,
    };
  }
  if (kind === 'motion') {
    return { kind, prompt: `动作提示，时长 ${ctx.shot_duration}s。${charText}。` };
  }
  if (kind === 'camera') {
    return {
      kind,
      prompt: `镜头提示：${ctx.scene_name}，${ctx.shot_duration}s，机位 ${cam?.name ?? '主相机'} fov ${fov}，运动 ${motion}，位置 ${cam?.position}，目标 ${cam?.target ?? '无'}。`,
    };
  }
  if (kind === 'scene') {
    return { kind, prompt: `场景提示：${ctx.scene_name}。物件：${propText}。角色：${charText}。` };
  }
  return {
    kind: 'video',
    prompt: `电影视频，${ctx.shot_duration} 秒，${ctx.scene_name}。${desc}角色：${charText}。场景：${propText}。镜头 ${motion}，fov ${fov}，机位 ${cam?.position}。真实光影，连贯动作，不要字幕。`,
  };
}
