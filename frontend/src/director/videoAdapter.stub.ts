/**
 * Phase 2 reserved — Video Model Adapter (design only).
 *
 * Future chain:
 *   Agent → Video Generation Skill → Model Adapter → MiniMax H3 / other models
 *
 * API keys MUST live on the backend. Do not store MINIMAX_API_KEY in the frontend.
 */
import type { DirectorSceneState } from './types';

export interface VideoModelGenerateInput {
  screenshot: Blob;
  sceneState: DirectorSceneState;
  modelId?: string;
}

export interface VideoModelAdapter {
  id: string;
  generate(_input: VideoModelGenerateInput): Promise<never>;
}

export function createVideoModelAdapter(): VideoModelAdapter {
  throw new Error('Phase 2: Video Model Adapter is reserved and not implemented');
}
