import { scopedStorageKey } from './scope';
import type { DirectorSceneState } from './types';
import { normalizeScene } from './types';

export const SCENE_STORAGE_KEY = 'wedeo-forge.director.scene.v1';

function sceneKey(): string {
  return scopedStorageKey('scene.v1');
}

export function saveSceneToStorage(state: DirectorSceneState): void {
  const payload = JSON.stringify(state);
  localStorage.setItem(sceneKey(), payload);
}

export function loadSceneFromStorage(): DirectorSceneState | null {
  const raw = localStorage.getItem(sceneKey());
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as DirectorSceneState;
    if (!parsed || !Array.isArray(parsed.objects)) return null;
    return normalizeScene(parsed);
  } catch {
    return null;
  }
}

export function downloadSceneJson(state: DirectorSceneState): void {
  const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${state.sceneId}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export function parseSceneJson(text: string): DirectorSceneState {
  const parsed = JSON.parse(text) as DirectorSceneState;
  if (!parsed || parsed.version !== 1 || !Array.isArray(parsed.objects) || !Array.isArray(parsed.cameras)) {
    throw new Error('无效的 Scene State JSON');
  }
  return normalizeScene(parsed);
}

export const SCENE_BOOK_STATE_KEY = 'wedeo-forge.director.scenebook.v1';

function sceneBookKey(): string {
  return scopedStorageKey('scenebook.v1');
}

export interface SceneBook {
  currentId: string;
  scenes: DirectorSceneState[];
  projectName?: string;
  chapterName?: string;
}

export function loadSceneBook(): SceneBook | null {
  try {
    const raw = localStorage.getItem(sceneBookKey());
    if (!raw) {
      const single = loadSceneFromStorage();
      if (!single) return null;
      return { currentId: single.sceneId, scenes: [single] };
    }
    const parsed = JSON.parse(raw) as SceneBook;
    if (!parsed?.scenes?.length) return null;
    return {
      currentId: parsed.currentId,
      scenes: parsed.scenes.map((s) => normalizeScene(s)),
      projectName: parsed.projectName,
      chapterName: parsed.chapterName,
    };
  } catch {
    return null;
  }
}

export function saveSceneBook(book: SceneBook): void {
  localStorage.setItem(sceneBookKey(), JSON.stringify(book));
  const current = book.scenes.find((s) => s.sceneId === book.currentId) ?? book.scenes[0];
  if (current) saveSceneToStorage(current);
}
