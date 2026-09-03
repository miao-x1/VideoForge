import { useEffect, useRef } from 'react';
import { Card, Typography, Tag, Spin, Empty } from 'antd';
import { RobotOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useCreativeStore } from '../store/useCreativeStore';
import { api, type AnalyzeResp } from '../api/client';
import { brand, cardStyle } from '../theme';

const { Text, Paragraph } = Typography;

const DIMENSION_LABELS: Record<string, string> = {
  prompt: '创意描述',
  creative_elements: '创作元素',
  environment: '场景环境',
  narrative: '叙事结构',
  motion: '运动控制',
  visual_style: '视觉风格',
  camera: '镜头控制',
  audio: '音频设置',
  references: '参考素材',
  advanced: '高级参数',
};

export default function AIPlanPanel() {
  const spec = useCreativeStore((s) => s.spec);
  const analysis = useCreativeStore((s) => s.analysis);
  const analysisLoading = useCreativeStore((s) => s.analysisLoading);
  const setAnalysis = useCreativeStore((s) => s.setAnalysis);
  const setAnalysisLoading = useCreativeStore((s) => s.setAnalysisLoading);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const specKey = JSON.stringify(spec);

  useEffect(() => {
    if (!spec.prompt.trim()) {
      setAnalysis(null);
      return;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setAnalysisLoading(true);
      try {
        const result: AnalyzeResp = await api.analyzeCreativeIntent({
          spec,
          prompt: spec.prompt,
          duration: spec.duration,
          style: spec.custom_style,
          aspect_ratio: spec.aspect_ratio,
        });
        setAnalysis(result);
      } catch {
        setAnalysis(null);
      } finally {
        setAnalysisLoading(false);
      }
    }, 600);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [specKey]);

  const hasContent = spec.prompt.trim().length > 0;

  return (
    <div
      style={{
        ...cardStyle,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* 标题 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <RobotOutlined style={{ fontSize: 18, color: brand.primary }} />
        <Text strong style={{ fontSize: 15 }}>
          AI 创作计划
        </Text>
        <Tag color="purple" style={{ marginLeft: 'auto', fontSize: 11 }}>
          AI 助手
        </Tag>
      </div>

      {!hasContent ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="输入创意后, AI 将分析创作意图"
            imageStyle={{ height: 40 }}
          />
        </div>
      ) : analysisLoading ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Spin size="small" />
        </div>
      ) : analysis ? (
        <div style={{ flex: 1, overflow: 'auto' }}>
          {/* 推荐模型 */}
          {analysis.recommended_model && (
            <Card
              size="small"
              style={{ marginBottom: 12, background: '#f6f8ff', border: '1px solid #e6eaff' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <ThunderboltOutlined style={{ color: brand.primary, fontSize: 14 }} />
                <Text strong style={{ fontSize: 13 }}>
                  推荐模型: {analysis.recommended_model.selected_provider}
                </Text>
              </div>
              {analysis.recommended_model.reason && (
                <Paragraph
                  type="secondary"
                  style={{ fontSize: 12, margin: '4px 0 0', lineHeight: 1.5 }}
                >
                  {analysis.recommended_model.reason}
                </Paragraph>
              )}
            </Card>
          )}

          {/* 编译后的 prompt */}
          <div style={{ marginBottom: 12 }}>
            <Text type="secondary" style={{ fontSize: 12, fontWeight: 500 }}>
              编译后的创作意图
            </Text>
            <div
              style={{
                background: '#f5f5f5',
                borderRadius: 8,
                padding: 12,
                marginTop: 4,
                fontSize: 13,
                lineHeight: 1.6,
                whiteSpace: 'pre-wrap',
                maxHeight: 200,
                overflow: 'auto',
              }}
            >
              {analysis.compiled_prompt}
            </div>
          </div>

          {/* 维度摘要 */}
          <div>
            <Text type="secondary" style={{ fontSize: 12, fontWeight: 500 }}>
              创作维度
            </Text>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
              {Object.entries(analysis.dimensions || {}).map(([key, active]) => (
                <Tag
                  key={key}
                  color={active ? 'blue' : 'default'}
                  style={{ fontSize: 11, opacity: active ? 1 : 0.4 }}
                >
                  {DIMENSION_LABELS[key] || key}
                </Tag>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Text type="secondary" style={{ fontSize: 13 }}>
            分析服务暂时不可用
          </Text>
        </div>
      )}
    </div>
  );
}
