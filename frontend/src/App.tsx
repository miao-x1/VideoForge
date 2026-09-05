import { Component, lazy, Suspense, useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Layout, Typography, message, Spin, Steps, Empty, Tabs } from 'antd';
import CreativeBrief, { CreativeBriefValue } from './components/CreativeBrief';
import IntentReview from './components/IntentReview';
import ScriptReview from './components/ScriptReview';
import StoryboardReview from './components/StoryboardReview';
import PromptReview from './components/PromptReview';
import ShotRevisePanel from './components/ShotRevisePanel';
import SceneRevisePanel from './components/SceneRevisePanel';
import ProjectMemoryPanel from './components/ProjectMemoryPanel';
import ProjectAssetsPanel from './components/ProjectAssetsPanel';
import VersionHistoryPanel from './components/VersionHistoryPanel';
import WorkspacePage from './components/WorkspacePage';
import NodeNav, { type NodeKey } from './components/NodeNav';
import ShotsMediaGallery, { AssetsPanel, type GalleryShot } from './components/ShotsMediaGallery';
import { CreativeRecap, IntentSummary } from './components/NodeRecap';
import ProgressTimeline from './components/ProgressTimeline';
import FailureRecoveryCard from './components/FailureRecoveryCard';
import SubtitleEditor from './components/SubtitleEditor';
import ScriptViewer from './components/ScriptViewer';
import StoryboardViewer from './components/StoryboardViewer';
import PromptInspector from './components/PromptInspector';
import VideoResult from './components/VideoResult';
import BiblePanel from './components/BiblePanel';
import UserMenu from './components/UserMenu';
import AIPlanPanel from './components/AIPlanPanel';
import LoginPage from './pages/LoginPage';
import HistoryPage from './pages/HistoryPage';
import MarketplaceStubPage from './pages/MarketplaceStubPage';

const DirectorDeskPage = lazy(() => import('./director/DirectorDeskPage'));

class DeskGuard extends Component<{ children: ReactNode }, { error: string | null }> {
  state = { error: null as string | null };
  static getDerivedStateFromError(error: Error) {
    return { error: error?.message || '导演台渲染失败' };
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0e0d0b', color: '#f4f1ea', flexDirection: 'column', gap: 12, padding: 24 }}>
          <div style={{ fontWeight: 700 }}>导演台打不开</div>
          <div style={{ fontSize: 12, color: '#8a8680', maxWidth: 520, textAlign: 'center' }}>{this.state.error}</div>
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #c7b89c', background: 'transparent', color: '#c7b89c', cursor: 'pointer' }}
          >
            刷新重试
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
import { useAuth } from './hooks/useAuth';
import { useCreativeStore } from './store/useCreativeStore';
import { api, subscribeTask } from './api/client';
import type { CreativeIntent, ProjectState, TaskStatus } from './api/client';
import { cardStyle, colors } from './theme';

const { Header, Content } = Layout;
const { Title: PageTitle, Paragraph } = Typography;

/** 顶部创作流程:01创意 02方案 03设定 04剧本 05分镜 06Prompt 07生成 08质检 09成片 */
const FLOW_STEPS = [
  { title: '创意' },
  { title: '方案' },
  { title: '设定' },
  { title: '剧本' },
  { title: '分镜' },
  { title: 'Prompt' },
  { title: '生成' },
  { title: '质检' },
  { title: '成片' },
];

type FlowStage = 'workspace' | 'brief' | 'intent' | 'task';

function StudioPage() {
  const esRef = useRef<{ close: () => void } | null>(null);

  const store = useCreativeStore();
  const {
    taskLoading, taskStatus, taskError, taskLogs, taskResult,
    taskFailureDetail, taskModelUsed, taskCreativeIntent,
    taskScript, taskStoryboard, taskPromptEngineeringResult, taskRoutingDecision,
    taskId, spec,
    setTaskLoading, setTaskStatus, setTaskError, setTaskLogs,
    setTaskResult, setTaskId, resetTask,
    setTaskFailureDetail, setTaskModelUsed, setTaskRoutingDecision,
    setTaskCreativeIntent,
    setTaskScript, setTaskStoryboard, setTaskPromptEngineeringResult,
  } = store;

  const [stage, setStage] = useState<FlowStage>('workspace');
  const [understanding, setUnderstanding] = useState(false);
  const [creativeIntent, setCreativeIntent] = useState<CreativeIntent | null>(null);
  const [briefValue, setBriefValue] = useState<CreativeBriefValue | null>(null);
  // Gate 2(脚本审核)状态
  const [reviewDismissed, setReviewDismissed] = useState(false); // 确认/重新生成后暂离审核视图
  const [scriptRegenerating, setScriptRegenerating] = useState(false);
  const [scriptKey, setScriptKey] = useState(0); // 每次进入 SCRIPT_REVIEW 递增,用于重置审核草稿
  // Gate 3(分镜审核)状态
  const [sbReviewDismissed, setSbReviewDismissed] = useState(false);
  const [sbRegenerating, setSbRegenerating] = useState(false);
  const [shotRegenerating, setShotRegenerating] = useState<number | null>(null);
  const [storyboardKey, setStoryboardKey] = useState(0);
  // Gate 4(Prompt审核)状态
  const [promptReviewDismissed, setPromptReviewDismissed] = useState(false);
  const [promptRegenerating, setPromptRegenerating] = useState(false);
  const [switchingModel, setSwitchingModel] = useState(false);
  const [promptKey, setPromptKey] = useState(0);
  // 作品级状态(AI Director):Bible/镜头决策/质检,随 SSE 实时更新
  const [taskProjectState, setTaskProjectState] = useState<ProjectState | null>(null);
  // 版本历史刷新:任务完成(含局部重生成完成)时递增
  const [versionRefreshKey, setVersionRefreshKey] = useState(0);
  // 创作节点导航:任务结束后(浏览态)决定中心工作区显示哪个节点
  const [viewNode, setViewNode] = useState<NodeKey>('creative');
  // 项目记忆:任务所属项目 ID(结果态加载项目记忆面板)
  const [taskProjectId, setTaskProjectId] = useState<string>('');
  // 失败重试进行中
  const [retryingTask, setRetryingTask] = useState(false);

  // 第一步:AI 理解创意 → 创作意图页
  const handleUnderstand = useCallback(async (value: CreativeBriefValue) => {
    setUnderstanding(true);
    try {
      const resp = await api.understandCreative({
        user_input: value.user_input,
        duration: value.duration,
        aspect_ratio: value.aspect_ratio,
        input_sources: value.input_sources,
      });
      setBriefValue(value);
      setCreativeIntent(resp.creative_intent);
      setStage('intent');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'AI 理解创意失败,请稍后重试');
    } finally {
      setUnderstanding(false);
    }
  }, []);

  // 订阅任务实时状态(Gate 确认/重新生成后复用)
  const startTaskStream = useCallback((taskId: string, fallbackIntent: CreativeIntent | null) => {
    esRef.current?.close();
    esRef.current = subscribeTask(
      taskId,
      async (data) => {
        setTaskStatus(data.status);
        setTaskError(data.error);
        setTaskLogs(data.logs || []);
        setTaskFailureDetail(data.failure_detail);
        setTaskModelUsed(data.model_used);
        setTaskRoutingDecision(data.routing_decision);
        setTaskCreativeIntent(data.creative_intent || fallbackIntent);
        setTaskScript(data.script || null);
        setTaskStoryboard(data.storyboard || null);
        setTaskPromptEngineeringResult(data.prompt_engineering_result || null);
        setTaskProjectState(data.project_state ?? null);
        if (data.status === 'SCRIPT_REVIEW') {
          // Gate 2:脚本待确认
          setReviewDismissed(false);
          setScriptRegenerating(false);
          setScriptKey((k) => k + 1);
          setTaskLoading(false);
        } else if (data.status === 'STORYBOARD_REVIEW') {
          // Gate 3:分镜待确认
          setSbReviewDismissed(false);
          setSbRegenerating(false);
          setShotRegenerating(null);
          setStoryboardKey((k) => k + 1);
          setTaskLoading(false);
        } else if (data.status === 'PROMPT_REVIEW') {
          // Gate 4:Prompt待确认
          setPromptReviewDismissed(false);
          setPromptRegenerating(false);
          setSwitchingModel(false);
          setPromptKey((k) => k + 1);
          setTaskLoading(false);
        } else if (data.status === 'COMPLETED') {
          const r = await api.getResult(taskId);
          setTaskResult(r);
          if (r.project_state) setTaskProjectState(r.project_state);
          setTaskLoading(false);
          setVersionRefreshKey((k) => k + 1);
          setViewNode('final'); // 任务完成 → 进入成片节点(浏览态,可在左侧回溯其他节点)
        } else if (data.status === 'FAILED') {
          setTaskLoading(false);
          setScriptRegenerating(false);
          setSbRegenerating(false);
          setShotRegenerating(null);
          setPromptRegenerating(false);
          setRetryingTask(false);
          const errMsg = data.error || '未知错误';
          message.error(errMsg);
        } else if (data.status === 'HUMAN_REVIEW') {
          setTaskLoading(false);
          setScriptRegenerating(false);
          setSbRegenerating(false);
          setShotRegenerating(null);
          setPromptRegenerating(false);
        }
      },
      () => {
        setTaskLoading(false);
        setScriptRegenerating(false);
        setSbRegenerating(false);
        setShotRegenerating(null);
        setPromptRegenerating(false);
        message.error('实时连接中断');
      },
    );
  }, [setTaskLoading, setTaskStatus, setTaskError, setTaskLogs, setTaskResult, setTaskFailureDetail, setTaskModelUsed, setTaskRoutingDecision, setTaskCreativeIntent, setTaskScript, setTaskStoryboard, setTaskPromptEngineeringResult]);

  // 恢复任务:URL ?task= 或工作台点击 → 拉取后端全量状态回填,进行中任务重连 SSE
  const restoreTask = useCallback(async (taskId: string) => {
    setTaskLoading(true);
    try {
      const full = await api.getTask(taskId);
      setTaskId(taskId);
      setStage('task');
      setTaskStatus(full.status);
      setTaskError(full.error ?? null);
      setTaskLogs(full.logs ?? []);
      setTaskFailureDetail(full.failure_detail ?? null);
      setTaskModelUsed(full.model_used ?? null);
      setTaskRoutingDecision(full.routing_decision ?? null);
      setTaskCreativeIntent(full.creative_intent ?? null);
      setTaskScript(full.script ?? null);
      setTaskStoryboard(full.storyboard ?? null);
      setTaskPromptEngineeringResult(full.prompt_engineering_result ?? null);
      setTaskProjectState(full.project_state ?? null);
      setTaskProjectId(full.project_id || '');
      setBriefValue({
        user_input: full.user_input || '',
        duration: full.duration || 30,
        aspect_ratio: full.aspect_ratio || '9:16',
        compliance_enabled: true,
        input_sources: full.input_sources ?? [],
      });
      const st = full.status as TaskStatus;
      if (st === 'COMPLETED') {
        const r = await api.getResult(taskId);
        setTaskResult(r);
        if (r.project_state) setTaskProjectState(r.project_state);
        setViewNode('final');
        setVersionRefreshKey((k) => k + 1);
        setTaskLoading(false);
      } else if (['FAILED', 'SCRIPT_REVIEW', 'STORYBOARD_REVIEW', 'PROMPT_REVIEW', 'HUMAN_REVIEW'].includes(st)) {
        // 失败态/审核 Gate:直接呈现对应界面
        setTaskLoading(false);
      } else {
        // 进行中:重连实时流继续跟踪
        startTaskStream(taskId, full.creative_intent ?? null);
      }
      window.history.replaceState({}, '', `/?task=${taskId}`);
    } catch {
      message.error('恢复任务失败,任务可能已不存在');
      setTaskLoading(false);
      setStage('workspace');
      window.history.replaceState({}, '', '/');
    }
  }, [startTaskStream, setTaskLoading, setTaskId, setTaskStatus, setTaskError, setTaskLogs, setTaskFailureDetail, setTaskModelUsed, setTaskRoutingDecision, setTaskCreativeIntent, setTaskScript, setTaskStoryboard, setTaskPromptEngineeringResult]);

  // 路由 ?task= 变化 → 恢复指定任务(历史页跳转/刷新保持/直接输 URL)
  const location = useLocation();
  useEffect(() => {
    const taskId = new URLSearchParams(location.search).get('task');
    if (!taskId || taskId === store.taskId) return;
    restoreTask(taskId);
  }, [location.search, restoreTask, store.taskId]);

  // Gate 1:确认创作方案 → 创建任务,进入生成流程(脚本生成后暂停等待确认)
  const handleConfirmIntent = useCallback(async (edited: CreativeIntent) => {
    if (!briefValue) return;
    resetTask();
    setTaskProjectState(null);
    setReviewDismissed(false);
    setScriptRegenerating(false);
    setSbReviewDismissed(false);
    setSbRegenerating(false);
    setShotRegenerating(null);
    setPromptReviewDismissed(false);
    setPromptRegenerating(false);
    setTaskLoading(true);
    setTaskStatus('PENDING');
    try {
      // 关联作品:未选择则自动新建(标题取创作主题)
      let projectId = briefValue.project_id || '';
      if (!projectId) {
        try {
          const proj = await api.createProject({
            title: (edited.subject || briefValue.user_input).slice(0, 24) || '未命名作品',
            description: briefValue.user_input.slice(0, 200),
          });
          projectId = proj.id;
        } catch {
          // 作品创建失败不阻塞创作流程
        }
      }
      setTaskProjectId(projectId);
      const brief = await api.createTask({
        user_input: briefValue.user_input,
        duration: edited.duration || briefValue.duration,
        style: edited.visual_style || '',
        aspect_ratio: edited.aspect_ratio || briefValue.aspect_ratio,
        compliance_enabled: briefValue.compliance_enabled,
        input_sources: briefValue.input_sources,
        mode: 'collaborative',
        // 专业创作控制:风格栈/创作元素/镜头/场景/音频 → 后端全量消费进 Prompt 编译
        spec: {
          ...spec,
          prompt: briefValue.user_input,
          duration: edited.duration || briefValue.duration,
          aspect_ratio: edited.aspect_ratio || briefValue.aspect_ratio,
        },
        project_id: projectId,
        confirmed_intent: edited,
      });
      setTaskId(brief.task_id);
      setStage('task');
      // URL 同步任务 ID:刷新/分享后可恢复
      window.history.replaceState({}, '', `/?task=${brief.task_id}`);
      startTaskStream(brief.task_id, edited);
    } catch (e: any) {
      setTaskLoading(false);
      message.error('创建任务失败: ' + (e?.message || ''));
    }
  }, [briefValue, spec, resetTask, setTaskLoading, setTaskStatus, setTaskId, startTaskStream]);

  // Gate 2:确认脚本(可携带编辑) → 继续分镜/Prompt/生成
  const handleConfirmScript = useCallback(async (editedScript: any) => {
    if (!taskId) return;
    setReviewDismissed(true);
    setTaskLoading(true);
    setTaskStatus('COMPLIANCE_CHECKING');
    try {
      await api.confirmScript(taskId, editedScript);
      startTaskStream(taskId, taskCreativeIntent);
    } catch (e: any) {
      setReviewDismissed(false);
      setTaskLoading(false);
      message.error(e?.response?.data?.detail || '确认脚本失败,请重试');
    }
  }, [taskId, taskCreativeIntent, startTaskStream, setTaskLoading, setTaskStatus]);

  // Gate 2:重新生成脚本草稿(可携带用户反馈)
  const handleRegenerateScript = useCallback(async (feedback?: string) => {
    if (!taskId) return;
    setReviewDismissed(true);
    setScriptRegenerating(true);
    setTaskStatus('SCRIPTING');
    try {
      await api.regenerateScript(taskId, feedback);
      startTaskStream(taskId, taskCreativeIntent);
    } catch (e: any) {
      setReviewDismissed(false);
      setScriptRegenerating(false);
      message.error(e?.response?.data?.detail || '重新生成脚本失败,请重试');
    }
  }, [taskId, taskCreativeIntent, startTaskStream, setTaskStatus]);

  // Gate 3:确认分镜(可携带编辑) → 继续Prompt/生成
  const handleConfirmStoryboard = useCallback(async (editedStoryboard: any) => {
    if (!taskId) return;
    setSbReviewDismissed(true);
    setTaskLoading(true);
    setTaskStatus('GENERATING_ASSETS');
    try {
      await api.confirmStoryboard(taskId, editedStoryboard);
      startTaskStream(taskId, taskCreativeIntent);
    } catch (e: any) {
      setSbReviewDismissed(false);
      setTaskLoading(false);
      message.error(e?.response?.data?.detail || '确认分镜失败,请重试');
    }
  }, [taskId, taskCreativeIntent, startTaskStream, setTaskLoading, setTaskStatus]);

  // Gate 3:重新生成全部分镜(可携带用户反馈)
  const handleRegenerateStoryboard = useCallback(async (feedback?: string) => {
    if (!taskId) return;
    setSbReviewDismissed(true);
    setSbRegenerating(true);
    setTaskStatus('STORYBOARDING');
    try {
      await api.regenerateStoryboard(taskId, null, feedback);
      startTaskStream(taskId, taskCreativeIntent);
    } catch (e: any) {
      setSbReviewDismissed(false);
      setSbRegenerating(false);
      message.error(e?.response?.data?.detail || '重新生成分镜失败,请重试');
    }
  }, [taskId, taskCreativeIntent, startTaskStream, setTaskStatus]);

  // Gate 3:重新生成单个镜头(草稿态,确认前可反复调整,可携带反馈)
  const handleRegenerateShot = useCallback(async (shotIndex: number, feedback?: string) => {
    if (!taskId) return;
    setShotRegenerating(shotIndex);
    try {
      await api.regenerateStoryboard(taskId, shotIndex, feedback);
      // 轮询分镜数据更新(单镜头重生成不经过前端草稿)
      const poll = setInterval(async () => {
        try {
          const full = await api.getTask(taskId);
          if (full.status === 'STORYBOARD_REVIEW' && full.storyboard) {
            clearInterval(poll);
            setTaskStoryboard(full.storyboard);
            setStoryboardKey((k) => k + 1);
            setShotRegenerating(null);
          } else if (full.status === 'FAILED') {
            clearInterval(poll);
            setShotRegenerating(null);
            message.error(full.error || '重新生成镜头失败');
          }
        } catch {
          clearInterval(poll);
          setShotRegenerating(null);
        }
      }, 1500);
      // 30 秒超时保护
      setTimeout(() => { clearInterval(poll); setShotRegenerating(null); }, 30000);
    } catch (e: any) {
      setShotRegenerating(null);
      message.error(e?.response?.data?.detail || '重新生成镜头失败,请重试');
    }
  }, [taskId, setTaskStoryboard]);

  // Gate 4:确认 Prompt(可携带编辑) → 继续风控/素材生成
  const handleConfirmPrompt = useCallback(async (editedPrompt: any) => {
    if (!taskId) return;
    setPromptReviewDismissed(true);
    setTaskLoading(true);
    setTaskStatus('GENERATING_ASSETS');
    try {
      await api.confirmPrompt(taskId, editedPrompt);
      startTaskStream(taskId, taskCreativeIntent);
    } catch (e: any) {
      setPromptReviewDismissed(false);
      setTaskLoading(false);
      message.error(e?.response?.data?.detail || '确认 Prompt 失败,请重试');
    }
  }, [taskId, taskCreativeIntent, startTaskStream, setTaskLoading, setTaskStatus]);

  // Gate 4:重新编译 Prompt(可携带用户反馈)
  const handleRegeneratePrompt = useCallback(async (feedback?: string) => {
    if (!taskId) return;
    setPromptReviewDismissed(true);
    setPromptRegenerating(true);
    setTaskStatus('GENERATING_ASSETS');
    try {
      await api.regeneratePrompt(taskId, feedback);
      startTaskStream(taskId, taskCreativeIntent);
    } catch (e: any) {
      setPromptReviewDismissed(false);
      setPromptRegenerating(false);
      message.error(e?.response?.data?.detail || '重新编译 Prompt 失败,请重试');
    }
  }, [taskId, taskCreativeIntent, startTaskStream, setTaskStatus]);

  // Gate 4:手动切换视频模型(按新模型能力重新编译 Prompt)
  const handleSwitchModel = useCallback(async (modelId: string) => {
    if (!taskId) return;
    setPromptReviewDismissed(true);
    setSwitchingModel(true);
    setTaskStatus('GENERATING_ASSETS');
    try {
      await api.switchModel(taskId, modelId);
      startTaskStream(taskId, taskCreativeIntent);
    } catch (e: any) {
      setPromptReviewDismissed(false);
      setSwitchingModel(false);
      message.error(e?.response?.data?.detail || '切换模型失败,请重试');
    }
  }, [taskId, taskCreativeIntent, startTaskStream, setTaskStatus]);

  // 局部修改:开始重生成受影响镜头 → 回到生成视图,重连 SSE
  const handleReviseStarted = useCallback(() => {
    setTaskResult(null);
    setTaskLoading(true);
    setTaskStatus('GENERATING_ASSETS');
    if (taskId) {
      startTaskStream(taskId, taskCreativeIntent);
    }
  }, [taskId, taskCreativeIntent, startTaskStream, setTaskResult, setTaskLoading, setTaskStatus]);

  // 镜头锁定变化 → 刷新分镜数据(锁状态)
  const handleLockChanged = useCallback(async () => {
    if (!taskId) return;
    try {
      const full = await api.getTask(taskId);
      if (full.storyboard) {
        setTaskStoryboard(full.storyboard);
      }
    } catch {
      /* 刷新失败不影响主流程 */
    }
  }, [taskId, setTaskStoryboard]);

  // 版本恢复 → 刷新任务对应内容(基于恢复的版本继续创作)
  const handleVersionRestored = useCallback(async (nodeType: string) => {
    if (!taskId) return;
    try {
      const full = await api.getTask(taskId);
      if (nodeType === 'storyboard' && full.storyboard) setTaskStoryboard(full.storyboard);
      if (nodeType === 'script' && full.script) setTaskScript(full.script);
      if (nodeType === 'prompt' && full.prompt_engineering_result) {
        setTaskPromptEngineeringResult(full.prompt_engineering_result);
      }
      if (nodeType === 'creative_intent' && full.creative_intent) {
        setTaskCreativeIntent(full.creative_intent);
      }
    } catch {
      /* 刷新失败不影响主流程 */
    }
  }, [taskId, setTaskStoryboard, setTaskScript, setTaskPromptEngineeringResult, setTaskCreativeIntent]);

  const handleBackToBrief = useCallback(() => {
    setStage('brief');
    setCreativeIntent(null);
  }, []);

  // 失败重试:从失败阶段恢复(后端保留已完成阶段产物)
  const handleRetryTask = useCallback(async () => {
    if (!taskId) return;
    setRetryingTask(true);
    setTaskLoading(true);
    setTaskStatus('PENDING');
    try {
      await api.retryTask(taskId);
      startTaskStream(taskId, taskCreativeIntent);
    } catch (e: any) {
      setRetryingTask(false);
      setTaskLoading(false);
      message.error(e?.response?.data?.detail || '重试失败,请稍后再试');
    }
  }, [taskId, taskCreativeIntent, startTaskStream, setTaskLoading, setTaskStatus]);

  // 失败后换模型:重试并指定偏好模型
  const handleRetryWithNewModel = useCallback(() => {
    if (!taskId) return;
    message.info('任务将从失败阶段重试,请在重新到达 Prompt 确认时选择新模型');
    handleRetryTask();
  }, [taskId, handleRetryTask]);

  // 失败后返回分镜修改(浏览分镜,用户编辑后用局部重生成)
  const handleBackToStoryboardFromFailure = useCallback(() => {
    if (taskStoryboard) {
      setSbReviewDismissed(false);
      message.info('可在分镜视图中调整后重新生成');
    }
  }, [taskStoryboard]);

  // 返回项目工作台(新建创作从工作台进入)
  const handleNewCreation = useCallback(() => {
    esRef.current?.close();
    resetTask();
    setTaskProjectState(null);
    setStage('workspace');
    setCreativeIntent(null);
    setBriefValue(null);
    setViewNode('creative');
    setTaskProjectId('');
    window.history.replaceState({}, '', '/');
  }, [resetTask]);

  const showProgress = stage === 'task' && taskStatus !== null;
  const currentStatus = taskStatus || 'PENDING';
  const showResult = taskResult !== null;

  // 结果态:加载任务所属项目 ID(供项目记忆面板)
  useEffect(() => {
    if (!taskId || !showResult || taskProjectId !== '') return;
    api.getTask(taskId)
      .then((full: any) => setTaskProjectId(full.project_id || ''))
      .catch(() => setTaskProjectId(''));
  }, [taskId, showResult, taskProjectId]);

  // Gate 2:脚本待确认(未处于确认后/重新生成中的过渡态)
  const showScriptReview =
    stage === 'task' &&
    currentStatus === 'SCRIPT_REVIEW' &&
    taskScript !== null &&
    !reviewDismissed;
  // Gate 3:分镜待确认(未处于确认后/重新生成中的过渡态)
  const showStoryboardReview =
    stage === 'task' &&
    currentStatus === 'STORYBOARD_REVIEW' &&
    taskStoryboard !== null &&
    !sbReviewDismissed;
  // Gate 4:Prompt待确认(未处于确认后/重新编译中的过渡态)
  const showPromptReview =
    stage === 'task' &&
    currentStatus === 'PROMPT_REVIEW' &&
    taskPromptEngineeringResult !== null &&
    !promptReviewDismissed;

  // 顶部流程条当前步(浏览态跟随选中节点,进行中跟随任务状态)
  const shots: GalleryShot[] = (taskStoryboard?.shots as GalleryShot[]) ?? [];
  // 任务处于浏览态:完成后允许在流程节点与资源间自由切换
  const taskBrowsing = stage === 'task' && showResult;
  let currentStep = 0;
  if (stage === 'brief') currentStep = 0;
  else if (stage === 'intent') currentStep = 1;
  else if (stage === 'task') {
    const statusStep: Record<string, number> = {
      PENDING: 1, ANALYZING: 1, SCRIPTING: 3, COMPLIANCE_CHECKING: 3,
      SCRIPT_REVIEW: 3,
      STORYBOARDING: 4, STORYBOARD_REVIEW: 4,
      PROMPT_REVIEW: 5,
      GENERATING_ASSETS: 6, ASSEMBLING: 6,
      COMPLETED: 8, FAILED: 6, HUMAN_REVIEW: 7,
    };
    currentStep = statusStep[currentStatus] ?? 3;
    if (taskBrowsing) {
      const viewStep: Partial<Record<NodeKey, number>> = {
        creative: 0, intent: 1, bible: 2, script: 3, storyboard: 4,
        prompt: 5, videos: 6, final: 8,
      };
      currentStep = viewStep[viewNode] ?? currentStep;
    }
  }

  // ---- 节点可用性 ----
  // 作品设定是否有可展示内容(故事/人物/世界观/风格任一)
  const hasBibleContent = !!(
    taskProjectState &&
    (taskProjectState.story_state?.beats?.length ||
      taskProjectState.story_state?.logline ||
      taskProjectState.character_state?.bibles?.length ||
      taskProjectState.world_state?.bible?.era ||
      taskProjectState.world_state?.bible?.scenes?.length ||
      taskProjectState.style_state?.bible?.visual_style)
  );

  // 流程节点可用性(顶部流程条路由)
  const flowAvailable: Partial<Record<NodeKey, boolean>> = {
    creative: true,
    intent: !!(creativeIntent || taskCreativeIntent),
    bible: hasBibleContent,
    script: !!taskScript,
    storyboard: !!taskStoryboard,
    prompt: !!taskPromptEngineeringResult,
    videos: shots.some((s) => s.video_path),
    final: showResult,
  };
  // 资源节点可用性(左侧导航路由):浏览态开放
  const navAvailable: Partial<Record<NodeKey, boolean>> = {
    assets: taskBrowsing,
    versions: taskBrowsing,
  };

  // 点击左侧资源:浏览态路由
  const handleNodeSelect = useCallback(
    (key: NodeKey) => {
      if (!taskBrowsing) return;
      setViewNode(key);
    },
    [taskBrowsing],
  );

  // 项目工作台首页:新建作品 / 最近作品 / 进行中任务恢复
  if (stage === 'workspace') {
    return (
      <Layout style={{ minHeight: '100vh', background: colors.bg }}>
        <Header
          style={{
            background: colors.surface,
            padding: '0 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            height: 56,
            lineHeight: '56px',
            borderBottom: `1px solid ${colors.border}`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <PageTitle level={4} style={{ margin: 0, fontWeight: 500, letterSpacing: '0.06em' }}>项目工作台</PageTitle>
          </div>
          <UserMenu />
        </Header>
        <Content style={{ padding: 24, overflow: 'auto' }}>
          <WorkspacePage
            onOpenTask={(id) => restoreTask(id)}
          />
        </Content>
      </Layout>
    );
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: colors.bg }}>
      <NodeNav active={viewNode} available={navAvailable} onSelect={handleNodeSelect} onBackHome={handleNewCreation} />
      <Layout style={{ flex: 1, minHeight: 0, background: colors.bg }}>
        <Header
          style={{
            background: colors.surface,
            padding: '0 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            height: 56,
            lineHeight: '56px',
            borderBottom: `1px solid ${colors.border}`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <PageTitle level={4} style={{ margin: 0, fontWeight: 500, letterSpacing: '0.06em' }}>
              创作工作台
            </PageTitle>
            <span style={{ fontSize: 12, color: colors.textMuted, letterSpacing: '0.08em' }}>AI 影视创作</span>
          </div>
          <UserMenu />
        </Header>
        <Content style={{ padding: 16, overflow: 'hidden' }}>
          <div style={{ display: 'flex', gap: 16, height: '100%' }}>
            {/* 中央工作区 */}
            <div
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                gap: 16,
                minWidth: 0,
                overflow: 'auto',
              }}
            >
              {/* 顶部创作流程导航(流程节点唯一入口,浏览态可回溯) */}
              <div style={{ ...cardStyle, padding: '12px 24px', flexShrink: 0 }}>
                <Steps
                  size="small"
                  current={currentStep}
                  items={FLOW_STEPS}
                  onChange={(i) => {
                    if (stage === 'brief') return;
                    if (stage === 'intent') {
                      if (i === 0) setStage('brief');
                      return;
                    }
                    if (stage === 'task' && taskBrowsing) {
                      const stepNodeMap: Record<number, NodeKey> = {
                        0: 'creative', 1: 'intent', 2: 'bible', 3: 'script', 4: 'storyboard',
                        5: 'prompt', 6: 'videos', 7: 'final', 8: 'final',
                      };
                      const node = stepNodeMap[i];
                      if (node && (flowAvailable[node] ?? false)) setViewNode(node);
                    }
                  }}
                />
              </div>

              {/* 第一步:创作输入 */}
              {stage === 'brief' && (
                <div style={{ ...cardStyle, flex: 1, minHeight: 0 }}>
                  <CreativeBrief loading={understanding} onSubmit={handleUnderstand} />
                </div>
              )}

              {/* Gate 1:创作方案确认 */}
              {stage === 'intent' && creativeIntent && (
                <div style={{ ...cardStyle, flex: 1, minHeight: 0 }}>
                  <IntentReview
                    intent={creativeIntent}
                    submitting={taskLoading}
                    onBack={handleBackToBrief}
                    onConfirm={handleConfirmIntent}
                  />
                </div>
              )}

              {/* Gate 2:脚本审核(编辑/删除/新增/重新生成/确认) */}
              {showScriptReview && (
                <div style={{ ...cardStyle, flex: 1, minHeight: 0, overflow: 'auto' }}>
                  <ScriptReview
                    key={scriptKey}
                    script={taskScript}
                    targetDuration={taskCreativeIntent?.duration || briefValue?.duration || 30}
                    regenerating={scriptRegenerating}
                    submitting={taskLoading}
                    taskId={taskId ?? undefined}
                    onRegenerate={handleRegenerateScript}
                    onConfirm={handleConfirmScript}
                    onBack={handleNewCreation}
                  />
                </div>
              )}

              {/* Gate 3:分镜审核(编辑镜头/排序/增删/单镜头重生成/确认) */}
              {showStoryboardReview && (
                <div style={{ ...cardStyle, flex: 1, minHeight: 0, overflow: 'auto' }}>
                  <StoryboardReview
                    key={storyboardKey}
                    storyboard={taskStoryboard}
                    regenerating={sbRegenerating}
                    shotRegenerating={shotRegenerating}
                    submitting={taskLoading}
                    onRegenerateAll={handleRegenerateStoryboard}
                    onRegenerateShot={handleRegenerateShot}
                    onConfirm={handleConfirmStoryboard}
                    onBack={() => message.info('脚本已确认,如需修改请重新生成视频')}
                  />
                </div>
              )}

              {/* Gate 4:Prompt审核(查看/编辑/重编译/确认) */}
              {showPromptReview && (
                <div style={{ ...cardStyle, flex: 1, minHeight: 0, overflow: 'auto' }}>
                  <PromptReview
                    key={promptKey}
                    result={taskPromptEngineeringResult}
                    routingDecision={taskRoutingDecision}
                    regenerating={promptRegenerating}
                    switchingModel={switchingModel}
                    submitting={taskLoading}
                    onRegenerate={handleRegeneratePrompt}
                    onSwitchModel={handleSwitchModel}
                    onConfirm={handleConfirmPrompt}
                    onBack={() => message.info('分镜已确认,如需修改请重新生成视频')}
                  />
                </div>
              )}

              {/* 生成执行 / 结果 */}
              {showProgress && !showResult && !showScriptReview && !showStoryboardReview && !showPromptReview && (
                <div style={{ ...cardStyle, flex: 1, minHeight: 0, overflow: 'auto' }}>
                  <Paragraph type="secondary" style={{ marginBottom: 12 }}>
                    {currentStatus === 'SCRIPTING' && scriptRegenerating
                      ? '正在重新生成脚本…'
                      : '正在生成,你可以实时查看 AI 的工作成果'}
                  </Paragraph>
                  <ProgressTimeline status={currentStatus} error={taskError} logs={taskLogs} failureDetail={taskFailureDetail} modelUsed={taskModelUsed} creativeIntent={taskCreativeIntent} />
                  {currentStatus === 'FAILED' && (
                    <FailureRecoveryCard
                      failureDetail={taskFailureDetail}
                      error={taskError}
                      modelUsed={taskModelUsed}
                      hasPrompt={!!taskPromptEngineeringResult}
                      hasStoryboard={!!taskStoryboard}
                      retrying={retryingTask}
                      onRetryFromStage={handleRetryTask}
                      onSwitchModel={handleRetryWithNewModel}
                      onEditPrompt={handleRetryWithNewModel}
                      onBackToStoryboard={handleBackToStoryboardFromFailure}
                    />
                  )}
                  <ScriptViewer script={taskScript} />
                  <StoryboardViewer storyboard={taskStoryboard} projectState={taskProjectState} />
                  <PromptInspector result={taskPromptEngineeringResult} routingDecision={taskRoutingDecision} />
                </div>
              )}
              {/* 任务结束 → 创作节点路由(浏览态:中间区域永远是当前选中节点) */}
              {showResult && (
                <div style={{ ...cardStyle, flex: 1, minHeight: 0, overflow: 'auto' }}>
                  {viewNode === 'creative' &&
                    (briefValue ? (
                      <CreativeRecap userInput={briefValue.user_input} onNewCreation={handleNewCreation} />
                    ) : (
                      <Empty description="创意信息不存在" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    ))}

                  {viewNode === 'intent' && (taskCreativeIntent || creativeIntent) && (
                    <IntentSummary intent={taskCreativeIntent || creativeIntent!} />
                  )}

                  {viewNode === 'bible' && (
                    <BiblePanel
                      projectState={taskProjectState}
                      taskId={taskId ?? undefined}
                      onUpdated={(ps) => setTaskProjectState(ps)}
                    />
                  )}

                  {viewNode === 'script' && (
                    <>
                      <ScriptViewer script={taskScript} />
                      {currentStatus === 'COMPLETED' && taskId && taskScript && (
                        <SceneRevisePanel
                          taskId={taskId}
                          scenes={taskScript.scenes as any}
                          onReviseStarted={handleReviseStarted}
                        />
                      )}
                    </>
                  )}

                  {viewNode === 'storyboard' && <StoryboardViewer storyboard={taskStoryboard} projectState={taskProjectState} />}

                  {viewNode === 'prompt' && (
                    <PromptInspector result={taskPromptEngineeringResult} routingDecision={taskRoutingDecision} />
                  )}

                  {viewNode === 'assets' && (
                    <Tabs
                      defaultActiveKey="images"
                      items={[
                        {
                          key: 'images',
                          label: `生成图片${shots.some((s) => s.image_path) ? `(${shots.filter((s) => s.image_path).length})` : ''}`,
                          children: <ShotsMediaGallery shots={shots} kind="image" />,
                        },
                        {
                          key: 'videos',
                          label: `生成视频${shots.some((s) => s.video_path) ? `(${shots.filter((s) => s.video_path).length})` : ''}`,
                          children: <ShotsMediaGallery shots={shots} kind="video" />,
                        },
                        {
                          key: 'audio',
                          label: `生成音频${shots.some((s) => s.audio_path) ? `(${shots.filter((s) => s.audio_path).length})` : ''}`,
                          children: <ShotsMediaGallery shots={shots} kind="audio" />,
                        },
                        {
                          key: 'uploads',
                          label: '上传素材',
                          children: <AssetsPanel sources={briefValue?.input_sources ?? []} />,
                        },
                        ...(taskProjectId
                          ? [{ key: 'project', label: '项目素材', children: <ProjectAssetsPanel projectId={taskProjectId} /> }]
                          : []),
                        ...(taskProjectId
                          ? [{ key: 'memory', label: '项目记忆', children: <ProjectMemoryPanel projectId={taskProjectId} /> }]
                          : []),
                      ]}
                    />
                  )}

                  {viewNode === 'versions' && taskId && (
                    <VersionHistoryPanel
                      taskId={taskId}
                      refreshKey={versionRefreshKey}
                      onRestored={handleVersionRestored}
                    />
                  )}

                  {viewNode === 'final' && (
                    <>
                      <VideoResult result={taskResult} />
                      {currentStatus === 'COMPLETED' && taskId && taskStoryboard && (
                        <ShotRevisePanel
                          taskId={taskId}
                          shots={taskStoryboard.shots as any}
                          onReviseStarted={handleReviseStarted}
                          onLockChanged={handleLockChanged}
                        />
                      )}
                      {currentStatus === 'COMPLETED' && taskId && taskStoryboard && (
                        <SubtitleEditor taskId={taskId} onUpdated={handleReviseStarted} />
                      )}
                    </>
                  )}
                </div>
              )}
            </div>

            {/* 右侧 AI 助手面板 */}
            <div style={{ width: 360, flexShrink: 0 }}>
              <AIPlanPanel />
            </div>
          </div>
        </Content>
      </Layout>
    </div>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/history" element={<ProtectedRoute><HistoryPage /></ProtectedRoute>} />
      <Route path="/director" element={<ProtectedRoute><Suspense fallback={<div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Spin size="large" /></div>}><DeskGuard><DirectorDeskPage /></DeskGuard></Suspense></ProtectedRoute>} />
      <Route path="/director/marketplace" element={<ProtectedRoute><MarketplaceStubPage /></ProtectedRoute>} />
      <Route path="/" element={<ProtectedRoute><Navigate to="/director" replace /></ProtectedRoute>} />
      <Route path="/studio" element={<ProtectedRoute><StudioPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/director" replace />} />
    </Routes>
  );
}
