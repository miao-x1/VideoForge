import { Button, Card, Descriptions, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import type { CreativeIntent } from '../api/client';

const { Title, Paragraph, Text } = Typography;

interface RecapProps {
  userInput: string;
  onNewCreation: () => void;
}

/** 创意节点(任务存在时):回顾原始创意输入 */
export function CreativeRecap({ userInput, onNewCreation }: RecapProps) {
  return (
    <Card>
      <Title level={4} style={{ marginBottom: 12 }}>你的创意</Title>
      <Paragraph style={{ fontSize: 15, whiteSpace: 'pre-wrap' }}>{userInput}</Paragraph>
      <Paragraph type="secondary" style={{ fontSize: 12 }}>
        创意已经 AI 结构化并进入生产流程,可在左侧节点导航中查看各阶段成果;修改创意将开始一次新创作。
      </Paragraph>
      <Button type="primary" icon={<PlusOutlined />} onClick={onNewCreation}>
        开始新创作
      </Button>
    </Card>
  );
}

const INTENT_FIELDS: { key: keyof CreativeIntent; label: string }[] = [
  { key: 'subject', label: '主体' },
  { key: 'subject_description', label: '主体描述' },
  { key: 'scene', label: '环境' },
  { key: 'action', label: '动作' },
  { key: 'emotion', label: '情绪' },
  { key: 'visual_style', label: '视觉风格' },
  { key: 'camera_style', label: '镜头' },
  { key: 'lighting', label: '光线' },
  { key: 'color_mood', label: '色彩' },
  { key: 'duration', label: '时长(秒)' },
  { key: 'aspect_ratio', label: '画幅' },
  { key: 'creative_goal', label: '创作目标' },
];

/** 创作方案节点(任务存在时):只读回顾已确认的创作方案 */
export function IntentSummary({ intent }: { intent: CreativeIntent }) {
  return (
    <Card>
      <Title level={4} style={{ marginBottom: 12 }}>创作方案(已确认)</Title>
      <Descriptions column={2} size="small" bordered>
        {INTENT_FIELDS.map(({ key, label }) => {
          const v = intent[key];
          if (v == null || v === '') return null;
          return (
            <Descriptions.Item key={String(key)} label={label}>
              <Text style={{ fontSize: 13 }}>{String(v)}</Text>
            </Descriptions.Item>
          );
        })}
      </Descriptions>
      {intent.constraints?.length ? (
        <Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0, fontSize: 12 }}>
          约束:{intent.constraints.join(';')}
        </Paragraph>
      ) : null}
    </Card>
  );
}
