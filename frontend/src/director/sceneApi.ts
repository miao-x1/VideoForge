/**
 * Reserved Phase-2 Agent surface.
 * Agents must call these functions — never Three.js Object3D.
 */
import * as THREE from 'three';
import { useDirectorStore } from './store/useDirectorStore';
import { getCaptureContext, setCapturing } from './captureRegistry';
import { downloadSceneJson, loadSceneFromStorage, parseSceneJson, saveSceneToStorage } from './persist';
import { capturePixelSize, parseAspect } from './types';
import type { DirectorSceneState, SceneCamera, SceneObject } from './types';
import { useCharacterLibrary } from './characters/useCharacterLibrary';
import type { CharacterAsset } from './characters/types';
import { buildControlData, type SceneControlData } from './characters/controlData';

export interface CaptureResult {
  blob: Blob;
  file: File;
  dataUrl: string;
}

function getActiveCamera(): SceneCamera {
  const state = useDirectorStore.getState();
  return state.cameras.find((c) => c.id === state.activeCamera) ?? state.cameras[0];
}

function cameraFromState(cam: SceneCamera, aspect: number): THREE.PerspectiveCamera {
  const camera = new THREE.PerspectiveCamera(cam.fov, aspect, 0.1, 200);
  camera.position.set(...cam.position);
  camera.rotation.set(...cam.rotation);
  camera.updateMatrixWorld(true);
  return camera;
}

export function getSceneState(): DirectorSceneState {
  return useDirectorStore.getState().getSceneState();
}

export function setSceneState(state: DirectorSceneState): void {
  useDirectorStore.getState().setSceneState(state);
}

export function saveScene(): DirectorSceneState {
  const state = getSceneState();
  saveSceneToStorage(state);
  downloadSceneJson(state);
  return state;
}

export function loadScene(source?: DirectorSceneState | string): DirectorSceneState {
  if (typeof source === 'string') {
    const next = parseSceneJson(source);
    setSceneState(next);
    return next;
  }
  if (source) {
    setSceneState(source);
    return source;
  }
  const stored = loadSceneFromStorage();
  if (!stored) throw new Error('没有可加载的场景');
  setSceneState(stored);
  return stored;
}

export function getSceneObjects(): SceneObject[] {
  return useDirectorStore.getState().objects;
}

export function getSelectedObject(): SceneObject | SceneCamera | null {
  const state = useDirectorStore.getState();
  if (!state.selectedId) return null;
  return (
    state.objects.find((o) => o.id === state.selectedId) ??
    state.cameras.find((c) => c.id === state.selectedId) ??
    null
  );
}

export function getCameraState(): SceneCamera | null {
  return getActiveCamera() ?? null;
}

export async function captureScene(): Promise<CaptureResult> {
  const ctx = getCaptureContext();
  if (!ctx) throw new Error('3D Viewport 尚未就绪');

  const state = getSceneState();
  const camState = getActiveCamera();
  if (!camState) throw new Error('没有可用机位');

  const { width, height } = capturePixelSize(state.aspectRatio);
  const aspect = parseAspect(state.aspectRatio);
  const camera = cameraFromState(camState, aspect);

  setCapturing(true);
  await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));

  const { gl, scene } = ctx;
  const prev = new THREE.Vector2();
  gl.getSize(prev);
  const prevPixelRatio = gl.getPixelRatio();

  try {
    gl.setPixelRatio(1);
    gl.setSize(width, height, false);
    gl.render(scene, camera);
    const dataUrl = gl.domElement.toDataURL('image/png');
    const blob = await new Promise<Blob>((resolve, reject) => {
      gl.domElement.toBlob((b) => (b ? resolve(b) : reject(new Error('截图失败'))), 'image/png');
    });
    const file = new File([blob], `${state.sceneId}.png`, { type: 'image/png' });
    return { blob, file, dataUrl };
  } finally {
    gl.setPixelRatio(prevPixelRatio);
    gl.setSize(prev.x, prev.y, false);
    setCapturing(false);
  }
}

export async function getSceneScreenshot(): Promise<string> {
  const result = await captureScene();
  return result.dataUrl;
}

export function getCharacterLibrary(): CharacterAsset[] {
  return useCharacterLibrary.getState().characters;
}

export function getCharacter(characterId: string): CharacterAsset | undefined {
  return useCharacterLibrary.getState().getById(characterId);
}

export function exportControlData(): SceneControlData {
  return buildControlData();
}

export const directorApi = {
  getSceneState,
  setSceneState,
  saveScene,
  loadScene,
  getSceneObjects,
  getSelectedObject,
  getCameraState,
  captureScene,
  getSceneScreenshot,
  getCharacterLibrary,
  getCharacter,
  exportControlData,
};

declare global {
  interface Window {
    directorDesk?: typeof directorApi;
  }
}

export function exposeDirectorApi(): void {
  window.directorDesk = directorApi;
}
