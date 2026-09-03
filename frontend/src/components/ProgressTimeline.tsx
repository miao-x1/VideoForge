import { Steps, Tag, Typography, Collapse, Descriptions } from 'antd';
import {
  CheckCircleFilled,
  LoadingOutlined,
  CloseCircleFilled,
  WarningFilled,
  BulbFilled,
} from '@ant-design/icons';
import type { TaskStatus, LogEntry, CreativeIntent } from '../api/client';

const { Text } = Typography;

interface Props {
  status: TaskStatus;
  logs: LogEntry[];
  error: string | null;
  failureDetail?: any | null;
  modelUsed?: string | null;
  creativeIntent?: CreativeIntent | null;
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
  SCRIPT_REVIEW: 1, // 脚本已生成,等待用户确认(Gate 2)
  STORYBOARDING: 3,
  STORYBOARD_REVIEW: 3, // 分镜已生成,等待用户确认(Gate 3)
  GENERATING_ASSETS: 4, // 默认 ContentGuard,用 logs 细分到 media(5)
  PROMPT_REVIEW: 4, // Prompt 已编译,等待用户确认(Gate 4)
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

// 错误码 → 中文说明
const ERROR_CODE_LABELS: Record<string, string> = {
  INSUFFICIENT_BALANCE: '账户余额不足',
  MODEL_UNAVAILABLE: '模型不可用',
  MODEL_NOT_AVAILABLE: '指定模型不可用',
  NO_MODELS_AVAILABLE: '无可用模型',
  PROVIDER_NOT_CONFIGURED: 'Provider 未配置',
  PROVIDER_UNAVAILABLE: 'Provider 不可用',
  INVALID_API_KEY: 'API Key 无效',
  ACCESS_DENIED: '无权访问',
  RATE_LIMITED: '请求被限流',
  HTTP_ERROR: '网络请求错误',
  SUBMIT_FAILED: '视频提交失败',
  GENERATION_FAILED: '视频生成失败',
  POLL_TIMEOUT: '生成超时',
  PIPELINE_ERROR: 'Pipeline 异常',
};

export default function ProgressTimeline({ status, logs, error, failureDetail, modelUsed, creativeIntent }: Props) {
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
      {modelUsed && !failed && (
        <div style={{ marginTop: 8, fontSize: 13 }}>
          <Text type="secondary">视频模型: </Text>
          <Tag color="blue">{modelUsed}</Tag>
        </div>
      )}
      {failed && error && (
        <div style={{ color: '#ff4d4f', marginTop: 8, fontSize: 13 }}>
          失败原因：{error}
        </div>
      )}
      {failed && failureDetail && (
        <div style={{ marginTop: 8, padding: '8px 12px', background: '#fff2f0', border: '1px solid #ffccc7', borderRadius: 6, fontSize: 13 }}>
          {failureDetail.error_code && (
            <div style={{ marginBottom: 4 }}>
              <Text strong style={{ color: '#ff4d4f' }}>
                {ERROR_CODE_LABELS[failureDetail.error_code] || failureDetail.error_code}
              </Text>
              {failureDetail.provider && (
                <Tag style={{ marginLeft: 8, fontSize: 11 }}>{failureDetail.provider}</Tag>
              )}
            </div>
          )}
          {failureDetail.stage && (
            <div style={{ color: '#666', marginBottom: 2 }}>
              失败阶段: {failureDetail.stage}
            </div>
          )}
          {failureDetail.reason && (
            <div style={{ color: '#666', marginBottom: 2 }}>
              详细原因: {failureDetail.reason}
            </div>
          )}
          {failureDetail.input_files && Array.isArray(failureDetail.input_files) && failureDetail.input_files.length > 0 && (
            <div style={{ color: '#666' }}>
              已生成素材: {failureDetail.input_files.length} 个
            </div>
          )}
        </div>
      )}
      {humanReview && (
        <div style={{ color: '#faad14', marginTop: 8, fontSize: 13 }}>
          合规预审未通过且自动修订已耗尽,需人工审核
        </div>
      )}
      {creativeIntent && (
        <Collapse
          size="small"
          style={{ marginTop: 12 }}
          items={[{
            key: 'intent',
            label: (
              <span>
                <BulbFilled style={{ color: '#faad14', marginRight: 6 }} />
                AI 已理解你的创意
              </span>
            ),
            children: (
              <Descriptions column={1} size="small" bordered>
                {creativeIntent.concept && (
                  <Descriptions.Item label="创意概念">{creativeIntent.concept}</Descriptions.Item>
                )}
                {creativeIntent.subject && (
                  <Descriptions.Item label="主体">{creativeIntent.subject}</Descriptions.Item>
                )}
                {creativeIntent.subject_description && (
                  <Descriptions.Item label="主体描述">{creativeIntent.subject_description}</Descriptions.Item>
                )}
                {creativeIntent.scene && (
                  <Descriptions.Item label="场景">{creativeIntent.scene}</Descriptions.Item>
                )}
                {creativeIntent.action && (
                  <Descriptions.Item label="动作">{creativeIntent.action}</Descriptions.Item>
                )}
                {creativeIntent.emotion && (
                  <Descriptions.Item label="情绪">{creativeIntent.emotion}</Descriptions.Item>
                )}
                {creativeIntent.visual_style && (
                  <Descriptions.Item label="视觉风格">{creativeIntent.visual_style}</Descriptions.Item>
                )}
                {creativeIntent.camera_style && (
                  <Descriptions.Item label="镜头">{creativeIntent.camera_style}</Descriptions.Item>
                )}
                {creativeIntent.lighting && (
                  <Descriptions.Item label="光线">{creativeIntent.lighting}</Descriptions.Item>
                )}
                {creativeIntent.color_mood && (
                  <Descriptions.Item label="色彩">{creativeIntent.color_mood}</Descriptions.Item>
                )}
                {creativeIntent.creative_goal && (
                  <Descriptions.Item label="创作目标">{creativeIntent.creative_goal}</Descriptions.Item>
                )}
                {creativeIntent.inferred_needs && creativeIntent.inferred_needs.length > 0 && (
                  <Descriptions.Item label="推断需求">
                    {creativeIntent.inferred_needs.map((n, i) => (
                      <Tag key={i} style={{ marginBottom: 2 }}>{n}</Tag>
                    ))}
                  </Descriptions.Item>
                )}
              </Descriptions>
            ),
          }]}
        />
      )}
    </div>
  );
}
