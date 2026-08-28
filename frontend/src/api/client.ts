import axios from 'axios';

// 后端状态枚举(与 backend/app/models/state.py TaskStatus 保持一致)
export type TaskStatus =
  | 'PENDING'
  | 'ANALYZING'
  | 'SCRIPTING'
  | 'STORYBOARDING'
  | 'GENERATING_ASSETS'
  | 'ASSEMBLING'
  | 'COMPLETED'
  | 'FAILED';

export interface LogEntry {
  ts: number;
  status: TaskStatus;
  message: string;
}

export interface CreateTaskReq {
  user_input: string;
  duration: number;
  style: string;
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
export function subscribeTask(
  taskId: string,
  onUpdate: (payload: {
    task_id: string;
    status: TaskStatus;
    logs: LogEntry[];
    error: string | null;
    video_path: string | null;
  }) => void,
  onError?: () => void,
): EventSource {
  const es = new EventSource(`/api/video/tasks/${taskId}/stream`);
  es.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      onUpdate(data);
    } catch {
      // 忽略解析异常
    }
  };
  es.onerror = () => {
    es.close();
    onError?.();
  };
  return es;
}
