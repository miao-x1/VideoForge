import axios from 'axios';

// 后端状态枚举(与 backend/app/models/state.py TaskStatus 保持一致)
export type TaskStatus =
  | 'PENDING'
  | 'ANALYZING'
  | 'SCRIPTING'
  | 'COMPLIANCE_CHECKING'
  | 'STORYBOARDING'
  | 'GENERATING_ASSETS'
  | 'ASSEMBLING'
  | 'COMPLETED'
  | 'FAILED'
  | 'HUMAN_REVIEW';

export interface LogEntry {
  ts: number;
  status: TaskStatus;
  message: string;
}

export interface CreateTaskReq {
  user_input: string;
  duration: number;
  style: string;
  aspect_ratio: string;
  compliance_enabled: boolean;
}

export interface TaskBrief {
  task_id: string;
  user_input: string;
  status: TaskStatus;
  created_at: number;
}

export interface StatusResp {
  task_id: string;
  status: TaskStatus;
  logs: LogEntry[];
  error: string | null;
}

export interface ResultResp {
  task_id: string;
  status: TaskStatus;
  video_path: string | null;
  video_url: string | null;
  title: string | null;
  created_at: number;
  // 各阶段结构化产物(后端渐进推送 / getResult 终态返回)
  requirement: any | null;
  script: any | null;
  storyboard: any | null;
  compliance_report: any | null;
  content_guard_report: any | null;
  quality_report: any | null;
  revision_count: number;
  human_review_required: boolean;
}

const http = axios.create({ baseURL: '' });

export const api = {
  createTask: (data: CreateTaskReq) =>
    http.post<TaskBrief>('/api/video/tasks', data).then((r) => r.data),
  getStatus: (taskId: string) =>
    http.get<StatusResp>(`/api/video/tasks/${taskId}/status`).then((r) => r.data),
  getResult: (taskId: string) =>
    http.get<ResultResp>(`/api/video/tasks/${taskId}/result`).then((r) => r.data),
};

// SSE 订阅,通过 EventSource 持续接收状态更新
// 断线自动重连(指数退避,最多 5 次),终态(COMPLETED/FAILED/HUMAN_REVIEW)后停止
export function subscribeTask(
  taskId: string,
  onUpdate: (payload: {
    task_id: string;
    status: TaskStatus;
    logs: LogEntry[];
    error: string | null;
    video_path: string | null;
    requirement: any | null;
    script: any | null;
    storyboard: any | null;
    compliance_report: any | null;
    content_guard_report: any | null;
    quality_report: any | null;
    revision_count: number;
    human_review_required: boolean;
  }) => void,
  onError?: () => void,
): { close: () => void } {
  const terminalStatuses: TaskStatus[] = ['COMPLETED', 'FAILED', 'HUMAN_REVIEW'];
  let retryCount = 0;
  const maxRetries = 5;
  let closed = false;
  let es: EventSource | null = null;

  const connect = () => {
    es = new EventSource(`/api/video/tasks/${taskId}/stream`);
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
