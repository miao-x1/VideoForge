import { Steps } from 'antd';
import { CheckCircleFilled, LoadingOutlined, CloseCircleFilled } from '@ant-design/icons';
import type { TaskStatus } from '../api/client';

interface Props {
  status: TaskStatus;
  error: string | null;
}

// 按后端状态机定义的执行阶段顺序
const STAGES: { key: string; title: string; startStatus: TaskStatus }[] = [
  { key: 'req', title: '需求理解', startStatus: 'ANALYZING' },
  { key: 'script', title: '脚本生成', startStatus: 'SCRIPTING' },
  { key: 'story', title: '分镜生成', startStatus: 'STORYBOARDING' },
  { key: 'assets', title: '素材生成', startStatus: 'GENERATING_ASSETS' },
  { key: 'assemble', title: '视频合成', startStatus: 'ASSEMBLING' },
];

const STATUS_ORDER: Record<TaskStatus, number> = {
  PENDING: -1,
  ANALYZING: 0,
  SCRIPTING: 1,
  STORYBOARDING: 2,
  GENERATING_ASSETS: 3,
  ASSEMBLING: 4,
  COMPLETED: 5,
  FAILED: 5,
};

export default function ProgressTimeline({ status, error }: Props) {
  const currentIdx = STATUS_ORDER[status] ?? -1;
  const failed = status === 'FAILED';

  // 找到失败时卡在哪一步:取 currentIdx,但 COMPLETED/FAILED 都是 5
  const failedAt = failed ? (currentIdx < 0 ? 0 : Math.min(currentIdx, STAGES.length - 1)) : -1;

  const items = STAGES.map((stage, i) => {
    let state: 'finish' | 'process' | 'wait' | 'error' = 'wait';
    if (failed && i === failedAt) state = 'error';
    else if (i < currentIdx) state = 'finish';
    else if (i === currentIdx && !failed) state = 'process';
    else if (status === 'COMPLETED') state = 'finish';

    let icon;
    if (state === 'process') icon = <LoadingOutlined />;
    else if (state === 'finish') icon = <CheckCircleFilled style={{ color: '#52c41a' }} />;
    else if (state === 'error') icon = <CloseCircleFilled style={{ color: '#ff4d4f' }} />;

    return { title: stage.title, status: state as any, icon };
  });

  if (status === 'COMPLETED') {
    items.push({ title: '完成', status: 'finish', icon: <CheckCircleFilled style={{ color: '#52c41a' }} /> });
  }

  return (
    <div>
      <Steps direction="vertical" size="small" items={items} />
      {failed && error && (
        <div style={{ color: '#ff4d4f', marginTop: 8, fontSize: 13 }}>失败原因：{error}</div>
      )}
    </div>
  );
}
