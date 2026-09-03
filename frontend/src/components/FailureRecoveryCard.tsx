import { Alert, Button, Space, Typography } from 'antd';
import {
  ReloadOutlined,
  SwapOutlined,
  EditOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

export interface FailureDetail {
  stage?: string;
  reason?: string;
  error_code?: string;
  provider?: string;
  input_files?: string[];
}

interface Props {
  failureDetail: FailureDetail | null;
  error?: string | null;
  modelUsed?: string | null;
  hasPrompt?: boolean;
  hasStoryboard?: boolean;
  retrying?: boolean;
  onRetryFromStage: () => void;
  onSwitchModel: () => void;
  onEditPrompt: () => void;
  onBackToStoryboard: () => void;
}

// 失败阶段 → 用户可执行的恢复动作
const STAGE_ACTIONS: Record<string, string[]> = {
  // 素材/视频生成失败:重试该阶段 + 换模型
  GENERATING_ASSETS: ['retry', 'switch_model'],
  // Prompt 编译失败:重新编译/编辑 + 换模型
  PROMPT_REVIEW: ['retry', 'switch_model', 'edit_prompt'],
  // 分镜失败:重新生成分镜
  STORYBOARDING: ['retry'],
  STORYBOARD_REVIEW: ['retry'],
  // 脚本失败:重新生成脚本
  SCRIPTING: ['retry'],
  SCRIPT_REVIEW: ['retry'],
  // 合规:回到分镜/脚本修改(重试由后端修订循环处理)
  COMPLIANCE_CHECKING: ['retry'],
};

const ACTION_LABELS: Record<string, { label: string; icon: React.ReactNode }> = {
  retry: { label: '重试本阶段', icon: <ReloadOutlined /> },
  switch_model: { label: '更换模型', icon: <SwapOutlined /> },
  edit_prompt: { label: '修改 Prompt', icon: <EditOutlined /> },
};

// 已生成的中间产物提示(保留了多少工作成果)
function preservedSummary(failureDetail: FailureDetail | null): string | null {
  if (!failureDetail?.input_files?.length) return null;
  return `已保留 ${failureDetail.input_files.length} 个生成素材,重试不会重新生成已完成部分`;
}

export default function FailureRecoveryCard({
  failureDetail,
  error,
  modelUsed,
  hasPrompt,
  hasStoryboard,
  retrying,
  onRetryFromStage,
  onSwitchModel,
  onEditPrompt,
  onBackToStoryboard,
}: Props) {
  if (!failureDetail && !error) return null;

  const stage = failureDetail?.stage || '';
  const actions = STAGE_ACTIONS[stage] || ['retry'];
  const preserved = preservedSummary(failureDetail);

  return (
    <Alert
      type="error"
      showIcon
      style={{ marginTop: 12 }}
      message={
        <div>
          <div>
            <Text strong>生成失败</Text>
            {stage && (
              <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                (阶段: {stage})
              </Text>
            )}
          </div>
          {error && (
            <div style={{ marginTop: 4, fontSize: 13 }}>{error}</div>
          )}
          {failureDetail?.reason && (
            <div style={{ marginTop: 2, fontSize: 12, color: '#888' }}>
              原因: {failureDetail.reason}
            </div>
          )}
          {modelUsed && (
            <div style={{ marginTop: 2, fontSize: 12, color: '#888' }}>
              使用模型: {modelUsed}
            </div>
          )}
          {preserved && (
            <div style={{ marginTop: 4, fontSize: 12, color: '#faad14' }}>
              {preserved}
            </div>
          )}
        </div>
      }
      action={
        <Space wrap direction="vertical" size={4} style={{ marginTop: 8 }}>
          <Space wrap>
            {actions.map((key) => {
              const a = ACTION_LABELS[key];
              if (!a) return null;
              if (key === 'edit_prompt' && !hasPrompt) return null;
              return (
                <Button
                  key={key}
                  size="small"
                  icon={a.icon}
                  loading={key === 'retry' && retrying}
                  onClick={() => {
                    if (key === 'retry') onRetryFromStage();
                    else if (key === 'switch_model') onSwitchModel();
                    else if (key === 'edit_prompt') onEditPrompt();
                  }}
                >
                  {a.label}
                </Button>
              );
            })}
          </Space>
          {hasStoryboard && (
            <Button
              size="small"
              type="link"
              icon={<ArrowLeftOutlined />}
              onClick={onBackToStoryboard}
            >
              返回修改分镜
            </Button>
          )}
        </Space>
      }
    />
  );
}
