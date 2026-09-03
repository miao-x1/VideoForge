import { create } from 'zustand';
import type {
  VideoSpecification,
  AnalyzeResp,
  TaskStatus,
  LogEntry,
  ResultResp,
  CreativeIntent,
} from '../api/client';

const defaultSpec: VideoSpecification = {
  prompt: '',
  duration: 30,
  aspect_ratio: '9:16',
  target_platform: '',
  creative_elements: [],
  environment: null,
  narrative: null,
  motion: null,
  visual_style: [],
  custom_style: '',
  camera: null,
  audio: null,
  references: [],
  advanced: null,
  preferred_model: '',
  routing_decision: null,
};

type CreativeMode = 'quick' | 'professional';

interface CreativeStore {
  // 创作状态
  spec: VideoSpecification;
  mode: CreativeMode;

  // 分析预览
  analysis: AnalyzeResp | null;
  analysisLoading: boolean;

  // 任务执行状态
  taskLoading: boolean;
  taskStatus: TaskStatus | null;
  taskError: string | null;
  taskFailureDetail: any | null;
  taskModelUsed: string | null;
  taskRoutingDecision: any | null;
  taskCreativeIntent: CreativeIntent | null;
  taskScript: any | null;
  taskStoryboard: any | null;
  taskPromptEngineeringResult: any | null;
  taskLogs: LogEntry[];
  taskResult: ResultResp | null;
  taskId: string | null;

  // 创作动作
  updateSpec: (partial: Partial<VideoSpecification>) => void;
  setSpec: (spec: VideoSpecification) => void;
  setMode: (mode: CreativeMode) => void;
  resetSpec: () => void;

  // 分析动作
  setAnalysis: (result: AnalyzeResp | null) => void;
  setAnalysisLoading: (loading: boolean) => void;

  // 任务动作
  setTaskLoading: (loading: boolean) => void;
  setTaskStatus: (status: TaskStatus | null) => void;
  setTaskError: (error: string | null) => void;
  setTaskFailureDetail: (detail: any | null) => void;
  setTaskModelUsed: (model: string | null) => void;
  setTaskRoutingDecision: (decision: any | null) => void;
  setTaskCreativeIntent: (intent: CreativeIntent | null) => void;
  setTaskScript: (script: any | null) => void;
  setTaskStoryboard: (storyboard: any | null) => void;
  setTaskPromptEngineeringResult: (result: any | null) => void;
  setTaskLogs: (logs: LogEntry[]) => void;
  setTaskResult: (result: ResultResp | null) => void;
  setTaskId: (id: string | null) => void;
  resetTask: () => void;
}

export const useCreativeStore = create<CreativeStore>((set) => ({
  spec: { ...defaultSpec },
  mode: 'quick',

  analysis: null,
  analysisLoading: false,

  taskLoading: false,
  taskStatus: null,
  taskError: null,
  taskFailureDetail: null,
  taskModelUsed: null,
  taskRoutingDecision: null,
  taskCreativeIntent: null,
  taskScript: null,
  taskStoryboard: null,
  taskPromptEngineeringResult: null,
  taskLogs: [],
  taskResult: null,
  taskId: null,

  updateSpec: (partial) =>
    set((state) => ({
      spec: { ...state.spec, ...partial },
    })),

  setSpec: (spec) => set({ spec }),

  setMode: (mode) => set({ mode }),

  resetSpec: () => set({ spec: { ...defaultSpec }, analysis: null }),

  setAnalysis: (result) => set({ analysis: result }),
  setAnalysisLoading: (loading) => set({ analysisLoading: loading }),

  setTaskLoading: (loading) => set({ taskLoading: loading }),
  setTaskStatus: (status) => set({ taskStatus: status }),
  setTaskError: (error) => set({ taskError: error }),
  setTaskFailureDetail: (detail) => set({ taskFailureDetail: detail }),
  setTaskModelUsed: (model) => set({ taskModelUsed: model }),
  setTaskRoutingDecision: (decision) => set({ taskRoutingDecision: decision }),
  setTaskCreativeIntent: (intent) => set({ taskCreativeIntent: intent }),
  setTaskScript: (script) => set({ taskScript: script }),
  setTaskStoryboard: (storyboard) => set({ taskStoryboard: storyboard }),
  setTaskPromptEngineeringResult: (result) => set({ taskPromptEngineeringResult: result }),
  setTaskLogs: (logs) => set({ taskLogs: logs }),
  setTaskResult: (result) => set({ taskResult: result }),
  setTaskId: (id) => set({ taskId: id }),
  resetTask: () =>
    set({
      taskLoading: false,
      taskStatus: null,
      taskError: null,
      taskFailureDetail: null,
      taskModelUsed: null,
      taskRoutingDecision: null,
      taskCreativeIntent: null,
      taskScript: null,
      taskStoryboard: null,
      taskPromptEngineeringResult: null,
      taskLogs: [],
      taskResult: null,
      taskId: null,
    }),
}));
