import type { ClipId } from '../characters/types';

export type ActionGroup = 'daily' | 'drama' | 'emotion';

export interface DirectorAction {
  id: string;
  group: ActionGroup;
  label: string;
  clip: ClipId;
  pose?: string;
  note?: string;
}

export const DIRECTOR_ACTIONS: DirectorAction[] = [
  { id: 'walk', group: 'daily', label: '走路', clip: 'walk', pose: 'walk' },
  { id: 'sit', group: 'daily', label: '坐下', clip: 'sit', pose: 'sit' },
  { id: 'idle', group: 'daily', label: '站立', clip: 'idle', pose: 'stand' },
  { id: 'drink', group: 'daily', label: '喝水', clip: 'idle', pose: 'stand', note: '用站立预演持杯，可再微调手势' },
  { id: 'talk', group: 'drama', label: '对话', clip: 'talk', pose: 'stand' },
  { id: 'hug', group: 'drama', label: '拥抱', clip: 'hug', pose: 'stand' },
  { id: 'fight', group: 'drama', label: '打斗', clip: 'fight', pose: 'stand' },
  { id: 'argue', group: 'drama', label: '争吵', clip: 'talk', pose: 'stand', note: '配合冲突站位使用' },
  { id: 'turn', group: 'drama', label: '转身', clip: 'turn', pose: 'stand' },
  { id: 'happy', group: 'emotion', label: '开心', clip: 'wave', pose: 'wave' },
  { id: 'angry', group: 'emotion', label: '愤怒', clip: 'shake', pose: 'stand' },
  { id: 'sad', group: 'emotion', label: '悲伤', clip: 'look', pose: 'stand' },
];

export const ACTION_GROUPS: Array<{ key: ActionGroup; label: string }> = [
  { key: 'daily', label: '日常' },
  { key: 'drama', label: '剧情' },
  { key: 'emotion', label: '情绪' },
];
