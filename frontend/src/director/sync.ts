import { apiHttp } from '../api/client';
import { normalizeAsset, loadCharacterLibrary, saveCharacterLibrary, type CharacterLibraryState } from './characters/persistLibrary';
import { useCharacterLibrary } from './characters/useCharacterLibrary';
import { loadSceneBook, saveSceneBook, type SceneBook } from './persist';
import { directorProjectParams } from './scope';
import { putRemoteLibrary, putRemoteSceneBook } from './syncSchedule';
import { useDirectorStore } from './store/useDirectorStore';
import { createEmptyScene, normalizeScene } from './types';

const http = apiHttp;

export async function fetchRemoteLibrary(): Promise<CharacterLibraryState | null> {
  try {
    const { data } = await http.get<CharacterLibraryState>('/api/director/library', {
      params: directorProjectParams(),
    });
    return {
      characters: (data.characters ?? []).map((c) => normalizeAsset(c)),
      favorites: data.favorites ?? [],
      recentIds: data.recentIds ?? [],
      savedPoses: data.savedPoses ?? [],
      customAnimations: data.customAnimations ?? [],
    };
  } catch {
    return null;
  }
}

export async function fetchRemoteSceneBook(): Promise<SceneBook | null> {
  try {
    const { data } = await http.get<SceneBook>('/api/director/scenebook', {
      params: directorProjectParams(),
    });
    return {
      currentId: data.currentId ?? '',
      scenes: (data.scenes ?? []).map((s) => normalizeScene(s)),
      projectName: data.projectName,
      chapterName: data.chapterName,
    };
  } catch {
    return null;
  }
}

export function applyScopedLocalCaches(): void {
  const lib = loadCharacterLibrary();
  useCharacterLibrary.setState({
    characters: lib.characters,
    favorites: lib.favorites,
    recentIds: lib.recentIds,
    savedPoses: lib.savedPoses,
    customAnimations: lib.customAnimations,
  });
  const book = loadSceneBook();
  if (book?.scenes.length) {
    const current = book.scenes.find((s) => s.sceneId === book.currentId) ?? book.scenes[0];
      useDirectorStore.setState({
        ...current,
        scenes: book.scenes,
        projectName: current.projectName || book.projectName || '未命名项目',
        chapterName: current.chapterName || book.chapterName || '第1集',
        historyPast: [],
        historyFuture: [],
      });
    return;
  }
  const empty = createEmptyScene();
  useDirectorStore.setState({
    ...empty,
    scenes: [empty],
    historyPast: [],
    historyFuture: [],
  });
}

export async function hydrateDirectorFromBackend(): Promise<void> {
  const localLib = {
    characters: useCharacterLibrary.getState().characters,
    favorites: useCharacterLibrary.getState().favorites,
    recentIds: useCharacterLibrary.getState().recentIds,
    savedPoses: useCharacterLibrary.getState().savedPoses,
    customAnimations: useCharacterLibrary.getState().customAnimations,
  };
  const remoteLib = await fetchRemoteLibrary();
  if (remoteLib) {
    const remoteEmpty = !remoteLib.characters.length && !remoteLib.savedPoses.length && !remoteLib.customAnimations.length;
    if (remoteEmpty && (localLib.characters.length || localLib.savedPoses.length || localLib.customAnimations.length)) {
      putRemoteLibrary(localLib).catch(() => undefined);
    } else {
      saveCharacterLibrary(remoteLib);
      useCharacterLibrary.setState(remoteLib);
    }
  } else if (localLib.characters.length || localLib.savedPoses.length || localLib.customAnimations.length) {
    putRemoteLibrary(localLib).catch(() => undefined);
  }

  const localBook = loadSceneBook();
  const remoteBook = await fetchRemoteSceneBook();
  if (remoteBook) {
    if (!remoteBook.scenes.length && localBook?.scenes.length) {
      putRemoteSceneBook(localBook).catch(() => undefined);
    } else if (remoteBook.scenes.length) {
      saveSceneBook(remoteBook);
      const current = remoteBook.scenes.find((s) => s.sceneId === remoteBook.currentId) ?? remoteBook.scenes[0];
      useDirectorStore.setState({
        ...current,
        scenes: remoteBook.scenes,
        projectName: current.projectName || remoteBook.projectName || localBook?.projectName || '未命名项目',
        chapterName: current.chapterName || remoteBook.chapterName || localBook?.chapterName || '第1集',
        historyPast: [],
        historyFuture: [],
      });
    }
  } else if (localBook?.scenes.length) {
    putRemoteSceneBook(localBook).catch(() => undefined);
  }
}
