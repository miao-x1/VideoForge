import { apiHttp } from '../api/client';
import type { CharacterLibraryState } from './characters/persistLibrary';
import type { SceneBook } from './persist';
import { ensureDirectorProject } from './scope';
import { useSaveStatus } from './saveStatus';

const http = apiHttp;

function apiErrorMessage(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

function stripDataUrls<T>(value: T): T {
  if (typeof value === 'string') {
    return (value.startsWith('data:') ? null : value) as T;
  }
  if (Array.isArray(value)) {
    return value.map((item) => stripDataUrls(item)) as T;
  }
  if (value && typeof value === 'object') {
    const next: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      next[key] = stripDataUrls(item);
    }
    return next as T;
  }
  return value;
}

export async function putRemoteLibrary(state: CharacterLibraryState): Promise<void> {
  const project_id = await ensureDirectorProject();
  await http.put('/api/director/library', stripDataUrls(state), { params: { project_id } });
}

export async function putRemoteSceneBook(book: SceneBook): Promise<void> {
  const project_id = await ensureDirectorProject();
  await http.put('/api/director/scenebook', stripDataUrls(book), { params: { project_id } });
}

let libTimer: number | null = null;
let sceneTimer: number | null = null;

export function flushLibrarySync(state: CharacterLibraryState): void {
  if (libTimer) window.clearTimeout(libTimer);
  libTimer = null;
  putRemoteLibrary(state).catch((err) => {
    useSaveStatus.getState().markError(apiErrorMessage(err, '角色库保存失败'));
  });
}

export function scheduleLibrarySync(state: CharacterLibraryState): void {
  if (libTimer) window.clearTimeout(libTimer);
  useSaveStatus.getState().markSaving();
  libTimer = window.setTimeout(() => {
    putRemoteLibrary(state)
      .then(() => useSaveStatus.getState().markSaved())
      .catch((err) => {
        useSaveStatus.getState().markError(apiErrorMessage(err, '角色库保存失败'));
      });
  }, 450);
}

export function flushSceneBookSync(book: SceneBook): void {
  void flushSceneBookNow(book);
}

export async function flushSceneBookNow(book?: SceneBook): Promise<void> {
  if (sceneTimer) window.clearTimeout(sceneTimer);
  sceneTimer = null;
  const payload = book ?? (await import('./agent/context')).captureBook();
  useSaveStatus.getState().markSaving();
  try {
    await putRemoteSceneBook(payload);
    useSaveStatus.getState().markSaved();
  } catch (err) {
    useSaveStatus.getState().markError(apiErrorMessage(err, '场景保存失败'));
    throw err;
  }
}

export function scheduleSceneBookSync(book: SceneBook): void {
  if (sceneTimer) window.clearTimeout(sceneTimer);
  useSaveStatus.getState().markSaving();
  sceneTimer = window.setTimeout(() => {
    putRemoteSceneBook(book)
      .then(() => useSaveStatus.getState().markSaved())
      .catch((err) => {
        useSaveStatus.getState().markError(apiErrorMessage(err, '场景保存失败'));
      });
  }, 450);
}
