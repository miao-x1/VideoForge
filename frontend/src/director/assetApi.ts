import { apiHttp } from '../api/client';
import { directorProjectParams } from './scope';

export interface DirectorAsset {
  id: string;
  name: string;
  asset_type?: string;
  mime_type?: string | null;
  file_name?: string | null;
  url?: string | null;
  created_at?: number;
}

export async function listDirectorAssets(): Promise<DirectorAsset[]> {
  const { data } = await apiHttp.get('/api/director/assets', { params: directorProjectParams() });
  return Array.isArray(data?.assets) ? data.assets : [];
}

export async function uploadDirectorAsset(file: File, assetType?: string): Promise<DirectorAsset> {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('name', file.name);
  if (assetType) fd.append('asset_type', assetType);
  const { data } = await apiHttp.post('/api/director/assets', fd, { params: directorProjectParams() });
  return data;
}

export async function deleteDirectorAsset(id: string): Promise<void> {
  await apiHttp.delete(`/api/director/assets/${id}`, { params: directorProjectParams() });
}
