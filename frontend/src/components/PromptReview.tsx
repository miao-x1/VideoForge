import { useState } from 'react';
import { Button, Collapse, Descriptions, Divider, Input, Typography, message } from 'antd';
import {
  CheckOutlined,
  CodeOutlined,
  ExperimentFilled,
} from '@ant-design/icons';
import ModelSelector from './ModelSelector';
import RegenerateWithFeedback from './RegenerateWithFeedback';

const { Title, Text } = Typography;

export interface StructuredPromptData {
  shot_index: number;
  subject: string;
  environment: string;
  action: string;
  composition: string;
  camera: string;
  lighting: string;
  visual_style: string;
  emotion: string;
  sound: string;
  rhythm: string;
  raw_image_prompt: string;
  raw_video_prompt: string;
  negative_prompt: string;
  generation_params: Record<string, any>;
  model_id: string;
  model_convention: string;
}

export interface PromptResultData {
  prompts: StructuredPromptData[];
  model_id: string;
  model_capabilities: Record<string, any>;
  compilation_notes: string;
}

interface Props {
  result: PromptResultData;
  routingDecision?: any | null;
  regenerating: boolean;
  switchingModel: boolean;
  submitting: boolean;
  onRegenerate: (feedback?: string) => void;
  onSwitchModel: (modelId: string) => void;
  onConfirm: (edited: PromptResultData) => void;
  onBack: () => void;
}

/**
 * Gate 4 Prompt 审核页:专业 Prompt 已编译,等待用户确认。
 * 支持:编辑 Raw Prompt / Negative Prompt(结构化维度折叠展示)、重新编译、确认后进入生成。
 */
export default function PromptReview({
  result,
  routingDecision,
  regenerating,
  switchingModel,
  submitting,
  onRegenerate,
  onSwitchModel,
  onConfirm,
  onBack,
}: Props) {
  const [draft, setDraft] = useState<PromptResultData>({ ...result, prompts: result.prompts.map((p) => ({ ...p })) });

  const modelName = routingDecision?.selected_model_id || draft.model_id || '';
  const reason = routingDecision?.reason || '';
  const qualityStars = routingDecision?.quality_stars || 0;
  const speedStars = routingDecision?.speed_stars || 0;
  const costStars = routingDecision?.cost_stars || 0;

  const updatePrompt = (index: number, patch: Partial<StructuredPromptData>) => {
    setDraft((d) => ({
      ...d,
      prompts: d.prompts.map((p, i) => (i === index ? { ...p, ...patch } : p)),
    }));
  };

  const handleConfirm = () => {
    if (draft.prompts.some((p) => !p.raw_image_prompt?.trim())) {
      message.warning('有镜头缺少文生图 Prompt,请补充');
      return;
    }
    onConfirm(draft);
  };

  return (
    <div style={{ maxWidth: 860, margin: '0 auto', padding: '32px 8px' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 4 }}>
          <ExperimentFilled style={{ color: '#722ed1', marginRight: 8 }} />
          专业 Prompt 已编译
        </Title>
        <Text type="secondary">
          以下是将真实发送给生成模型的专业 Prompt。你可以直接编辑文本,或让 AI 重新编译。确认后开始生成视频。
        </Text>
      </div>

      {/* 模型信息 + 手动切换 */}
      <div style={{ marginBottom: 16, padding: '12px 16px', background: '#f9f0ff', border: '1px solid #d3adf7', borderRadius: 8 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4, justifyContent: 'space-between' }}>
          <Text strong>当前模型: {modelName}</Text>
          <ModelSelector currentModelId={modelName} switching={switchingModel} onSwitch={onSwitchModel} />
        </div>
        {reason && (
          <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>
            选择原因: {reason}
          </Text>
        )}
        <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#666', marginTop: 4 }}>
          <span>质量 {'★'.repeat(qualityStars)}{'☆'.repeat(5 - qualityStars)}</span>
          <span>速度 {'★'.repeat(speedStars)}{'☆'.repeat(5 - speedStars)}</span>
          <span>成本 {'★'.repeat(costStars)}{'☆'.repeat(5 - costStars)}</span>
        </div>
        {draft.compilation_notes && (
          <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 4 }}>
            编译说明: {draft.compilation_notes}
          </Text>
        )}
      </div>

      {/* 每个镜头的 Prompt */}
      {draft.prompts.map((p, i) => (
        <div key={i} style={{ background: '#fff', borderRadius: 12, padding: 16, border: '1px solid #f0f0f0', marginBottom: 12 }}>
          <Divider style={{ margin: '0 0 12px', fontSize: 13 }} orientation="left">
            镜头 {p.shot_index + 1}
          </Divider>

          {/* Raw Image Prompt(可编辑) */}
          <div style={{ marginBottom: 10 }}>
            <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 4 }}>
              <CodeOutlined /> 文生图 Prompt
            </Text>
            <Input.TextArea
              value={p.raw_image_prompt}
              onChange={(e) => updatePrompt(i, { raw_image_prompt: e.target.value })}
              autoSize={{ minRows: 2, maxRows: 6 }}
              style={{ fontFamily: 'monospace', fontSize: 12 }}
            />
          </div>

          {/* Raw Video Prompt(可编辑) */}
          <div style={{ marginBottom: 10 }}>
            <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 4 }}>
              <CodeOutlined /> 文生视频 Prompt
            </Text>
            <Input.TextArea
              value={p.raw_video_prompt}
              onChange={(e) => updatePrompt(i, { raw_video_prompt: e.target.value })}
              autoSize={{ minRows: 2, maxRows: 6 }}
              style={{ fontFamily: 'monospace', fontSize: 12 }}
            />
          </div>

          {/* Negative Prompt(可编辑) */}
          <div>
            <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 4 }}>
              <CodeOutlined /> Negative Prompt(负面提示词)
            </Text>
            <Input.TextArea
              value={p.negative_prompt}
              onChange={(e) => updatePrompt(i, { negative_prompt: e.target.value })}
              autoSize={{ minRows: 1, maxRows: 3 }}
              style={{ fontFamily: 'monospace', fontSize: 12 }}
              placeholder="模型不支持负面提示词时可留空"
            />
          </div>

          {/* 结构化维度(折叠,B级) */}
          <Collapse
            size="small"
            ghost
            style={{ marginTop: 8 }}
            items={[{
              key: `detail_${i}`,
              label: <Text type="secondary" style={{ fontSize: 12 }}>结构化维度 ▼</Text>,
              children: (
                <Descriptions column={1} size="small" bordered style={{ fontSize: 12 }}>
                  {p.subject && <Descriptions.Item label="主体">{p.subject}</Descriptions.Item>}
                  {p.environment && <Descriptions.Item label="环境">{p.environment}</Descriptions.Item>}
                  {p.action && <Descriptions.Item label="动作">{p.action}</Descriptions.Item>}
                  {p.composition && <Descriptions.Item label="构图">{p.composition}</Descriptions.Item>}
                  {p.camera && <Descriptions.Item label="镜头">{p.camera}</Descriptions.Item>}
                  {p.lighting && <Descriptions.Item label="光线">{p.lighting}</Descriptions.Item>}
                  {p.visual_style && <Descriptions.Item label="风格">{p.visual_style}</Descriptions.Item>}
                  {p.emotion && <Descriptions.Item label="情绪">{p.emotion}</Descriptions.Item>}
                  {p.model_convention && <Descriptions.Item label="模型约定">{p.model_convention}</Descriptions.Item>}
                </Descriptions>
              ),
            }]}
          />
        </div>
      ))}

      {/* 操作区 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginTop: 8 }}>
        <Button size="large" onClick={onBack}>
          返回分镜
        </Button>
        <div style={{ display: 'flex', gap: 12 }}>
          <RegenerateWithFeedback
            label="重新编译 Prompt"
            title="Prompt 哪里不满意?"
            placeholder="例如:人物不够真实,镜头改为手持跟拍"
            loading={regenerating}
            onRegenerate={(fb) => onRegenerate(fb)}
          />
          <Button
            type="primary"
            size="large"
            icon={<CheckOutlined />}
            loading={submitting}
            onClick={handleConfirm}
            style={{ minWidth: 180 }}
          >
            确认并开始生成
          </Button>
        </div>
      </div>
    </div>
  );
}
