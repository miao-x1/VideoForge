import { api } from '../api/client';
import { captureScene } from './sceneApi';
import { useDirectorStore } from './store/useDirectorStore';

export type WorkspaceMode = 'canvas' | 'stage';

function toPublicUrl(filePath: string): string {
  if (filePath.startsWith('http') || filePath.startsWith('data:')) return filePath;
  let path = filePath;
  if (!path.startsWith('/storage/')) {
    const norm = filePath.replace(/\\/g, '/');
    const idx = norm.toLowerCase().lastIndexOf('/storage/');
    if (idx >= 0) path = norm.slice(idx);
    else if (norm.startsWith('storage/')) path = `/${norm}`;
    else {
      const uploads = norm.split('/uploads/')[1];
      path = uploads ? `/storage/uploads/${uploads}` : `/storage/${norm.replace(/^\/+/, '')}`;
    }
  }
  return path;
}

/** 3D 构图截图发送到画布节点，作为后续生图/生视频的空间参考。 */
export async function sendCompositionToCanvas(): Promise<string> {
  const shot = await captureScene();
  let url = shot.dataUrl;
  try {
    const uploaded = await api.uploadImage(shot.file);
    if (uploaded.file_path) url = toPublicUrl(uploaded.file_path);
  } catch {
    /* 上传失败仍用本地 dataURL，保证画布能立刻看到构图 */
  }
  useDirectorStore.getState().updateShotMeta({ compositionUrl: url });
  useDirectorStore.getState().persistNow();
  window.dispatchEvent(new CustomEvent('director:composition-sent', { detail: { url } }));
  return url;
}
