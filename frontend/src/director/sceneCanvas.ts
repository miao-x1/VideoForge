import { mediaUrl } from '../api/client';
import { uploadDirectorAsset } from './assetApi';
import { useDirectorStore } from './store/useDirectorStore';

/** 把实拍图贴到 3D 摄影棚画布上，同时作为出片参考。 */
export function applySceneCanvas(url: string): void {
  const store = useDirectorStore.getState();
  store.setEnvironment({ backdropUrl: url });
  store.updateShotMeta({ compositionUrl: url });
}

export function clearSceneCanvas(): void {
  const store = useDirectorStore.getState();
  const current = store.environment.backdropUrl;
  store.setEnvironment({ backdropUrl: null });
  if (current && store.compositionUrl === current) {
    store.updateShotMeta({ compositionUrl: null });
  }
}

export async function applySceneCanvasFile(file: File): Promise<void> {
  if (!file.type.startsWith('image/')) {
    throw new Error('请上传图片作为场景画布');
  }
  const dataUrl = await readFileAsDataUrl(file);
  applySceneCanvas(dataUrl);
  try {
    const uploaded = await uploadDirectorAsset(file, 'image');
    if (uploaded.url) applySceneCanvas(mediaUrl(uploaded.url));
  } catch {
    /* 上传失败仍保留本地画布，保证视口立刻能看见 */
  }
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error('读取图片失败'));
    reader.readAsDataURL(file);
  });
}
