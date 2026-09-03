import { useState } from 'react';
import {
  Alert, Button, Card, Drawer, Input, InputNumber, List, Tag, Typography, message,
} from 'antd';
import { EditOutlined, ReloadOutlined } from '@ant-design/icons';
import { api } from '../api/client';

const { Text } = Typography;

export interface SceneItem {
  scene_id: number;
  duration: number;
  location: string;
  characters: string[];
  visual: string;
  dialogue: string;
  voiceover: string;
}

interface Props {
  taskId: string;
  scenes: SceneItem[];
  onReviseStarted: () => void;
}

/**
 * Scene 级局部修改面板:视频完成后,编辑某个脚本场景。
 * 依赖传播:Scene 编辑 → 关联镜头(scene_id) → Prompt → 关键帧图 → I2V 片段 → 重新合成。
 * 仅重新生成该场景关联镜头的完整链路,其余镜头素材直接复用。
 */
export default function SceneRevisePanel({ taskId, scenes, onReviseStarted }: Props) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [draft, setDraft] = useState<Partial<SceneItem>>({});
  const [impact, setImpact] = useState<{
    affected: number[]; unaffected: number[]; locked: number[]; message: string;
  } | null>(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [reviseFeedback, setReviseFeedback] = useState('');

  const openEdit = (index: number) => {
    const sc = scenes[index];
    setDraft({
      location: sc.location,
      visual: sc.visual,
      dialogue: sc.dialogue,
      voiceover: sc.voiceover,
      duration: sc.duration,
    });
    setImpact(null);
    setEditingIndex(index);
    setReviseFeedback('');
  };

  const previewImpact = async () => {
    if (editingIndex === null) return;
    setImpactLoading(true);
    try {
      const resp = await api.analyzeSceneImpact(taskId, editingIndex);
      setImpact(resp);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '影响分析失败');
    } finally {
      setImpactLoading(false);
    }
  };

  const confirmRevise = async () => {
    if (editingIndex === null) return;
    setSubmitting(true);
    try {
      await api.reviseScene(taskId, editingIndex, draft, reviseFeedback.trim() || undefined);
      message.success('已开始按场景局部重新生成受影响内容');
      setEditingIndex(null);
      onReviseStarted();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '场景局部重生成失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card size="small" style={{ marginTop: 16 }} title={<Text strong>场景级修改</Text>}>
      <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 12 }}>
        想调整某个场景的剧情或画面?直接编辑它——系统只重新生成该场景关联的镜头,其他场景的镜头保持不变。
      </Text>
      <List
        size="small"
        dataSource={scenes}
        renderItem={(scene, i) => (
          <List.Item
            actions={[
              <Button
                key="edit"
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => openEdit(i)}
              >
                修改此场景
              </Button>,
            ]}
          >
            <List.Item.Meta
              title={<span style={{ fontSize: 13 }}>场景 {scene.scene_id} · {scene.duration}s · {scene.location || '-'}</span>}
              description={
                <span style={{ fontSize: 12 }}>
                  {scene.visual?.slice(0, 80) || '无画面描述'}
                </span>
              }
            />
          </List.Item>
        )}
      />

      <Drawer
        title={`修改场景 ${editingIndex !== null ? editingIndex + 1 : ''}`}
        open={editingIndex !== null}
        onClose={() => setEditingIndex(null)}
        width={480}
        footer={
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
            <Button onClick={() => setEditingIndex(null)}>取消</Button>
            <Button icon={<ReloadOutlined />} loading={impactLoading} onClick={previewImpact}>
              预览影响
            </Button>
            <Button
              type="primary"
              loading={submitting}
              disabled={!impact || impact.affected.length === 0}
              onClick={confirmRevise}
            >
              确认重新生成受影响内容
            </Button>
          </div>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>场景地点</Text>
            <Input
              value={draft.location || ''}
              onChange={(e) => setDraft((d) => ({ ...d, location: e.target.value }))}
              placeholder="例如:雨夜的便利店门口"
            />
          </div>
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>画面描述</Text>
            <Input.TextArea
              value={draft.visual || ''}
              onChange={(e) => setDraft((d) => ({ ...d, visual: e.target.value }))}
              rows={3}
              placeholder="描述这个场景发生的事情与画面"
            />
          </div>
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>对白</Text>
            <Input.TextArea
              value={draft.dialogue || ''}
              onChange={(e) => setDraft((d) => ({ ...d, dialogue: e.target.value }))}
              rows={2}
            />
          </div>
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>旁白</Text>
            <Input.TextArea
              value={draft.voiceover || ''}
              onChange={(e) => setDraft((d) => ({ ...d, voiceover: e.target.value }))}
              rows={2}
            />
          </div>
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>场景时长(秒)</Text>
            <InputNumber
              min={3}
              max={60}
              value={draft.duration || 5}
              onChange={(v) => setDraft((d) => ({ ...d, duration: Number(v) || 5 }))}
            />
          </div>

          <div>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
              补充说明(可选):告诉 AI 期望的修改方向
            </Text>
            <Input.TextArea
              value={reviseFeedback}
              onChange={(e) => setReviseFeedback(e.target.value)}
              placeholder="例如:节奏加快,冲突更激烈"
              rows={2}
              maxLength={200}
              showCount
            />
          </div>

          {impact && (
            <Alert
              type={impact.affected.length > 0 ? 'warning' : 'info'}
              showIcon
              message="检测到内容变化"
              description={
                <div style={{ fontSize: 13 }}>
                  <div>
                    <Text strong>将受到影响:</Text>{' '}
                    {impact.affected.length > 0
                      ? impact.affected.map((n) => <Tag key={n} color="orange">镜头 {n}</Tag>)
                      : <Tag>无(可能已被锁定)</Tag>}
                  </div>
                  <div style={{ marginTop: 4 }}>
                    <Text strong>不会受到影响:</Text>{' '}
                    {impact.unaffected.length > 0
                      ? impact.unaffected.map((n) => <Tag key={n} color="green">镜头 {n}</Tag>)
                      : <Tag color="green">无</Tag>}
                  </div>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    将重新生成受影响镜头的分镜/Prompt/关键帧/音视频并重新合成整片;其余镜头素材直接复用。
                  </Text>
                </div>
              }
            />
          )}
        </div>
      </Drawer>
    </Card>
  );
}
