import { computeBlocking } from './blocking';
import { planAutoStage } from './autoStage';
import { analyzeScene } from './advice';
import { environmentLook, frameCamera } from './look';
import { createEmptyScene } from '../types';

export function runDirectingChecks(): string[] {
  const errors: string[] = [];
  const assert = (cond: boolean, msg: string) => {
    if (!cond) errors.push(msg);
  };

  const dialogue = computeBlocking('dialogue', 2);
  assert(dialogue.length === 2, 'dialogue blocking should place 2 characters');
  assert(dialogue[0].position[0] < 0 && dialogue[1].position[0] > 0, 'dialogue should face across X');

  const conflict = computeBlocking('conflict', 2);
  assert(Math.abs(conflict[0].position[0] - conflict[1].position[0]) > 2.5, 'conflict should keep distance');

  const plan = planAutoStage('两个人在雨夜街头争吵');
  assert(plan.weather === 'rain', 'rain keyword');
  assert(plan.timeOfDay === 'night', 'night keyword');
  assert(plan.presetId === 'street', 'street keyword');
  assert(plan.blocking === 'conflict', 'argue keyword');
  assert(plan.needCharacters === 2, 'two people');

  const love = planAutoStage('两个人在黄昏拥抱');
  assert(love.blocking === 'embrace', 'love blocking');
  assert(love.atmosphere === 'romantic', 'love atmosphere');

  const look = environmentLook('rain', 'night', 'oppressive');
  assert((look.ambientIntensity ?? 1) < 0.35, 'rain night should be dark');

  const cam = frameCamera('close', 'low', [0, 1.4, 0]);
  assert(cam.fov < 40, 'close shot tighter fov');
  assert(cam.position[1] < 1.2, 'low angle camera height');

  const empty = createEmptyScene();
  const tips = analyzeScene(empty);
  assert(tips.some((t) => t.id === 'no-char'), 'empty scene should ask for characters');

  return errors;
}
