import axios from 'axios';

// ---- 类型定义 ----

export type TaskStatus =
  | 'PENDING'
  | 'ANALYZING'
  | 'SCRIPTING'
  | 'COMPLIANCE_CHECKING'
  | 'SCRIPT_REVIEW'
  | 'STORYBOARDING'
  | 'STORYBOARD_REVIEW'
  | 'GENERATING_ASSETS'
  | 'PROMPT_REVIEW'
  | 'ASSEMBLING'
  | 'COMPLETED'
  | 'FAILED'
  | 'HUMAN_REVIEW';

export interface LogEntry {
  ts: number;
  status: TaskStatus;
  message: string;
}

export interface InputSourceItem {
  type: 'text' | 'image' | 'video' | 'url';
  content: string;
  purpose?: string;
}

export interface UploadResp {
  file_path: string;
  file_name: string;
  size: number;
}

export interface SearchResult {
  video_id: string;
  score: number;
  semantic_description: string;
  metadata: {
    title?: string;
    topic?: string;
    style?: string;
    duration?: number;
    quality_grade?: string;
    tags?: string[];
  };
  video_url: string | null;
}

export interface CreateTaskReq {
  user_input: string;
  duration: number;
  style: string;
  aspect_ratio: string;
  compliance_enabled: boolean;
  input_sources?: InputSourceItem[];
  preferred_model?: string;
  spec?: VideoSpecification | null;
  mode?: string;
  project_id?: string;
  confirmed_intent?: CreativeIntent | null;
}

export interface UnderstandReq {
  user_input: string;
  duration?: number;
  style?: string;
  aspect_ratio?: string;
  input_sources?: InputSourceItem[];
}

export interface UnderstandResp {
  creative_intent: CreativeIntent;
}

// ---- VideoSpecification 类型 ----

export interface CreativeElement {
  id?: string;
  type: string;
  name: string;
  description: string;
  attributes?: Record<string, any>;
  action?: string;
  reference_asset_id?: string | null;
  sort_order?: number;
}

export interface ReferenceAsset {
  id?: string;
  type: 'image' | 'video' | 'url';
  source: string;
  purpose: string;
  thumbnail?: string;
  description?: string;
}

export interface Environment {
  location?: string;
  time_of_day?: string;
  weather?: string;
  lighting?: string;
  lighting_type?: string;
  atmosphere?: string;
  color_palette?: string;
  color_temperature?: string;
  color_grading?: string;
}

export interface Narrative {
  structure?: string;
  theme?: string;
  mood?: string;
}

export interface MotionControl {
  subject_motion?: string;
  camera_motion?: string;
  environment_motion?: string;
}

export interface StyleItem {
  category?: string;
  name: string;
}

export interface CameraControl {
  shot_type?: string;
  angle?: string;
  movement?: string;
  rhythm?: string;
}

export interface AudioControl {
  bgm_mode?: string;
  bgm_path?: string;
  sfx_mode?: string;
  sfx_description?: string;
  dialogue_mode?: string;
  dialogue_text?: string;
  voice_style?: string;
}

export interface AdvancedParams {
  quality_priority?: string;
  compliance_enabled?: boolean;
  custom_params?: Record<string, any>;
}

export interface VideoSpecification {
  prompt: string;
  duration: number;
  aspect_ratio: string;
  target_platform?: string;
  creative_elements?: CreativeElement[];
  environment?: Environment | null;
  narrative?: Narrative | null;
  motion?: MotionControl | null;
  visual_style?: StyleItem[];
  custom_style?: string;
  camera?: CameraControl | null;
  audio?: AudioControl | null;
  references?: ReferenceAsset[];
  advanced?: AdvancedParams | null;
  preferred_model?: string;
  routing_decision?: Record<string, any> | null;
}

export interface AnalyzeReq {
  spec?: VideoSpecification | null;
  prompt?: string;
  duration?: number;
  style?: string;
  aspect_ratio?: string;
}

export interface AnalyzeResp {
  compiled_prompt: string;
  recommended_model: Record<string, any>;
  dimensions: Record<string, boolean>;
}

export interface TaskBrief {
  task_id: string;
  user_input: string;
  status: TaskStatus;
  created_at: number;
  model_used: string;
}

// ---- 项目 / 素材库 / 生成历史 ----

export interface ProjectInfo {
  id: string;
  title: string;
  description: string;
  cover_image: string | null;
  is_series: boolean;
  task_count: number;
  asset_count: number;
  created_at: number;
  updated_at: number;
}

export interface ProjectTaskBrief {
  task_id: string;
  user_input: string;
  status: TaskStatus;
  video_path: string | null;
  mode: string;
  model_used: string;
  created_at: number;
}

export interface AssetInfo {
  id: string;
  name: string;
  asset_type: string;
  description: string;
  file_path: string | null;
  media_type: string | null;
  project_id: string | null;
  metadata: Record<string, any> | null;
  created_at: number;
}

export interface ProjectDetail {
  id: string;
  title: string;
  description: string;
  cover_image: string | null;
  is_series: boolean;
  memory: Record<string, any>;
  created_at: number;
  tasks: ProjectTaskBrief[];
  assets: AssetInfo[];
}

export interface HistoryEntry {
  task_id: string;
  user_input: string;
  duration: number;
  style: string;
  aspect_ratio: string;
  mode: string;
  status: TaskStatus;
  video_path: string | null;
  quality_grade: string | null;
  model_used: string;
  project_id: string | null;
  created_at: number;
}

export interface ModelInfo {
  provider: string;
  model: string;
  capabilities: {
    max_duration: number;
    supported_ratios: string[];
    max_resolution: string;
    quality_score: number;
    speed_score: number;
    cost_per_sec: number;
    supports_image_input: boolean;
    supports_video_input: boolean;
    supports_audio_output: boolean;
    supports_text_to_video: boolean;
    supports_first_frame: boolean;
    supports_last_frame: boolean;
    supports_motion_control: boolean;
    supports_negative_prompt: boolean;
  };
}

export type RoutingStrategy = 'auto' | 'best_quality' | 'lowest_cost' | 'fastest' | 'manual';

export interface RegistryModel {
  model_id: string;
  provider: string;
  model_name: string;
  model_type: string;
  capabilities: Record<string, any>;
  input_types: string[];
  output_types: string[];
  quality_score: number;
  speed_score: number;
  cost_score: number;
  context_length: number;
  supported_styles: string[];
  supported_durations: number[];
  supported_aspect_ratios: string[];
  supports_reference_image: boolean;
  supports_reference_video: boolean;
  supports_audio: boolean;
  supports_video_extension: boolean;
  supports_image_to_video: boolean;
  supports_text_to_video: boolean;
  supports_negative_prompt: boolean;
  enabled: boolean;
  priority: number;
}

export interface RoutingDecision {
  selected_provider: string;
  selected_model: string;
  selected_model_id: string;
  model_type: string;
  strategy: string;
  reason: string;
  profile: Record<string, any>;
  scored_models: Array<{
    model_id: string;
    provider: string;
    model: string;
    model_type: string;
    total_score: number;
    quality_score: number;
    speed_score: number;
    cost_score: number;
    fit_score: number;
    reason: string;
  }>;
  quality_stars: number;
  speed_stars: number;
  cost_stars: number;
}

export interface StatusResp {
  task_id: string;
  status: TaskStatus;
  logs: LogEntry[];
  error: string | null;
}

export interface CreativeIntent {
  concept: string;
  subject: string;
  subject_description: string;
  scene: string;
  scene_description: string;
  action: string;
  action_description: string;
  emotion: string;
  visual_style: string;
  camera_style: string;
  lighting: string;
  color_mood: string;
  duration: number;
  aspect_ratio: string;
  references: string[];
  creative_goal: string;
  constraints: string[];
  inferred_needs: string[];
}

export interface VideoVersionInfo {
  version: number;
  url: string;
  reason: string;
  ts: number;
  current: boolean;
}

export interface SubtitleItem {
  shot_index: number;
  text: string;
  enabled: boolean;
  font_size: number;
  start: number;
  end: number;
}

export interface TimelineSegment {
  shot_index: number;
  start: number;
  end: number;
  duration: number;
  narration_path: string | null;
  narration_duration: number | null;
  subtitle_text: string;
  subtitle_enabled: boolean;
}

export interface ResultResp {
  task_id: string;
  status: TaskStatus;
  video_path: string | null;
  video_url: string | null;
  video_versions?: VideoVersionInfo[];
  title: string | null;
  created_at: number;
  model_used: string | null;
  routing_decision: any | null;
  image_model_used: string | null;
  image_routing_decision: any | null;
  voice_model_used: string | null;
  creative_intent: CreativeIntent | null;
  prompt_engineering_result: any | null;
  requirement: any | null;
  script: any | null;
  storyboard: any | null;
  compliance_report: any | null;
  content_guard_report: any | null;
  quality_report: any | null;
  project_state?: ProjectState | null;
  revision_count: number;
  human_review_required: boolean;
  failure_detail?: any | null;
}

export interface UserOut {
  id: string;
  email: string;
  phone?: string;
  display_name: string;
  created_at: number;
}

export interface CaptchaResp {
  captcha_id: string;
  image: string;
  debug_text?: string | null;
}

export interface SendCodeResp {
  ok: boolean;
  cooldown: number;
  message: string;
  dev_code?: string | null;
}

export interface AuthStatus {
  sms_configured: boolean;
  email_configured: boolean;
  password_login: boolean;
}

export interface BillingPackage {
  id: string;
  yuan: number;
  fen: number;
  label: string;
}

export interface BillingCatalogItem {
  provider: string;
  model: string;
  label: string;
  price_fen_per_sec: number;
  available: boolean;
  region: string;
}

export interface BillingCredential {
  provider: string;
  last4: string;
  base_url: string;
  enabled: boolean;
}

export interface BillingLedgerItem {
  id: number;
  delta_fen: number;
  balance_after: number;
  kind: string;
  note: string;
  created_at: number;
}

export interface BillingStatus {
  video_source: 'platform' | 'own';
  video_provider: string;
  video_model: string;
  wallet: { balance_fen: number; balance_yuan: string };
  credentials: BillingCredential[];
  catalog: BillingCatalogItem[];
  packages: BillingPackage[];
  price_fen_per_sec: number;
  dev_recharge: boolean;
  platform_ready: boolean;
  wallet_kind?: 'platform_ledger';
  recharge_kind?: 'dev_credit' | 'payment_pending';
  wallet_note?: string;
  minimax_note?: string;
}

export const billingApi = {
  status: () => http.get<BillingStatus>('/api/billing/status').then((r) => r.data),
  updatePrefs: (data: { video_source?: 'platform' | 'own'; video_provider?: string; video_model?: string }) =>
    http.put<BillingStatus>('/api/billing/prefs', data).then((r) => r.data),
  saveCredential: (data: { provider: string; api_key: string; base_url?: string }) =>
    http.put<{ ok: boolean; credential: BillingCredential }>('/api/billing/credentials', data).then((r) => r.data),
  deleteCredential: (provider: string) =>
    http.delete<{ ok: boolean; deleted: boolean }>(`/api/billing/credentials/${provider}`).then((r) => r.data),
  ledger: (limit = 12) =>
    http.get<{ items: BillingLedgerItem[] }>('/api/billing/ledger', { params: { limit } }).then((r) => r.data),
  recharge: (data: { package_id?: string; yuan?: number }) =>
    http.post<BillingStatus>('/api/billing/recharge', data).then((r) => r.data),
};

// ---- 版本控制 ----

export interface TaskVersionNodeInfo {
  node_type: string;
  label: string;
  latest_version: number;
  version_count: number;
  latest_reason: string;
  latest_ts: number;
}

export interface TaskVersionEntry {
  version: number;
  ts: number;
  label: string;
  reason: string;
  data?: any;
}

// ---- 项目记忆 ----

export interface ProjectMemory {
  settings?: Record<string, any>;
  subjects?: string[];
  scenes?: string[];
  styles?: string[];
  prompts?: { model_id: string; shot_index: number; text: string }[];
  videos?: { task_id: string; video_path: string; model?: string; grade?: string }[];
  modifications?: { node_type: string; version: number; reason: string }[];
  script_summary?: Record<string, any>;
  storyboard_summary?: Record<string, any>;
}

// ---- ProjectState(AI Director 作品级状态) ----

export interface CharacterRelation {
  target_name: string;
  relation: string;
  description: string;
}

export interface CharacterBible {
  character_id: string;
  name: string;
  age: string;
  gender: string;
  identity: string;
  personality: string;
  appearance: string;
  hairstyle: string;
  clothing: string;
  body_type: string;
  speech_style: string;
  emotion_traits: string;
  relations: CharacterRelation[];
  background: string;
  visual_keywords: string[];
  reference_asset_ids: string[];
  status: string;
}

export interface SceneSetting {
  scene_key: string;
  name: string;
  location: string;
  time_of_day: string;
  weather: string;
  lighting: string;
  description: string;
}

export interface WorldBible {
  era: string;
  region: string;
  architecture: string;
  weather_base: string;
  time_span: string;
  props_system: string[];
  world_rules: string;
  scenes: SceneSetting[];
}

export interface StyleBible {
  visual_style: string;
  photography_style: string;
  color_palette: string;
  color_temperature: string;
  saturation: string;
  contrast: string;
  color_grading: string;
  lighting_base: string;
  lens_language: string;
  texture: string;
  negative_keywords: string[];
}

export interface ProjectInfo {
  project_id: string | null;
  title: string;
  genre: string;
  duration_target: number;
  aspect_ratio: string;
  language: string;
}

export interface StoryBeat {
  beat_id: string;
  name: string;
  summary: string;
  emotion: string;
  scene_refs: number[];
}

export interface CharacterArc {
  character_id: string;
  arc_summary: string;
  start_state: string;
  end_state: string;
}

export interface StoryState {
  theme: string;
  logline: string;
  core_conflict: string;
  ending_tone: string;
  beats: StoryBeat[];
  character_arcs: CharacterArc[];
}

export interface CharacterState {
  bibles: CharacterBible[];
  current_status: Record<string, string>;
}

export interface SceneStateEntry {
  scene_id: number;
  name: string;
  location: string;
  time_of_day: string;
  weather: string;
  lighting: string;
  characters: string[];
  summary: string;
  shot_count: number;
  status: string;
}

export interface ShotStateEntry {
  shot_index: number;
  scene_id: number;
  characters: string[];
  location: string;
  time_of_day: string;
  action: string;
  emotion_start: string;
  emotion_end: string;
  camera: string;
  camera_motion: string;
  lighting: string;
  dialogue: string;
  sound: string;
  continuity_in: string;
  continuity_out: string;
  causal_note: string;
  prev_shot: number | null;
  next_shot: number | null;
  ref_asset_ids: string[];
  desired_mode: string;
  desired_duration: number;
  status: string;
}

export interface GenerationDecision {
  shot_index: number;
  provider: string;
  model: string;
  mode: string;
  reference_asset_ids: string[];
  attempt: number;
  reason: string;
  status: string;
}

export interface QualityCheck {
  dimension: string;
  passed: boolean;
  note: string;
}

export interface QualityReportItem {
  shot_index: number;
  attempt: number;
  passed: boolean;
  checks: QualityCheck[];
  issues: string[];
  judge_note: string;
  repair_hint: string;
}

export interface ProjectState {
  project_info: ProjectInfo;
  story_state: StoryState;
  character_state: CharacterState;
  world_state: { bible: WorldBible | null };
  style_state: { bible: StyleBible | null };
  scene_state: { scenes: SceneStateEntry[] };
  shot_state: { shots: ShotStateEntry[] };
  asset_state: { assets: any[] };
  generation_state: {
    current_stage: string;
    decisions: GenerationDecision[];
    completed_shots: number[];
    failed_shots: number[];
  };
  audio_state: { cues: any[]; music_mood: string; music_style: string; bgm_asset_id: string | null };
  editing_state: {
    shot_order: number[];
    transitions: Record<string, string>;
    pacing_note: string;
    subtitle_enabled: boolean;
    decision_source: string;
    final_video_asset_id: string | null;
  };
  quality_state: {
    reports: QualityReportItem[];
    passed_shots: number[];
    failed_shots: number[];
  };
  updated_at: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserOut;
}

// ---- Axios 实例 ----

export function getAccessToken(): string | null {
  return localStorage.getItem('vf_token');
}

/** 给 /storage 资源补上 access_token，供 <img>/<video> 在生产受控访问。 */
export function mediaUrl(path: string): string {
  if (!path) return path;
  if (path.startsWith('data:') || path.startsWith('blob:')) return path;
  const token = getAccessToken();
  if (!token) return path;
  try {
    const url = new URL(path, window.location.origin);
    const managed = url.pathname.startsWith('/storage/') || url.pathname.startsWith('/api/director/assets/');
    if (!managed) return path;
    if (!url.searchParams.has('access_token')) url.searchParams.set('access_token', token);
    return `${url.pathname}${url.search}`;
  } catch {
    return path;
  }
}

const http = axios.create({ baseURL: '' });

export { http as apiHttp };

// 请求拦截器:自动附加 Authorization 头；导演台接口补上 project_id
http.interceptors.request.use(async (config) => {
  const token = localStorage.getItem('vf_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const url = String(config.url || '');
  if (url.includes('/api/director')) {
    const params = { ...(config.params || {}) };
    let pid = String(params.project_id || '').trim();
    if (!pid) {
      const scope = await import('../director/scope');
      pid = scope.getDirectorProjectId();
      if (!pid && token) {
        try {
          pid = await scope.ensureDirectorProject();
        } catch {
          pid = '';
        }
      }
    }
    if (pid) {
      params.project_id = pid;
      config.params = params;
    }
  }
  return config;
});

// 只在会话真的失效时回登录。业务 401（密码错、模型余额不足）不得清登录态。
const AUTH_LOST = new Set([
  '未提供认证信息',
  '认证信息无效或已过期',
  '认证信息无效',
  '用户不存在',
]);

http.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error?.response?.status;
    const url = String(error?.config?.url || '');
    const detail = error?.response?.data?.detail;
    const authEndpoint = /\/api\/auth\/(login|login-sms|register|send-code|reset-password|captcha)/.test(url);
    const optionalAuth = /\/api\/billing\//.test(url);
    if (
      status === 401
      && !authEndpoint
      && !optionalAuth
      && typeof detail === 'string'
      && AUTH_LOST.has(detail)
    ) {
      localStorage.removeItem('vf_token');
      localStorage.removeItem('vf_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

// ---- Auth API ----

export const authApi = {
  status: () => http.get<AuthStatus>('/api/auth/status').then((r) => r.data),
  captcha: () => http.get<CaptchaResp>('/api/auth/captcha').then((r) => r.data),
  sendCode: (data: { account: string; purpose: 'register' | 'login' | 'reset'; captcha_id: string; captcha_code: string }) =>
    http.post<SendCodeResp>('/api/auth/send-code', data).then((r) => r.data),
  register: (data: {
    account: string;
    password: string;
    display_name?: string;
    captcha_id: string;
    captcha_code: string;
    verify_code?: string;
    agree: boolean;
  }) => http.post<TokenResponse>('/api/auth/register', data).then((r) => r.data),
  login: (data: {
    account: string;
    password: string;
    captcha_id: string;
    captcha_code: string;
    remember?: boolean;
  }) => http.post<TokenResponse>('/api/auth/login', data).then((r) => r.data),
  loginSms: (data: {
    account: string;
    verify_code: string;
    captcha_id: string;
    captcha_code: string;
    remember?: boolean;
  }) => http.post<TokenResponse>('/api/auth/login-sms', data).then((r) => r.data),
  resetPassword: (data: { account: string; verify_code: string; password: string }) =>
    http.post<{ ok: boolean; message: string }>('/api/auth/reset-password', data).then((r) => r.data),
  me: () =>
    http.get<UserOut>('/api/auth/me').then((r) => r.data),
};

// ---- Video API ----

export const api = {
  createTask: (data: CreateTaskReq) =>
    http.post<TaskBrief>('/api/video/tasks', data).then((r) => r.data),
  listTasks: () =>
    http.get<TaskBrief[]>('/api/video/tasks').then((r) => r.data),
  getStatus: (taskId: string) =>
    http.get<StatusResp>(`/api/video/tasks/${taskId}/status`).then((r) => r.data),
  getTask: (taskId: string) =>
    http.get<any>(`/api/video/tasks/${taskId}`).then((r) => r.data),
  getResult: (taskId: string) =>
    http.get<ResultResp>(`/api/video/tasks/${taskId}/result`).then((r) => r.data),
  uploadImage: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return http.post<UploadResp>('/api/upload/image', fd).then((r) => r.data);
  },
  uploadVideo: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return http.post<UploadResp>('/api/upload/video', fd).then((r) => r.data);
  },
  searchVideos: (q: string, topK = 5) =>
    http.get<SearchResult[]>(`/api/video/search?q=${encodeURIComponent(q)}&top_k=${topK}`).then((r) => r.data),
  listModels: () =>
    http.get<ModelInfo[]>('/api/video/models').then((r) => r.data),
  listRegistryModels: (modelType?: string) =>
    http.get<RegistryModel[]>('/api/video/models/registry', {
      params: modelType ? { model_type: modelType } : {},
    }).then((r) => r.data),
  switchModel: (taskId: string, modelId: string) =>
    http.post<{ task_id: string; status: string; message: string }>(
      `/api/video/tasks/${taskId}/model/select`,
      { model_id: modelId },
    ).then((r) => r.data),
  retryTask: (taskId: string) =>
    http.post<{ task_id: string; status: string; message: string }>(
      `/api/video/tasks/${taskId}/retry`,
      { retry: true },
    ).then((r) => r.data),
  // ---- 字幕编辑 + 音轨时间轴 ----
  getSubtitles: (taskId: string) =>
    http.get<{ task_id: string; items: SubtitleItem[] }>(
      `/api/video/tasks/${taskId}/subtitles`,
    ).then((r) => r.data),
  updateSubtitles: (taskId: string, items: SubtitleItem[]) =>
    http.put<{ task_id: string; status: string; message: string }>(
      `/api/video/tasks/${taskId}/subtitles`,
      { items },
    ).then((r) => r.data),
  getTimeline: (taskId: string) =>
    http.get<{ task_id: string; segments: TimelineSegment[]; bgm: string | null; total_duration: number }>(
      `/api/video/tasks/${taskId}/timeline`,
    ).then((r) => r.data),
  analyzeShotImpact: (taskId: string, shotIndices: number[]) =>
    http.post<{ task_id: string; affected: number[]; unaffected: number[]; locked: number[]; message: string }>(
      `/api/video/tasks/${taskId}/shots/impact`,
      { shot_indices: shotIndices },
    ).then((r) => r.data),
  toggleShotLock: (taskId: string, shotIndex: number, locked: boolean) =>
    http.post<{ task_id: string; shot_index: number; locked: boolean }>(
      `/api/video/tasks/${taskId}/shots/${shotIndex}/lock`,
      { locked },
    ).then((r) => r.data),
  reviseShots: (taskId: string, shotIndices: number[], edits?: Record<string, any>, feedback?: string) =>
    http.post<{ task_id: string; status: string; message: string }>(
      `/api/video/tasks/${taskId}/shots/revise`,
      { shot_indices: shotIndices, edits: edits ?? null, feedback: feedback || null },
    ).then((r) => r.data),
  analyzeSceneImpact: (taskId: string, sceneIndex: number) =>
    http.post<{ task_id: string; scene_index: number; scene_id: number; affected: number[]; unaffected: number[]; locked: number[]; message: string }>(
      `/api/video/tasks/${taskId}/scenes/${sceneIndex}/impact`,
    ).then((r) => r.data),
  reviseScene: (taskId: string, sceneIndex: number, sceneEdits?: Record<string, any>, feedback?: string) =>
    http.post<{ task_id: string; status: string; message: string }>(
      `/api/video/tasks/${taskId}/scenes/${sceneIndex}/revise`,
      { scene_edits: sceneEdits ?? null, feedback: feedback || null },
    ).then((r) => r.data),
  recommendModel: (q: string, duration: number, style: string, aspectRatio: string, preferredModel?: string, strategy?: RoutingStrategy) =>
    http.get<RoutingDecision>('/api/video/models/recommend', {
      params: { q, duration, style, aspect_ratio: aspectRatio, preferred_model: preferredModel || '', strategy: strategy || 'auto' },
    }).then((r) => r.data),
  analyzeCreativeIntent: (data: AnalyzeReq) =>
    http.post<AnalyzeResp>('/api/video/analyze', data).then((r) => r.data),
  understandCreative: (data: UnderstandReq) =>
    http.post<UnderstandResp>('/api/video/understand', data).then((r) => r.data),
  confirmScript: (taskId: string, script?: Record<string, any> | null) =>
    http.post<{ task_id: string; status: string; message: string }>(
      `/api/video/tasks/${taskId}/script/confirm`,
      { script: script ?? null },
    ).then((r) => r.data),
  regenerateScript: (taskId: string, feedback?: string) =>
    http.post<{ task_id: string; status: string; message: string }>(
      `/api/video/tasks/${taskId}/script/regenerate`,
      feedback ? { feedback } : undefined,
    ).then((r) => r.data),
  confirmStoryboard: (taskId: string, storyboard?: Record<string, any> | null) =>
    http.post<{ task_id: string; status: string; message: string }>(
      `/api/video/tasks/${taskId}/storyboard/confirm`,
      { storyboard: storyboard ?? null },
    ).then((r) => r.data),
  regenerateStoryboard: (taskId: string, shotIndex?: number | null, feedback?: string) =>
    http.post<{ task_id: string; status: string; message: string }>(
      `/api/video/tasks/${taskId}/storyboard/regenerate`,
      { shot_index: shotIndex ?? null, feedback: feedback || null },
    ).then((r) => r.data),
  confirmPrompt: (taskId: string, promptResult?: Record<string, any> | null) =>
    http.post<{ task_id: string; status: string; message: string }>(
      `/api/video/tasks/${taskId}/prompt/confirm`,
      { prompt_result: promptResult ?? null },
    ).then((r) => r.data),
  regeneratePrompt: (taskId: string, feedback?: string) =>
    http.post<{ task_id: string; status: string; message: string }>(
      `/api/video/tasks/${taskId}/prompt/regenerate`,
      feedback ? { feedback } : undefined,
    ).then((r) => r.data),
  // ---- 版本控制(任务级) ----
  listTaskVersions: (taskId: string) =>
    http.get<{ task_id: string; nodes: TaskVersionNodeInfo[] }>(
      `/api/video/tasks/${taskId}/versions`,
    ).then((r) => r.data),
  getTaskVersionHistory: (taskId: string, nodeType: string, includeData = false) =>
    http.get<{ task_id: string; node_type: string; versions: TaskVersionEntry[] }>(
      `/api/video/tasks/${taskId}/versions/${nodeType}`,
      { params: { include_data: includeData } },
    ).then((r) => r.data),
  restoreTaskVersion: (taskId: string, nodeType: string, version: number) =>
    http.post<{ task_id: string; node_type: string; version: number; restored: boolean; message: string }>(
      `/api/video/tasks/${taskId}/versions/${nodeType}/restore/${version}`,
    ).then((r) => r.data),
  // ---- 项目记忆 ----
  getProjectMemory: (projectId: string) =>
    http.get<{ project_id: string; memory: ProjectMemory; summary: Record<string, number> }>(
      `/api/projects/${projectId}/memory`,
    ).then((r) => r.data),
  // ---- 作品设定编辑 ----
  updateProjectState: (taskId: string, projectState: ProjectState) =>
    http.put<{ task_id: string; updated: boolean }>(
      `/api/video/tasks/${taskId}/project-state`,
      { project_state: projectState },
    ).then((r) => r.data),
  // ---- 剧本局部 AI(续写/改写/扩写/缩写) ----
  scriptSceneAI: (taskId: string, body: {
    scene_index: number;
    action: 'continue' | 'rewrite' | 'expand' | 'condense';
    instruction?: string;
    scene: Record<string, any>;
  }) =>
    http.post<{ task_id: string; action: string; scene: Record<string, any> }>(
      `/api/video/tasks/${taskId}/script/scene-ai`, body,
    ).then((r) => r.data),
  // ---- 项目 / 素材库 / 生成历史 ----
  listProjects: () =>
    http.get<{ projects: ProjectInfo[] }>('/api/projects').then((r) => r.data.projects),
  createProject: (data: { title: string; description?: string; is_series?: boolean }) =>
    http.post<ProjectInfo>('/api/projects', data).then((r) => r.data),
  getProject: (projectId: string) =>
    http.get<ProjectDetail>(`/api/projects/${projectId}`).then((r) => r.data),
  deleteProject: (projectId: string) =>
    http.delete<{ deleted: boolean; id: string }>(`/api/projects/${projectId}`).then((r) => r.data),
  listAssets: (params?: { asset_type?: string; project_id?: string }) =>
    http.get<{ assets: AssetInfo[] }>('/api/assets', { params }).then((r) => r.data.assets),
  deleteAsset: (assetId: string) =>
    http.delete<{ deleted: boolean; id: string }>(`/api/assets/${assetId}`).then((r) => r.data),
  listHistory: (params?: { project_id?: string; limit?: number; offset?: number }) =>
    http.get<{ history: HistoryEntry[]; total: number }>('/api/history', { params }).then((r) => r.data),
};

// ---- SSE 订阅 ----

export function subscribeTask(
  taskId: string,
  onUpdate: (payload: {
    task_id: string;
    status: TaskStatus;
    logs: LogEntry[];
    error: string | null;
    video_path: string | null;
    failure_detail: any | null;
    model_used: string | null;
    routing_decision: any | null;
    image_model_used: string | null;
    image_routing_decision: any | null;
    voice_model_used: string | null;
    creative_intent: CreativeIntent | null;
    prompt_engineering_result: any | null;
    requirement: any | null;
    script: any | null;
    storyboard: any | null;
    compliance_report: any | null;
    content_guard_report: any | null;
    quality_report: any | null;
    project_state?: ProjectState | null;
    revision_count: number;
    human_review_required: boolean;
  }) => void,
  onError?: () => void,
): { close: () => void } {
  const terminalStatuses: TaskStatus[] = ['COMPLETED', 'FAILED', 'HUMAN_REVIEW', 'SCRIPT_REVIEW', 'STORYBOARD_REVIEW', 'PROMPT_REVIEW'];
  let retryCount = 0;
  const maxRetries = 5;
  let closed = false;
  let es: EventSource | null = null;

  const connect = () => {
    // SSE 需要通过 URL 传递 token(Fetch API 不支持自定义头)
    const token = localStorage.getItem('vf_token') || '';
    const url = `/api/video/tasks/${taskId}/stream?token=${encodeURIComponent(token)}`;
    es = new EventSource(url);
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        onUpdate(data);
        if (terminalStatuses.includes(data.status)) {
          closed = true;
          es?.close();
        }
      } catch {
        // 忽略解析异常
      }
    };
    es.onerror = () => {
      es?.close();
      if (closed) return;
      if (retryCount < maxRetries) {
        retryCount += 1;
        const delay = Math.min(1000 * 2 ** retryCount, 10000);
        setTimeout(connect, delay);
      } else {
        onError?.();
      }
    };
  };
  connect();

  return {
    close: () => {
      closed = true;
      es?.close();
    },
  };
}
