import { api } from '../api/client';

const USER_KEY = 'vf_user';
const PROJECT_KEY = 'vf_director_project';

let memoryProjectId = '';
let ensureInflight: Promise<string> | null = null;

export function getStoredUserId(): string {
  try {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return '';
    const parsed = JSON.parse(raw) as { id?: string };
    return String(parsed?.id || '');
  } catch {
    return '';
  }
}

function persistProjectId(projectId: string): void {
  if (!projectId) return;
  memoryProjectId = projectId;
  try {
    localStorage.setItem(PROJECT_KEY, projectId);
    const userId = getStoredUserId();
    if (userId) localStorage.setItem(`${PROJECT_KEY}:${userId}`, projectId);
  } catch {
    /* ignore quota / private mode */
  }
}

export function getDirectorProjectId(): string {
  if (typeof window === 'undefined') return memoryProjectId;
  const fromQuery = new URLSearchParams(window.location.search).get('project_id');
  if (fromQuery) {
    persistProjectId(fromQuery);
    return fromQuery;
  }
  if (memoryProjectId) return memoryProjectId;
  const userId = getStoredUserId();
  const scoped = userId ? localStorage.getItem(`${PROJECT_KEY}:${userId}`) || '' : '';
  const fallback = localStorage.getItem(PROJECT_KEY) || '';
  const found = scoped || fallback;
  if (found) memoryProjectId = found;
  return found;
}

export function setDirectorProjectId(projectId: string): void {
  persistProjectId(projectId);
}

export function directorProjectParams(): { project_id: string } {
  return { project_id: getDirectorProjectId() };
}

export function withDirectorProject(url: string): string {
  const pid = getDirectorProjectId();
  if (!pid) return url;
  const sep = url.includes('?') ? '&' : '?';
  return `${url}${sep}project_id=${encodeURIComponent(pid)}`;
}

export function scopedStorageKey(base: string): string {
  const userId = getStoredUserId() || 'anon';
  const projectId = getDirectorProjectId() || 'none';
  return `wedeo-forge.director.${userId}.${projectId}.${base}`;
}

export async function ensureDirectorProject(): Promise<string> {
  if (ensureInflight) return ensureInflight;
  ensureInflight = (async () => {
    const existing = getDirectorProjectId();
    if (existing) {
      try {
        await api.getProject(existing);
        persistProjectId(existing);
        return existing;
      } catch {
        memoryProjectId = '';
      }
    }
    const projects = await api.listProjects();
    const first = projects[0];
    if (first?.id) {
      persistProjectId(first.id);
      return first.id;
    }
    const created = await api.createProject({ title: '导演台' });
    persistProjectId(created.id);
    return created.id;
  })().finally(() => {
    ensureInflight = null;
  });
  return ensureInflight;
}

export async function switchDirectorProject(projectId: string): Promise<void> {
  persistProjectId(projectId);
}
