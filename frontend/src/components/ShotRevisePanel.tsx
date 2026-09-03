import { useState } from 'react';
import {
  Alert, Button, Card, Drawer, Input, InputNumber, List, Select, Tag, Typography, message,
} from 'antd';
import {
  EditOutlined, LockFilled, ReloadOutlined, UnlockOutlined,
} from '@ant-design/icons';
import { api } from '../api/client';

const { Text } = Typography;

export interface ShotItem {
  scene_id: number;
  duration: number;
  shot_type: string;
  camera_movement: string;
  visual_description: string;
  character_action: string;
  dialogue: string;
  voiceover: string;
  image_prompt: string;
  video_prompt: string;
  negative_prompt: string;
  locked?: boolean;
  image_path?: string | null;
  audio_path?: string | null;
  video_path?: string | null;
}

interface Props {
  taskId: string;
  shots: ShotItem[];
  onReviseStarted: () => void;
  onLockChanged: () => void;
}

const SHOT_TYPES = ['wide shot', 'medium shot', 'close-up', 'extreme close-up', 'over-the-shoulder', 'low angle', 'high angle', 'aerial shot'];
const CAMERA_MOVES = ['static', 'slow push in', 'slow pull out', 'slow pan', 'tracking shot', 'handheld', 'crane up', 'zoom in'];

/**
 * 局部修改面板:视频完成后,用户指出某个镜头的问题并修改。
 * 依赖图分析 → 仅重新生成受影响镜头(Prompt/图/音/视频),其他镜头素材直接复用。
 * 支持锁定镜头,防止重生成时被修改(对连续角色/场景保持一致性)。
 */
export default function ShotRevisePanel({ taskId, shots, onReviseStarted, onLockChanged }: Props) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [draft, setDraft] = useState<Partial<ShotItem>>({});
  const [impact, setImpact] = useState<{ affected: number[]; unaffected: number[]; message: string } | null>(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [lockToggling, setLockToggling] = useState<number | null>(null);
  // Decision Loop:修改说明(哪里不满意/期望效果),注入单镜头 Prompt 重编译
  const [reviseFeedback, setReviseFeedback] = useState('');

  const openEdit = (index: number) => {
    const s = shots[index];
    setDraft({
      visual_description: s.visual_description,
      character_action: s.character_action,
      shot_type: s.shot_type,
      camera_movement: s.camera_movement,
      voiceover: s.voiceover,
      duration: s.duration,
    });
    setImpact(null);
    setEditingIndex(index);
    setReviseFeedback('');
  };

  const previewImpact = async () => {
    if (editingIndex === null) return;
    setImpactLoading(true);
    try {
      const resp = await api.analyzeShotImpact(taskId, [editingIndex]);
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
      await api.reviseShots(
        taskId, [editingIndex],
        { [String(editingIndex)]: draft },
        reviseFeedback.trim() || undefined,
      );
      message.success('已开始局部重新生成受影响内容');
      setEditingIndex(null);
      onReviseStarted();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '局部重生成失败');
    } finally {
      setSubmitting(false);
    }
  };

  const toggleLock = async (index: number) => {
    setLockToggling(index);
    try {
      await api.toggleShotLock(taskId, index, !shots[index].locked);
      onLockChanged();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '锁定操作失败');
    } finally {
      setLockToggling(null);
    }
  };

  return (
    <Card size="small" style={{ marginTop: 16 }} title={<Text strong>局部修改</Text>}>
      <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 12 }}>
        不满意某个镜头?直接修改它——系统只重新生成受影响的镜头,其他镜头保持不变。锁定镜头可防止其在任何重生成中被修改。
      </Text>
      <List
        size="small"
        dataSource={shots}
        renderItem={(shot, i) => {
          const imgFile = shot.image_path?.split(/[\\/]/).pop();
          const imgUrl = imgFile ? `/storage/images/${imgFile}` : null;
          return (
            <List.Item
              actions={[
                <Button
                  key="lock"
                  type="text"
                  size="small"
                  icon={shot.locked ? <LockFilled style={{ color: '#faad14' }} /> : <UnlockOutlined />}
                  loading={lockToggling === i}
                  onClick={() => toggleLock(i)}
                  title={shot.locked ? '已锁定,点击解锁' : '点击锁定(重生成时不会修改)'}
                >
                  {shot.locked ? '已锁定' : '锁定'}
                </Button>,
                <Button
                  key="edit"
                  type="link"
                  size="small"
                  icon={<EditOutlined />}
                  disabled={shot.locked}
                  onClick={() => openEdit(i)}
                >
                  修改此镜头
                </Button>,
              ]}
            >
              <List.Item.Meta
                avatar={
                  imgUrl ? (
                    <img
                      src={imgUrl}
                      alt={`镜头${i + 1}`}
                      style={{ width: 64, height: 36, objectFit: 'cover', borderRadius: 4 }}
                      onError={(e) => { (e.target as HTMLImageElement).style.visibility = 'hidden'; }}
                    />
                  ) : undefined
                }
                title={<span style={{ fontSize: 13 }}>镜头 {i + 1} · {shot.duration}s · {shot.shot_type || '-'}</span>}
                description={
                  <span style={{ fontSize: 12 }}>
                    {shot.visual_description?.slice(0, 80) || '无描述'}
                  </span>
                }
              />
            </List.Item>
          );
        }}
      />

      <Drawer
        title={`修改镜头 ${editingIndex !== null ? editingIndex + 1 : ''}`}
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
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>画面描述</Text>
            <Input.TextArea
              value={draft.visual_description || ''}
              onChange={(e) => setDraft((d) => ({ ...d, visual_description: e.target.value }))}
              rows={3}
            />
          </div>
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>主体动作</Text>
            <Input.TextArea
              value={draft.character_action || ''}
              onChange={(e) => setDraft((d) => ({ ...d, character_action: e.target.value }))}
              rows={2}
            />
          </div>
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>旁白(留空则使用画面描述)</Text>
            <Input.TextArea
              value={draft.voiceover || ''}
              onChange={(e) => setDraft((d) => ({ ...d, voiceover: e.target.value }))}
              rows={2}
            />
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ flex: 1 }}>
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>景别</Text>
              <Select
                value={draft.shot_type || 'medium shot'}
                onChange={(v) => setDraft((d) => ({ ...d, shot_type: v }))}
                options={SHOT_TYPES.map((t) => ({ value: t, label: t }))}
                style={{ width: '100%' }}
                showSearch
              />
            </div>
            <div style={{ flex: 1 }}>
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>运镜</Text>
              <Select
                value={draft.camera_movement || 'static'}
                onChange={(v) => setDraft((d) => ({ ...d, camera_movement: v }))}
                options={CAMERA_MOVES.map((t) => ({ value: t, label: t }))}
                style={{ width: '100%' }}
                showSearch
              />
            </div>
            <div>
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>时长(秒)</Text>
              <InputNumber
                min={2}
                max={15}
                value={draft.duration || 5}
                onChange={(v) => setDraft((d) => ({ ...d, duration: Number(v) || 5 }))}
              />
            </div>
          </div>

          <div>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
              补充说明(可选):告诉 AI 期望的修改方向
            </Text>
            <Input.TextArea
              value={reviseFeedback}
              onChange={(e) => setReviseFeedback(e.target.value)}
              placeholder="例如:画面整体调暗一些,增加雨夜氛围"
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
                    将重新生成受影响镜头的 Prompt/关键帧/音视频并重新合成整片。
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
