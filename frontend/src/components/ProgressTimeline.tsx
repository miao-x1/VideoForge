import { Steps } from 'antd';
import {
  CheckCircleFilled,
  LoadingOutlined,
  CloseCircleFilled,
  WarningFilled,
} from '@ant-design/icons';
import type { TaskStatus, LogEntry } from '../api/client';

interface Props {
  status: TaskStatus;
  logs: LogEntry[];
  error: string | null;
}

// 7 阶段,对齐后端 Pipeline:
// Requirement → Script → Compliance → Storyboard → ContentGuard → Media → Assembly
const STAGES: { key: string; title: string; status: TaskStatus }[] = [
  { key: 'req', title: '需求理解', status: 'ANALYZING' },
  { key: 'script', title: '脚本生成', status: 'SCRIPTING' },
  { key: 'compliance', title: '合规预审', status: 'COMPLIANCE_CHECKING' },
  { key: 'story', title: '分镜生成', status: 'STORYBOARDING' },
  { key: 'guard', title: '内容风控', status: 'GENERATING_ASSETS' },
  { key: 'media', title: '素材生成', status: 'GENERATING_ASSETS' },
  { key: 'assemble', title: '视频合成', status: 'ASSEMBLING' },
];

// status → 阶段索引(0-6),-1 表示尚未开始
const STATUS_STAGE: Record<TaskStatus, number> = {
  PENDING: -1,
  ANALYZING: 0,
  SCRIPTING: 1,
  COMPLIANCE_CHECKING: 2,
  STORYBOARDING: 3,
  GENERATING_ASSETS: 4, // 默认 ContentGuard,用 logs 细分到 media(5)
  ASSEMBLING: 6,
  COMPLETED: 7,
  FAILED: 7,
  HUMAN_REVIEW: 2, // 卡在合规预审
};

// ContentGuard 与 Media 共享 GENERATING_ASSETS,用 logs 最后一条 message 区分
function resolveStage(status: TaskStatus, logs: LogEntry[]): number {
  if (status !== 'GENERATING_ASSETS') return STATUS_STAGE[status] ?? -1;
  if (logs.length === 0) return 4;
  const last = logs[logs.length - 1].message || '';
  // 已进入素材生成的标志:开始/完成 shot 素材
  if (
    last.includes('素材') ||
    last.includes('shot') ||
    last.includes('I2V') ||
    last.includes('文生图') ||
    last.includes('TTS') ||
    last.includes('BGM')
  ) {
    return 5;
  }
  return 4; // ContentGuard
}

// 失败时定位失败阶段:取 logs 中最后一条非 FAILED/COMPLETED 的 status
function resolveFailedStage(logs: LogEntry[]): number {
  for (let i = logs.length - 1; i >= 0; i--) {
    const s = logs[i].status;
    if (s !== 'FAILED' && s !== 'COMPLETED') {
      return resolveStage(s, logs.slice(0, i + 1));
    }
  }
  return 0;
}

// 解析分镜级进度:从 logs 提取"正在生成第 X/N 个镜头"
function resolveShotProgress(logs: LogEntry[]): string | null {
  for (let i = logs.length - 1; i >= 0; i--) {
    const m = (logs[i].message || '').match(
      /正在生成第\s*(\d+)\s*\/\s*(\d+)\s*个镜头/,
    );
    if (m) return `${m[1]}/${m[2]} 镜头`;
  }
  return null;
}

export default function ProgressTimeline({ status, logs, error }: Props) {
  const completed = status === 'COMPLETED';
  const failed = status === 'FAILED';
  const humanReview = status === 'HUMAN_REVIEW';

  const currentIdx = resolveStage(status, logs);
  const failedIdx = failed ? resolveFailedStage(logs) : -1;
  const shotProgress = resolveShotProgress(logs);

  const items = STAGES.map((stage, i) => {
    let state: 'finish' | 'process' | 'wait' | 'error' = 'wait';

    if (completed) {
      state = 'finish';
    } else if (failed) {
      if (i < failedIdx) state = 'finish';
      else if (i === failedIdx) state = 'error';
      else state = 'wait';
    } else if (humanReview) {
      // 合规预审阶段(i=2)需要人工审核,之前的阶段完成
      if (i < 2) state = 'finish';
      else if (i === 2) state = 'error';
      else state = 'wait';
    } else {
      if (i < currentIdx) state = 'finish';
      else if (i === currentIdx) state = 'process';
      else state = 'wait';
    }

    let icon;
    if (state === 'process') icon = <LoadingOutlined />;
    else if (state === 'finish')
      icon = <CheckCircleFilled style={{ color: '#52c41a' }} />;
    else if (state === 'error')
      icon =
        humanReview && i === 2 ? (
          <WarningFilled style={{ color: '#faad14' }} />
        ) : (
          <CloseCircleFilled style={{ color: '#ff4d4f' }} />
        );

    let title = stage.title;
    if (humanReview && i === 2) title = '合规预审(需人工审核)';

    let description: string | undefined;
    if (stage.key === 'media' && shotProgress && state === 'process') {
      description = shotProgress;
    }

    return { title, status: state as any, icon, description };
  });

  if (completed) {
    items.push({
      title: '完成',
      status: 'finish' as any,
      icon: <CheckCircleFilled style={{ color: '#52c41a' }} />,
      description: undefined,
    });
  }

  return (
    <div>
      <Steps direction="vertical" size="small" items={items} />
      {failed && error && (
        <div style={{ color: '#ff4d4f', marginTop: 8, fontSize: 13 }}>
          失败原因：{error}
        </div>
      )}
      {humanReview && (
        <div style={{ color: '#faad14', marginTop: 8, fontSize: 13 }}>
          合规预审未通过且自动修订已耗尽,需人工审核
        </div>
      )}
    </div>
  );
}
