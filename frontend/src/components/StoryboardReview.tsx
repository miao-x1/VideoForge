import { useState } from 'react';
import { Button, InputNumber, Popconfirm, Select, Tag, Typography, message } from 'antd';
import {
  ArrowDownOutlined,
  ArrowUpOutlined,
  CheckOutlined,
  DeleteOutlined,
  PlusOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons';
import { brand } from '../theme';
import RegenerateWithFeedback from './RegenerateWithFeedback';

const { Title, Text, Paragraph } = Typography;

export interface StoryboardShotData {
  scene_id: number;
  duration: number;
  shot_type: string;
  camera_movement: string;
  visual_description: string;
  character_action: string;
  dialogue: string;
  voiceover: string;
  background_music: string;
  sound_effect: string;
  image_prompt: string;
  video_prompt: string;
  negative_prompt: string;
  subtitle: string;
  transition: string;
  emotion: string;
  image_path?: string | null;
  audio_path?: string | null;
  video_path?: string | null;
}

export interface StoryboardData {
  shots: StoryboardShotData[];
}

interface Props {
  storyboard: StoryboardData;
  regenerating: boolean;
  shotRegenerating: number | null;
  submitting: boolean;
  onRegenerateAll: (feedback?: string) => void;
  onRegenerateShot: (shotIndex: number, feedback?: string) => void;
  onConfirm: (edited: StoryboardData) => void;
  onBack: () => void;
}

const SHOT_TYPES = [
  'wide shot', 'medium shot', 'close-up', 'extreme close-up',
  'over-the-shoulder', 'low angle', 'high angle', 'aerial shot',
];
const CAMERA_MOVES = [
  'static', 'slow push in', 'slow pull out', 'slow pan', 'tracking shot',
  'handheld', 'crane up', 'zoom in',
];
const TRANSITIONS = ['cut', 'fade', 'dissolve', 'slide'];

/** 可点击编辑的文本字段 */
function EditableField({
  label,
  value,
  onChange,
  placeholder,
  multiline,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  multiline?: boolean;
}) {
  const content = value || <span style={{ color: '#bbb' }}>{placeholder || '未填写'}</span>;
  const editable = {
    icon: <span style={{ color: brand.primary }}>编辑</span>,
    onChange,
    tooltip: '点击编辑',
  };
  return (
    <div>
      <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>
        {label}
      </Text>
      {multiline ? (
        <Paragraph editable={editable} style={{ margin: 0, fontSize: 14, lineHeight: 1.6, minHeight: 22, whiteSpace: 'pre-wrap' }}>
          {content}
        </Paragraph>
      ) : (
        <Text editable={editable} style={{ fontSize: 14, minHeight: 22, display: 'inline-block' }}>
          {content}
        </Text>
      )}
    </div>
  );
}

/**
 * Gate 3 分镜审核页:分镜已生成,等待用户确认。
 * 支持:编辑镜头字段 / 调整顺序 / 增删镜头 / 重新生成单镜头或全部分镜 / 确认进入 Prompt。
 */
export default function StoryboardReview({
  storyboard,
  regenerating,
  shotRegenerating,
  submitting,
  onRegenerateAll,
  onRegenerateShot,
  onConfirm,
  onBack,
}: Props) {
  const [draft, setDraft] = useState<StoryboardData>({ shots: [...storyboard.shots] });

  const totalDuration = draft.shots.reduce((s, sh) => s + (sh.duration || 0), 0);

  const updateShot = (index: number, patch: Partial<StoryboardShotData>) => {
    setDraft((d) => ({
      shots: d.shots.map((sh, i) => (i === index ? { ...sh, ...patch } : sh)),
    }));
  };

  const moveShot = (index: number, dir: -1 | 1) => {
    const target = index + dir;
    if (target < 0 || target >= draft.shots.length) return;
    setDraft((d) => {
      const shots = [...d.shots];
      [shots[index], shots[target]] = [shots[target], shots[index]];
      return { shots };
    });
  };

  const deleteShot = (index: number) => {
    setDraft((d) => ({ shots: d.shots.filter((_, i) => i !== index) }));
  };

  const addShot = () => {
    setDraft((d) => ({
      shots: [
        ...d.shots,
        {
          scene_id: d.shots.length ? d.shots[d.shots.length - 1].scene_id : 1,
          duration: 4,
          shot_type: 'medium shot',
          camera_movement: 'static',
          visual_description: '',
          character_action: '',
          dialogue: '',
          voiceover: '',
          background_music: '',
          sound_effect: '',
          image_prompt: '',
          video_prompt: '',
          negative_prompt: '',
          subtitle: '',
          transition: 'fade',
          emotion: 'neutral',
        },
      ],
    }));
  };

  const handleConfirm = () => {
    if (draft.shots.length === 0) {
      message.warning('至少需要一个镜头');
      return;
    }
    if (draft.shots.some((sh) => !sh.visual_description?.trim())) {
      message.warning('有镜头缺少画面描述,请补充或删除该镜头');
      return;
    }
    onConfirm(draft);
  };

  return (
    <div style={{ maxWidth: 860, margin: '0 auto', padding: '32px 8px' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 4 }}>
          <VideoCameraOutlined style={{ color: brand.primary, marginRight: 8 }} />
          分镜已生成 · 共 {draft.shots.length} 个镜头 · {totalDuration} 秒
        </Title>
        <Text type="secondary">
          以下是 AI 根据脚本拆解的分镜。你可以编辑任意镜头的画面、动作、景别与运镜,调整顺序,或让 AI 重新生成某个镜头。确认后才进入 Prompt 编译。
        </Text>
      </div>

      {/* 镜头列表 */}
      {draft.shots.map((shot, i) => (
        <div
          key={i}
          style={{
            background: shotRegenerating === i ? '#f6f9ff' : '#fff',
            borderRadius: 12,
            padding: 16,
            border: '1px solid #f0f0f0',
            marginBottom: 12,
            opacity: shotRegenerating === i ? 0.7 : 1,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <Tag color="geekblue" style={{ fontSize: 13, padding: '2px 10px' }}>
                镜头 {i + 1}
              </Tag>
              <Tag>场景 {shot.scene_id}</Tag>
              <InputNumber
                min={1}
                max={30}
                value={shot.duration}
                onChange={(v) => updateShot(i, { duration: Number(v) || 4 })}
                addonAfter="秒"
                style={{ width: 100 }}
                size="small"
              />
              <Select
                value={shot.shot_type || 'medium shot'}
                onChange={(v) => updateShot(i, { shot_type: v })}
                options={SHOT_TYPES.map((t) => ({ value: t, label: t }))}
                size="small"
                style={{ width: 150 }}
                showSearch
              />
              <Select
                value={shot.camera_movement || 'static'}
                onChange={(v) => updateShot(i, { camera_movement: v })}
                options={CAMERA_MOVES.map((t) => ({ value: t, label: t }))}
                size="small"
                style={{ width: 140 }}
                showSearch
              />
              <Select
                value={shot.transition || 'fade'}
                onChange={(v) => updateShot(i, { transition: v })}
                options={TRANSITIONS.map((t) => ({ value: t, label: `转场: ${t}` }))}
                size="small"
                style={{ width: 120 }}
              />
            </div>
            <div style={{ display: 'flex', gap: 2, flexShrink: 0 }}>
              <Button
                type="text" size="small" icon={<ArrowUpOutlined />}
                disabled={i === 0}
                onClick={() => moveShot(i, -1)}
                title="上移"
              />
              <Button
                type="text" size="small" icon={<ArrowDownOutlined />}
                disabled={i === draft.shots.length - 1}
                onClick={() => moveShot(i, 1)}
                title="下移"
              />
              <RegenerateWithFeedback
                iconOnly
                label="AI 重新生成该镜头"
                title="这个镜头哪里不满意?"
                placeholder="例如:换成特写,动作放慢"
                loading={shotRegenerating === i}
                size="small"
                onRegenerate={(fb) => onRegenerateShot(i, fb)}
              />
              <Popconfirm
                title="删除该镜头?"
                onConfirm={() => deleteShot(i)}
                okText="删除"
                cancelText="取消"
              >
                <Button type="text" danger size="small" icon={<DeleteOutlined />} title="删除镜头" />
              </Popconfirm>
            </div>
          </div>

          <EditableField label="画面" value={shot.visual_description} onChange={(v) => updateShot(i, { visual_description: v })} multiline placeholder="这一镜头的画面内容" />
          <div style={{ height: 12 }} />
          <EditableField label="主体动作" value={shot.character_action} onChange={(v) => updateShot(i, { character_action: v })} multiline placeholder="主体在画面中的动作" />
          {(shot.dialogue || shot.voiceover) && (
            <>
              <div style={{ height: 12 }} />
              <EditableField label="对白" value={shot.dialogue} onChange={(v) => updateShot(i, { dialogue: v })} multiline placeholder="角色说的话(可留空)" />
              <div style={{ height: 12 }} />
              <EditableField label="旁白" value={shot.voiceover} onChange={(v) => updateShot(i, { voiceover: v })} multiline placeholder="画外音(可留空)" />
            </>
          )}
        </div>
      ))}

      <Button
        block
        type="dashed"
        icon={<PlusOutlined />}
        onClick={addShot}
        style={{ marginBottom: 20, height: 44 }}
      >
        新增镜头
      </Button>

      {/* 操作区 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <Button size="large" icon={<ArrowUpOutlined style={{ transform: 'rotate(-90deg)' }} />} onClick={onBack}>
          返回脚本
        </Button>
        <div style={{ display: 'flex', gap: 12 }}>
          <RegenerateWithFeedback
            label="重新生成分镜"
            title="分镜哪里不满意?"
            placeholder="例如:第三镜头节奏太慢,多给特写"
            loading={regenerating}
            onRegenerate={(fb) => onRegenerateAll(fb)}
          />
          <Button
            type="primary"
            size="large"
            icon={<CheckOutlined />}
            loading={submitting}
            onClick={handleConfirm}
            style={{ minWidth: 160 }}
          >
            确认分镜
          </Button>
        </div>
      </div>
    </div>
  );
}
