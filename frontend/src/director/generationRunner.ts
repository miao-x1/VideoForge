import { create } from 'zustand';
import { useCharacterLibrary } from './characters/useCharacterLibrary';
import {
  fetchGenerationHistory,
  requestGenerateImage,
  requestGenerateVideo,
  waitForGeneration,
  type GenerationVersion,
} from './generationApi';
import { ensureDirectorProject, getStoredUserId } from './scope';
import { captureScene } from './sceneApi';
import { useDirectorStore } from './store/useDirectorStore';

/** MiniMax 通常 2–4 分钟。用渐近曲线估算，完成前不到 100%。 */
export function estimateGenProgress(elapsedSec: number): number {
  if (elapsedSec <= 0) return 6;
  return Math.min(96, Math.round(95 * (1 - Math.exp(-elapsedSec / 90))));
}

function cleanMediaRef(url?: string | null): string | undefined {
  if (!url) return undefined;
  if (url.startsWith('data:') || url.startsWith('blob:')) return url;
  return url.split('?')[0].split('#')[0] || undefined;
}

export type GenKind = 'image' | 'video';
export type StepStatus = 'pending' | 'active' | 'done' | 'error';

export interface GenStep {
  key: string;
  label: string;
  status: StepStatus;
}

export const useGenerationRunner = create<{
  open: boolean;
  running: boolean;
  kind: GenKind | null;
  steps: GenStep[];
  error: string | null;
  lastVersion: GenerationVersion | null;
  startedAt: number | null;
  setOpen: (open: boolean) => void;
  generate: (kind: GenKind) => Promise<void>;
  resumeIfNeeded: () => Promise<void>;
}>((set, get) => ({
  open: false,
  running: false,
  kind: null,
  steps: [],
  error: null,
  lastVersion: null,
  startedAt: null,
  setOpen: (open) => set({ open }),
  resumeIfNeeded: async () => {
    if (get().running) return;
    const store = useDirectorStore.getState();
    if (!store.sceneId) return;
    try {
      const items = await fetchGenerationHistory(store.sceneId);
      const latest = [...items].reverse().find((item) => item.kind === 'video');
      if (!latest) return;
      if (latest.status === 'running' || latest.status === 'pending') {
        set({
          running: true,
          kind: 'video',
          startedAt: Date.now(),
          error: null,
          lastVersion: latest,
          steps: [
            { key: 'analyze', label: '分析镜头', status: 'done' },
            { key: 'prepare', label: '准备角色', status: 'done' },
            { key: 'render', label: '视频生成', status: 'active' },
          ],
        });
        try {
          const done = await waitForGeneration(latest.generation_id);
          useDirectorStore.getState().updateShotMeta({
            generationId: done.generation_id,
            videoUrl: done.url || null,
            videoPrompt: done.prompt,
          });
          set({ running: false, lastVersion: done, error: null, startedAt: null, steps: [
            { key: 'analyze', label: '分析镜头', status: 'done' },
            { key: 'prepare', label: '准备角色', status: 'done' },
            { key: 'render', label: '视频生成', status: 'done' },
          ] });
        } catch (err) {
          set({
            running: false,
            startedAt: null,
            error: err instanceof Error ? err.message : '生成失败',
            steps: [
              { key: 'analyze', label: '分析镜头', status: 'done' },
              { key: 'prepare', label: '准备角色', status: 'done' },
              { key: 'render', label: '视频生成', status: 'error' },
            ],
          });
        }
        return;
      }
      if (latest.status === 'completed' && latest.url && !store.videoUrl) {
        useDirectorStore.getState().updateShotMeta({
          generationId: latest.generation_id,
          videoUrl: latest.url,
          videoPrompt: latest.prompt,
        });
        set({ lastVersion: latest });
      }
    } catch {
      /* 历史拉不到时不挡出片 */
    }
  },
  generate: async (kind) => {
    if (get().running) return;
    const steps: GenStep[] = [
      { key: 'analyze', label: '分析镜头', status: 'active' },
      { key: 'prepare', label: '准备角色', status: 'pending' },
      { key: 'render', label: kind === 'image' ? '图片生成' : '视频生成', status: 'pending' },
    ];
    set({ running: true, kind, steps, error: null, lastVersion: null, startedAt: Date.now() });

    let projectId = '';
    try {
      projectId = await ensureDirectorProject();
    } catch {
      set({
        running: false,
        startedAt: null,
        error: '项目还没就绪，请先登录后再生成',
        steps: steps.map((s) => ({ ...s, status: s.key === 'analyze' ? 'error' : 'pending' })),
      });
      return;
    }

    const store = useDirectorStore.getState();
    const lib = useCharacterLibrary.getState();
    const context = {
      user_id: getStoredUserId(),
      project_id: projectId,
      scene_id: store.sceneId,
      scene_name: store.sceneName,
      objects: store.objects.map((o) => ({
        id: o.id,
        name: o.name,
        type: o.type,
        characterId: o.characterId,
        position: o.position,
        animation: o.animation,
        pose: o.pose,
      })),
      cameras: store.cameras,
      active_camera: store.activeCamera,
      environment: store.environment,
      relations: store.relations,
      project_name: store.projectName,
      chapter_name: store.chapterName,
      location_name: store.locationName,
      characters: lib.characters.map((c) => ({
        id: c.id,
        name: c.name,
        type: c.characterType,
      })),
    };
    const shot = {
      duration: store.shotDuration,
      shot_type: store.shotType,
      camera_movement: store.cameraMovement,
      visual_description: store.shotDescription,
      emotion: store.emotion,
      time_of_day: store.timeOfDay || store.environment.timeOfDay,
      weather: store.environment.weather,
      atmosphere: store.environment.atmosphere,
      camera: store.cameras.find((c) => c.id === store.activeCamera),
    };

    set({
      steps: steps.map((s) =>
        s.key === 'analyze' ? { ...s, status: 'done' } : s.key === 'prepare' ? { ...s, status: 'active' } : s,
      ),
    });

    let imageUrl = cleanMediaRef(store.imageUrl || store.compositionUrl || undefined);
    let imageDataUrl: string | undefined;
    if (kind === 'video' && !imageUrl) {
      try {
        const shotCap = await captureScene();
        imageDataUrl = shotCap.dataUrl;
      } catch (err) {
        set({
          running: false,
          startedAt: null,
          error: err instanceof Error ? err.message : '没有参考图，截图也失败。请先预览构图或生成图片。',
          steps: steps.map((s) => ({ ...s, status: s.key === 'render' ? 'error' : 'done' })),
        });
        return;
      }
    }

    set({
      steps: [
        { key: 'analyze', label: '分析镜头', status: 'done' },
        { key: 'prepare', label: '准备角色', status: 'done' },
        { key: 'render', label: kind === 'image' ? '图片生成' : '视频生成', status: 'active' },
      ],
    });

    try {
      const payload = {
        kind,
        scene_id: store.sceneId,
        shot_id: store.sceneId,
        parent_generation_id: store.generationId || undefined,
        aspect_ratio: store.aspectRatio,
        duration: store.shotDuration ?? 5,
        image_url: imageUrl,
        image_data_url: imageDataUrl,
        context,
        shot,
      };
      let result = kind === 'image'
        ? await requestGenerateImage(payload)
        : await requestGenerateVideo(payload);
      if (kind === 'video' && (result.status === 'running' || result.status === 'pending') && result.generation_id) {
        result = await waitForGeneration(result.generation_id);
      }
      useDirectorStore.getState().updateShotMeta({
        generationId: result.generation_id,
        imageUrl: result.kind === 'image' ? result.url || null : undefined,
        videoUrl: result.kind === 'video' ? result.url || null : undefined,
        imagePrompt: result.kind === 'image' ? result.prompt : undefined,
        videoPrompt: result.kind === 'video' ? result.prompt : undefined,
      });
      set({
        running: false,
        startedAt: null,
        lastVersion: result,
        error: null,
        steps: [
          { key: 'analyze', label: '分析镜头', status: 'done' },
          { key: 'prepare', label: '准备角色', status: 'done' },
          { key: 'render', label: kind === 'image' ? '图片生成' : '视频生成', status: 'done' },
        ],
      });
    } catch (err) {
      set({
        running: false,
        startedAt: null,
        error: err instanceof Error ? err.message : '生成失败',
        steps: [
          { key: 'analyze', label: '分析镜头', status: 'done' },
          { key: 'prepare', label: '准备角色', status: 'done' },
          { key: 'render', label: kind === 'image' ? '图片生成' : '视频生成', status: 'error' },
        ],
      });
    }
  },
}));
