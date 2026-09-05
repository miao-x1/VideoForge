import { apiHttp } from '../../api/client';
import { directorProjectParams } from '../scope';

export type PipelineTaskStatus = 'queued' | 'processing' | 'succeeded' | 'failed' | 'needs_reprocess';

export interface PipelineStage {
  name: string;
  status: 'pending' | 'succeeded' | 'failed' | 'skipped';
  error?: string | null;
}

export interface CharacterPipelineTask {
  task_id: string;
  kind: 'image_to_3d' | 'ai_generate';
  status: PipelineTaskStatus;
  progress: number;
  error: string | null;
  result: Record<string, unknown> | null;
  stages: PipelineStage[];
  created_at: number;
  updated_at: number;
}

const http = apiHttp;

export async function createImageTo3dTask(input: {
  images: File[];
  mode: 'single' | 'multi';
  name?: string;
}): Promise<CharacterPipelineTask> {
  const fd = new FormData();
  fd.append('kind', 'image_to_3d');
  fd.append('mode', input.mode);
  if (input.name) fd.append('name', input.name);
  input.images.forEach((file) => fd.append('images', file));
  const { data } = await http.post<CharacterPipelineTask>('/api/director/characters/tasks', fd, {
    params: directorProjectParams(),
  });
  return data;
}

export async function createAiGenerateTask(input: {
  prompt: string;
  name?: string;
}): Promise<CharacterPipelineTask> {
  const fd = new FormData();
  fd.append('kind', 'ai_generate');
  fd.append('prompt', input.prompt);
  if (input.name) fd.append('name', input.name);
  const { data } = await http.post<CharacterPipelineTask>('/api/director/characters/tasks', fd, {
    params: directorProjectParams(),
  });
  return data;
}

export async function getPipelineTask(taskId: string): Promise<CharacterPipelineTask> {
  const { data } = await http.get<CharacterPipelineTask>(`/api/director/characters/tasks/${taskId}`, {
    params: directorProjectParams(),
  });
  return data;
}

export async function getPipelineCapability(): Promise<{ image_to_3d: boolean; provider: string; message: string }> {
  const { data } = await http.get('/api/director/characters/capability');
  return data;
}
