import { useState } from 'react';
import { Button, InputNumber, Select, Tag, Typography, message } from 'antd';
import { ArrowLeftOutlined, CheckOutlined, EditOutlined, BulbOutlined } from '@ant-design/icons';
import type { CreativeIntent } from '../api/client';
import { brand } from '../theme';

const { Title, Text, Paragraph } = Typography;

const RATIOS = [
  { label: '9:16', value: '9:16' },
  { label: '16:9', value: '16:9' },
  { label: '1:1', value: '1:1' },
];

interface Props {
  intent: CreativeIntent;
  submitting: boolean;
  onBack: () => void;
  onConfirm: (edited: CreativeIntent) => void;
}

/** 可点击编辑的意图字段 */
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
    icon: <EditOutlined style={{ color: brand.primary }} />,
    onChange,
    tooltip: '点击编辑',
  };
  return (
    <div>
      <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>
        {label}
      </Text>
      {multiline ? (
        <Paragraph
          editable={editable}
          style={{ margin: 0, fontSize: 14, lineHeight: 1.6, minHeight: 22, whiteSpace: 'pre-wrap' }}
        >
          {content}
        </Paragraph>
      ) : (
        <Text
          editable={editable}
          style={{ fontSize: 14, minHeight: 22, display: 'inline-block' }}
        >
          {content}
        </Text>
      )}
    </div>
  );
}

/**
 * Gate 1 创作方案确认页:AI 已理解你的创意。
 * 每个字段可点击编辑;确认后才进入脚本生成。
 */
export default function IntentReview({ intent, submitting, onBack, onConfirm }: Props) {
  const [draft, setDraft] = useState<CreativeIntent>(intent);

  const set = (field: keyof CreativeIntent, value: any) => {
    setDraft((d) => ({ ...d, [field]: value }));
  };

  const handleConfirm = () => {
    if (!draft.concept?.trim()) {
      message.warning('请补充作品主题');
      return;
    }
    onConfirm(draft);
  };

  return (
    <div style={{ maxWidth: 860, margin: '0 auto', padding: '32px 8px' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 4 }}>
          <BulbOutlined style={{ color: brand.primary, marginRight: 8 }} />
          AI 已理解你的创意
        </Title>
        <Text type="secondary">
          以下内容来自 AI 对你创意的理解,点击任意字段即可修改。确认后将作为创作方案生成脚本。
        </Text>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
          gap: '20px 28px',
          background: '#fff',
          borderRadius: 12,
          padding: 24,
          border: '1px solid #f0f0f0',
          marginBottom: 20,
        }}
      >
        <EditableField label="作品主题" value={draft.concept} onChange={(v) => set('concept', v)} />
        <EditableField label="主体" value={draft.subject} onChange={(v) => set('subject', v)} placeholder="可以是人 / 物 / 场景 / 事件" />
        <EditableField label="场景" value={draft.scene} onChange={(v) => set('scene', v)} />
        <EditableField label="动作" value={draft.action} onChange={(v) => set('action', v)} />
        <EditableField label="情绪" value={draft.emotion} onChange={(v) => set('emotion', v)} />
        <EditableField label="视觉风格" value={draft.visual_style} onChange={(v) => set('visual_style', v)} />
        <EditableField label="镜头语言" value={draft.camera_style} onChange={(v) => set('camera_style', v)} />
        <EditableField label="光线" value={draft.lighting} onChange={(v) => set('lighting', v)} />
        <EditableField label="色彩情绪" value={draft.color_mood} onChange={(v) => set('color_mood', v)} />

        <div>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>
            时长(秒)
          </Text>
          <InputNumber
            min={5}
            max={120}
            value={draft.duration}
            onChange={(v) => set('duration', Number(v) || 15)}
            style={{ width: 100 }}
          />
        </div>
        <div>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>
            画面比例
          </Text>
          <Select
            value={draft.aspect_ratio}
            onChange={(v) => set('aspect_ratio', v)}
            options={RATIOS}
            style={{ width: 100 }}
          />
        </div>

        {draft.subject_description && (
          <div style={{ gridColumn: '1 / -1' }}>
            <EditableField
              label="主体描述"
              value={draft.subject_description}
              onChange={(v) => set('subject_description', v)}
              multiline
            />
          </div>
        )}
        {draft.scene_description && (
          <div style={{ gridColumn: '1 / -1' }}>
            <EditableField
              label="场景描述"
              value={draft.scene_description}
              onChange={(v) => set('scene_description', v)}
              multiline
            />
          </div>
        )}
        {draft.creative_goal && (
          <div style={{ gridColumn: '1 / -1' }}>
            <EditableField
              label="创作目标"
              value={draft.creative_goal}
              onChange={(v) => set('creative_goal', v)}
              multiline
            />
          </div>
        )}
      </div>

      {draft.inferred_needs?.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            AI 推断的创作需求(未在意图中明确,将体现在脚本与分镜中)
          </Text>
          <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {draft.inferred_needs.map((need, i) => (
              <Tag key={i} color="geekblue" style={{ fontSize: 12 }}>
                {need}
              </Tag>
            ))}
          </div>
        </div>
      )}

      {draft.constraints?.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            创作约束
          </Text>
          <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {draft.constraints.map((c, i) => (
              <Tag key={i} color="orange" style={{ fontSize: 12 }}>
                {c}
              </Tag>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <Button size="large" icon={<ArrowLeftOutlined />} onClick={onBack}>
          返回修改创意
        </Button>
        <Button
          type="primary"
          size="large"
          icon={<CheckOutlined />}
          loading={submitting}
          onClick={handleConfirm}
          style={{ minWidth: 200 }}
        >
          确认创作方案
        </Button>
      </div>
    </div>
  );
}
