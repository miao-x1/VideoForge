import { useEffect, useState } from 'react';
import { Card, Empty, Spin, Tag, Typography } from 'antd';
import { BookOutlined } from '@ant-design/icons';
import { api, type ProjectMemory } from '../api/client';

const { Text, Paragraph } = Typography;

interface Props {
  projectId: string;
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div style={{ marginBottom: 12 }}>
      <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>{title}</Text>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        {items.slice(0, 12).map((s, i) => <Tag key={i}>{s}</Tag>)}
      </div>
    </div>
  );
}

/**
 * 项目记忆面板:展示同项目沉淀的创作设定/主体/场景/风格。
 * 同项目新任务会自动继承这些设定,保持系列内容一致性。
 */
export default function ProjectMemoryPanel({ projectId }: Props) {
  const [memory, setMemory] = useState<ProjectMemory | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    api.getProjectMemory(projectId)
      .then((r) => setMemory(r.memory))
      .catch(() => setMemory(null))
      .finally(() => setLoading(false));
  }, [projectId]);

  if (!projectId) return null;
  if (loading) return <Card size="small" style={{ marginTop: 16 }}><Spin size="small" /></Card>;
  if (!memory) return null;

  const settings = memory.settings || {};
  const settingTags: string[] = [];
  if (settings.duration) settingTags.push(`${settings.duration}秒`);
  if (settings.aspect_ratio) settingTags.push(settings.aspect_ratio);
  if (settings.style) settingTags.push(String(settings.style));

  const hasContent = (memory.subjects?.length || 0) + (memory.scenes?.length || 0)
    + (memory.styles?.length || 0) + settingTags.length > 0;

  return (
    <Card
      size="small"
      style={{ marginTop: 16 }}
      title={<span><BookOutlined style={{ marginRight: 6 }} /><Text strong>项目记忆</Text></span>}
    >
      <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 12 }}>
        本项目沉淀的创作设定。在此项目中新创作时,AI 会自动继承这些设定,保持系列内容的一致性。
      </Text>
      {!hasContent ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无项目记忆——完成一次创作后,设定会自动沉淀到这里"
        />
      ) : (
        <>
          {settingTags.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>系列设定</Text>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {settingTags.map((t, i) => <Tag key={i} color="blue">{t}</Tag>)}
              </div>
            </div>
          )}
          <Section title="主体" items={memory.subjects || []} />
          <Section title="场景" items={memory.scenes || []} />
          <Section title="风格" items={memory.styles || []} />
          {(memory.videos?.length || 0) > 0 && (
            <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 0 }}>
              历史视频:{memory.videos!.length} 个 · 修改记录:{memory.modifications?.length || 0} 条
            </Paragraph>
          )}
        </>
      )}
    </Card>
  );
}
