import { Collapse, Typography, Descriptions, Divider, Row, Col } from 'antd';
import {
  CodeOutlined,
  ExperimentFilled,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { accents, calloutStyle, colors } from '../theme';

const { Text, Paragraph } = Typography;

interface StructuredPrompt {
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

interface PromptEngineeringResult {
  prompts: StructuredPrompt[];
  model_id: string;
  model_capabilities: Record<string, any>;
  compilation_notes: string;
}

interface Props {
  result: PromptEngineeringResult | null;
  routingDecision?: any | null;
}

export default function PromptInspector({ result, routingDecision }: Props) {
  if (!result || !result.prompts?.length) return null;

  const modelName = routingDecision?.selected_model_id || result.model_id || '';
  const reason = routingDecision?.reason || '';
  const qualityStars = routingDecision?.quality_stars || 0;
  const speedStars = routingDecision?.speed_stars || 0;
  const costStars = routingDecision?.cost_stars || 0;

  return (
    <Collapse
      size="small"
      style={{ marginTop: 12 }}
      items={[{
        key: 'prompt_inspector',
        label: (
          <span>
            <ExperimentFilled style={{ color: accents.brand.text, marginRight: 6 }} />
            Prompt Inspector · {result.prompts.length} 个镜头
          </span>
        ),
        children: (
          <div>
            {/* 模型信息 */}
            <div style={{ marginBottom: 8, ...calloutStyle(accents.brand), padding: '8px 10px' }}>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 4 }}>
                <InfoCircleOutlined style={{ color: accents.brand.text }} />
                <Text strong>当前模型: {modelName}</Text>
              </div>
              {reason && (
                <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>
                  选择原因: {reason}
                </Text>
              )}
              <div style={{ display: 'flex', gap: 12, fontSize: 12, color: colors.textMuted, marginTop: 4 }}>
                <span>质量 {'★'.repeat(qualityStars)}{'☆'.repeat(5 - qualityStars)}</span>
                <span>速度 {'★'.repeat(speedStars)}{'☆'.repeat(5 - speedStars)}</span>
                <span>成本 {'★'.repeat(costStars)}{'☆'.repeat(5 - costStars)}</span>
              </div>
              {result.compilation_notes && (
                <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 4 }}>
                  编译说明: {result.compilation_notes}
                </Text>
              )}
            </div>

            {/* 每个镜头的 Prompt */}
            {result.prompts.map((p, i) => (
              <div key={i} style={{ marginBottom: 8 }}>
                <Divider style={{ margin: '8px 0', fontSize: 13 }} orientation="left">
                  镜头 {p.shot_index + 1}
                </Divider>
                <Row gutter={12}>
                  {/* 左侧: 结构化 Prompt */}
                  <Col span={12}>
                    <Descriptions column={1} size="small" bordered style={{ fontSize: 12 }}>
                      {p.subject && <Descriptions.Item label="主体">{p.subject}</Descriptions.Item>}
                      {p.environment && <Descriptions.Item label="环境">{p.environment}</Descriptions.Item>}
                      {p.action && <Descriptions.Item label="动作">{p.action}</Descriptions.Item>}
                      {p.composition && <Descriptions.Item label="构图">{p.composition}</Descriptions.Item>}
                      {p.camera && <Descriptions.Item label="镜头">{p.camera}</Descriptions.Item>}
                      {p.lighting && <Descriptions.Item label="光线">{p.lighting}</Descriptions.Item>}
                      {p.visual_style && <Descriptions.Item label="风格">{p.visual_style}</Descriptions.Item>}
                      {p.emotion && <Descriptions.Item label="情绪">{p.emotion}</Descriptions.Item>}
                      {p.sound && <Descriptions.Item label="声音">{p.sound}</Descriptions.Item>}
                      {p.rhythm && <Descriptions.Item label="节奏">{p.rhythm}</Descriptions.Item>}
                    </Descriptions>
                  </Col>
                  {/* 右侧: Raw Prompt */}
                  <Col span={12}>
                    <div style={{ ...calloutStyle(accents.info), padding: '6px 8px', marginBottom: 4 }}>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        <CodeOutlined /> Raw Image Prompt
                      </Text>
                      <Paragraph style={{ margin: '4px 0 0', fontSize: 11, fontFamily: 'monospace', wordBreak: 'break-word' }}>
                        {p.raw_image_prompt}
                      </Paragraph>
                    </div>
                    <div style={{ ...calloutStyle(accents.brand), padding: '6px 8px', marginBottom: 4 }}>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        <CodeOutlined /> Raw Video Prompt
                      </Text>
                      <Paragraph style={{ margin: '4px 0 0', fontSize: 11, fontFamily: 'monospace', wordBreak: 'break-word' }}>
                        {p.raw_video_prompt}
                      </Paragraph>
                    </div>
                    {p.negative_prompt && (
                      <div style={{ ...calloutStyle(accents.error), padding: '6px 8px' }}>
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          <CodeOutlined /> Negative Prompt
                        </Text>
                        <Paragraph style={{ margin: '4px 0 0', fontSize: 11, fontFamily: 'monospace', wordBreak: 'break-word' }}>
                          {p.negative_prompt}
                        </Paragraph>
                      </div>
                    )}
                  </Col>
                </Row>
              </div>
            ))}
          </div>
        ),
      }]}
    />
  );
}
