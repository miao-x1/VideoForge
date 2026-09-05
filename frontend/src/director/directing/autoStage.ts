import type { Atmosphere, Weather } from '../types';
import type { BlockingPreset } from './blocking';
import type { ShotSize, CameraAngle } from '../types';

export interface AutoStagePlan {
  locationName: string;
  presetId: string | null;
  weather: Weather;
  timeOfDay: string;
  atmosphere: Atmosphere;
  blocking: BlockingPreset;
  shotSize: ShotSize;
  angle: CameraAngle;
  cameraTemplate: 'romance' | 'battle' | 'dialogue' | null;
  relation: 'hostile' | 'romantic' | 'ally' | 'stranger';
  action: string;
  needCharacters: number;
  summary: string;
}

export function planAutoStage(text: string): AutoStagePlan {
  const t = text.trim();
  const rainy = /雨/.test(t);
  const night = /夜|晚上|深夜/.test(t);
  const dusk = /黄昏|傍晚/.test(t);
  const street = /街|马路|巷/.test(t);
  const room = /房|屋|室内|厅/.test(t);
  const forest = /林|森/.test(t);
  const argue = /吵|冲突|打|敌/.test(t);
  const love = /爱|吻|拥抱|恋/.test(t);
  const two = /两|双|对/.test(t);

  let presetId: string | null = null;
  if (street) presetId = 'street';
  else if (forest) presetId = 'forest';
  else if (room) presetId = 'room';

  const weather: Weather = rainy ? 'rain' : /雾/.test(t) ? 'fog' : /雪/.test(t) ? 'snow' : 'clear';
  const timeOfDay = night ? 'night' : dusk ? 'dusk' : 'day';
  const atmosphere: Atmosphere = argue ? 'oppressive' : love ? 'romantic' : rainy ? 'melancholy' : 'neutral';
  const blocking: BlockingPreset = love ? 'embrace' : argue ? 'conflict' : 'dialogue';
  const shotSize: ShotSize = love ? 'close' : argue ? 'medium' : 'medium';
  const angle: CameraAngle = argue ? 'low' : love ? 'eye' : 'eye';
  const cameraTemplate = love ? 'romance' : argue ? 'battle' : 'dialogue';
  const relation = love ? 'romantic' : argue ? 'hostile' : 'stranger';
  const action = love ? 'hug' : argue ? 'argue' : 'talk';
  const needCharacters = two || argue || love ? 2 : 1;

  const locationName = [
    timeOfDay === 'night' ? '夜晚' : timeOfDay === 'dusk' ? '黄昏' : '',
    weather === 'rain' ? '雨' : '',
    street ? '街头' : room ? '室内' : forest ? '林间' : '场景',
  ].join('') || '自动场景';

  return {
    locationName,
    presetId,
    weather,
    timeOfDay,
    atmosphere,
    blocking,
    shotSize,
    angle,
    cameraTemplate,
    relation,
    action,
    needCharacters,
    summary: `将布置「${locationName}」：${needCharacters} 个角色，${blocking === 'conflict' ? '冲突站位' : blocking === 'embrace' ? '靠近站位' : '对话站位'}，${shotSize === 'close' ? '近景' : '中景'}。仍可继续手动改。`,
  };
}
