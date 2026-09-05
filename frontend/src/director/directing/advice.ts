import type { DirectorSceneState, SceneObject } from '../types';
import { distance2d, shotSizeFromFov, SHOT_SIZE_LABEL } from './look';

export interface DirectorAdvice {
  id: string;
  title: string;
  detail: string;
  apply?: 'closer' | 'medium' | 'sidelight' | 'lookat' | 'dialogue';
}

export function analyzeScene(state: DirectorSceneState): DirectorAdvice[] {
  const tips: DirectorAdvice[] = [];
  const chars = state.objects.filter((o) => o.characterId);
  const cam = state.cameras.find((c) => c.id === state.activeCamera) ?? state.cameras[0];
  const ambient = state.environment.ambientIntensity ?? 0.55;
  const weather = state.environment.weather ?? 'clear';
  const time = state.environment.timeOfDay || state.timeOfDay || '';

  if (chars.length === 0) {
    tips.push({ id: 'no-char', title: '还没有角色', detail: '从左侧导演资产库加入角色，再谈镜头。' });
    return tips;
  }

  if (chars.length >= 2) {
    const dist = distance2d(chars[0].position, chars[1].position);
    if (dist > 3.4) {
      tips.push({
        id: 'too-far',
        title: '两个角色距离过远',
        detail: `当前约 ${dist.toFixed(1)} 米。建议调成中景对话站位，让关系进画面。`,
        apply: 'dialogue',
      });
    } else if (dist < 0.45) {
      tips.push({
        id: 'too-close',
        title: '角色几乎重叠',
        detail: '除非拥抱，否则略微分开，避免穿模。',
      });
    }
  }

  if (cam) {
    const size = cam.shotSize || shotSizeFromFov(cam.fov);
    if (chars.length >= 2 && (size === 'extreme_close' || size === 'close')) {
      tips.push({
        id: 'tight-two',
        title: '双人戏用了过近景别',
        detail: `当前偏${SHOT_SIZE_LABEL[size]}。建议改为中景，同时保留关系。`,
        apply: 'medium',
      });
    }
    const target = chars[0];
    const lookDist = Math.hypot(cam.position[0] - target.position[0], cam.position[2] - target.position[2]);
    if (lookDist > 12) {
      tips.push({
        id: 'cam-far',
        title: '机位离人物太远',
        detail: '建议对准主角并切到中景。',
        apply: 'lookat',
      });
    }
  }

  if (ambient < 0.32 && time !== 'night') {
    tips.push({
      id: 'dark-day',
      title: '日戏偏暗',
      detail: '环境光过低，画面会脏。可提高环境光或改成夜戏。',
    });
  }
  if ((time === 'night' || weather === 'rain') && ambient > 0.5) {
    tips.push({
      id: 'sidelight',
      title: '建议增加侧光',
      detail: '雨夜/夜戏用侧光能保住轮廓，不要只靠环境光。',
      apply: 'sidelight',
    });
  }
  if (chars.length >= 2 && !state.relations?.length) {
    tips.push({
      id: 'relation',
      title: '还没标角色关系',
      detail: '在导演控制台标出敌对 / 同盟 / 爱慕，生成时会带上这段关系。',
    });
  }
  if (!tips.length) {
    tips.push({
      id: 'ok',
      title: '当前镜头可以拍',
      detail: '站位和光比没有明显问题。可以直接生成参考，或再微调情绪。',
    });
  }
  return tips;
}

export function leadCharacter(objects: SceneObject[]): SceneObject | undefined {
  return objects.find((o) => o.characterId);
}
