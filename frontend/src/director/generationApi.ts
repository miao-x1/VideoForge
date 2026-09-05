import { apiHttp } from '../api/client';
import { ensureDirectorProject } from './scope';

export interface GenerationVersion {
  generation_id: string;
  parent_generation_id?: string | null;
  version: number;
  version_number?: number;
  kind: string;
  title?: string;
  project_id?: string;
  scene_id: string;
  status: string;
  prompt?: string;
  url?: string | null;
  output_asset_id?: string | null;
  preview_asset?: string | null;
  duration?: number | null;
  aspect_ratio?: string | null;
  created_at?: number;
  error_message?: string | null;
  error?: string | null;
  idempotent?: boolean;
}

async function projectParams(extra: Record<string, string> = {}): Promise<{ project_id: string } & Record<string, string>> {
  return { project_id: await ensureDirectorProject(), ...extra };
}

export async function fetchGenerationHistory(sceneId: string): Promise<GenerationVersion[]> {
  const { data } = await apiHttp.get('/api/director/generate/history', {
    params: await projectParams({ scene_id: sceneId }),
  });
  return Array.isArray(data?.items) ? data.items : [];
}

export async function fetchUserWorks(kind?: 'image' | 'video' | '', q?: string): Promise<GenerationVersion[]> {
  const { data } = await apiHttp.get('/api/director/generate/works', {
    params: { ...(kind ? { kind } : {}), ...(q ? { q } : {}) },
  });
  return Array.isArray(data?.items) ? data.items : [];
}

export async function updateWorkTitle(id: string, title: string): Promise<GenerationVersion> {
  const { data } = await apiHttp.patch(`/api/director/generate/${id}`, { title });
  return data;
}

export async function deleteWork(id: string): Promise<void> {
  await apiHttp.delete(`/api/director/generate/${id}`);
}

export async function fetchGeneration(id: string): Promise<GenerationVersion> {
  const { data } = await apiHttp.get(`/api/director/generate/${id}`, {
    params: await projectParams(),
  });
  return data;
}

export async function restoreGeneration(id: string): Promise<GenerationVersion> {
  const { data } = await apiHttp.post(`/api/director/generate/${id}/restore`, null, {
    params: await projectParams(),
  });
  return data;
}

export interface GenerateBody {
  kind: 'image' | 'video';
  scene_id: string;
  shot_id?: string;
  parent_generation_id?: string;
  prompt?: string;
  negative_prompt?: string;
  duration?: number;
  aspect_ratio?: string;
  image_url?: string;
  image_data_url?: string;
  context?: Record<string, unknown>;
  shot?: Record<string, unknown>;
}

function generationError(err: unknown): Error {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (err instanceof Error) return err;
  return new Error('生成失败');
}

export async function requestGenerateImage(body: GenerateBody): Promise<GenerationVersion> {
  try {
    const project_id = await ensureDirectorProject();
    const { data } = await apiHttp.post('/api/director/generate/image', {
      ...body,
      kind: 'image',
      project_id,
    }, { params: { project_id } });
    return data;
  } catch (err) {
    throw generationError(err);
  }
}

export async function requestGenerateVideo(body: GenerateBody): Promise<GenerationVersion> {
  try {
    const project_id = await ensureDirectorProject();
    const { data } = await apiHttp.post('/api/director/generate/video', {
      ...body,
      kind: 'video',
      project_id,
    }, { params: { project_id, wait: false }, timeout: 30_000 });
    return data;
  } catch (err) {
    throw generationError(err);
  }
}

export async function waitForGeneration(
  id: string,
  onTick?: (row: GenerationVersion) => void,
): Promise<GenerationVersion> {
  const deadline = Date.now() + 15 * 60 * 1000;
  while (Date.now() < deadline) {
    const row = await fetchGeneration(id);
    onTick?.(row);
    if (row.status === 'completed') return row;
    if (row.status === 'failed' || row.status === 'cancelled') {
      throw new Error(row.error_message || row.error || '生成失败');
    }
    await new Promise((resolve) => setTimeout(resolve, 2500));
  }
  throw new Error('出片超过 15 分钟。请打开右上角「历史记录」查看结果，或再试一次。');
}
