import { Collapse, Tag, Typography, Card, Row, Col, Tooltip } from 'antd';
import { VideoCameraOutlined, LinkOutlined, ArrowRightOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { accents } from '../theme';
import type { ProjectState, ShotStateEntry, GenerationDecision, QualityReportItem } from '../api/client';

const { Text, Paragraph } = Typography;

interface StoryboardShot {
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
  image_path: string | null;
  video_path: string | null;
}

interface StoryboardData {
  shots: StoryboardShot[];
}

interface Props {
  storyboard: StoryboardData | null;
  /** 作品级状态(可选):提供时展示镜头衔接/生成方式/质检结论 */
  projectState?: ProjectState | null;
}

const EMOTION_COLORS: Record<string, string> = {
  neutral: 'default',
  surprise: 'gold',
  humor: 'green',
  tension: 'red',
  calm: 'blue',
};

/** 生成模式 → 用户友好文案 */
const MODE_LABELS: Record<string, string> = {
  t2v: '文生视频',
  i2v: '图生视频',
  r2v: '参考图生成',
  first_last: '首尾帧生成',
};

/** 镜头状态 → 用户友好文案 */
const SHOT_STATUS: Record<string, { label: string; color: string }> = {
  planned: { label: '规划中', color: 'default' },
  generating: { label: '生成中', color: 'processing' },
  generated: { label: '已生成', color: 'blue' },
  verified: { label: '质检通过', color: 'success' },
  failed: { label: '生成失败', color: 'error' },
};

/** 质检维度 → 用户友好文案 */
const QUALITY_DIMENSIONS: Record<string, string> = {
  character_consistency: '人物一致性',
  scene_consistency: '场景一致性',
  action: '动作',
  continuity: '衔接',
  story: '叙事',
};

/** 单镜头的衔接/生成/质检信息(来自作品级状态) */
function ShotContinuityInfo({
  entry,
  decision,
  quality,
  hasPrev,
  hasNext,
}: {
  entry: ShotStateEntry;
  decision?: GenerationDecision;
  quality?: QualityReportItem;
  hasPrev: boolean;
  hasNext: boolean;
}) {
  return (
    <div style={{ marginTop: 6 }}>
      {/* 因果链:上一镜 → 本镜 → 下一镜 */}
      {(hasPrev || hasNext) && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '4px 8px',
            marginBottom: 4,
            background: accents.info.bg,
            borderRadius: 4,
            fontSize: 12,
          }}
        >
          <LinkOutlined />
          <Text type="secondary">叙事链: </Text>
          <Text type={hasPrev ? undefined : 'secondary'}>{hasPrev ? `镜头 ${entry.prev_shot! + 1}` : '开篇'}</Text>
          <ArrowRightOutlined style={{ fontSize: 10, color: '#999' }} />
          <Text strong>镜头 {entry.shot_index + 1}</Text>
          <ArrowRightOutlined style={{ fontSize: 10, color: '#999' }} />
          <Text type={hasNext ? undefined : 'secondary'}>{hasNext ? `镜头 ${entry.next_shot! + 1}` : '结尾'}</Text>
          {entry.causal_note && (
            <Tooltip title={`为什么有这个镜头: ${entry.causal_note}`}>
              <Text type="secondary" style={{ fontSize: 12, marginLeft: 4, cursor: 'help' }}>
                (因果)
              </Text>
            </Tooltip>
          )}
        </div>
      )}
      {/* 衔接字段 */}
      {entry.continuity_in && (
        <Paragraph style={{ margin: '2px 0', fontSize: 12 }}>
          <Text type="secondary">承接上一镜: </Text>{entry.continuity_in}
        </Paragraph>
      )}
      {entry.continuity_out && (
        <Paragraph style={{ margin: '2px 0', fontSize: 12 }}>
          <Text type="secondary">传递给下一镜: </Text>{entry.continuity_out}
        </Paragraph>
      )}
      {/* 情绪变化 */}
      {(entry.emotion_start || entry.emotion_end) && (
        <Paragraph style={{ margin: '2px 0', fontSize: 12 }}>
          <Text type="secondary">情绪变化: </Text>
          {entry.emotion_start || '—'} → {entry.emotion_end || '—'}
        </Paragraph>
      )}
      {/* 生成方式决策 */}
      {(decision || entry.desired_mode) && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center', marginTop: 4 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>生成方式: </Text>
          <Tag color="geekblue">{MODE_LABELS[entry.desired_mode] || entry.desired_mode || '自动'}</Tag>
          {decision?.model && <Tag style={{ fontSize: 11 }}>{decision.model}</Tag>}
          {decision && decision.attempt > 1 && <Tag color="orange">第 {decision.attempt} 次尝试</Tag>}
          {decision?.reason && (
            <Tooltip title={decision.reason}>
              <Text type="secondary" style={{ fontSize: 11, cursor: 'help' }}>(选择原因)</Text>
            </Tooltip>
          )}
        </div>
      )}
      {/* 质检结论 */}
      {quality && (
        <div
          style={{
            marginTop: 4,
            padding: '4px 8px',
            background: quality.passed ? accents.success.bg : accents.error.bg,
            border: `1px solid ${quality.passed ? accents.success.border : accents.error.border}`,
            borderRadius: 4,
          }}
        >
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <SafetyCertificateOutlined style={{ color: quality.passed ? '#52c41a' : '#ff4d4f' }} />
            <Text strong style={{ fontSize: 12 }}>{quality.passed ? '质检通过' : '质检未通过'}</Text>
          </div>
          {quality.checks
            .filter((c) => !c.passed)
            .map((c, i) => (
              <div key={i} style={{ fontSize: 12, marginTop: 2 }}>
                <Text type="secondary">{QUALITY_DIMENSIONS[c.dimension] || c.dimension}: </Text>
                {c.note}
              </div>
            ))}
          {quality.judge_note && (
            <div style={{ fontSize: 12, marginTop: 2 }}>
              <Text type="secondary">评判: </Text>{quality.judge_note}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function StoryboardViewer({ storyboard, projectState }: Props) {
  if (!storyboard || !storyboard.shots?.length) return null;

  const totalDuration = storyboard.shots.reduce((s, sh) => s + (sh.duration || 0), 0);

  // 镜头级作品状态索引:shot_index → entry / 最新路由决策 / 最新质检报告
  const shotEntries = new Map<number, ShotStateEntry>();
  (projectState?.shot_state?.shots ?? []).forEach((s) => shotEntries.set(s.shot_index, s));
  const latestDecisions = new Map<number, GenerationDecision>();
  (projectState?.generation_state?.decisions ?? []).forEach((d) => latestDecisions.set(d.shot_index, d));
  const latestQuality = new Map<number, QualityReportItem>();
  (projectState?.quality_state?.reports ?? []).forEach((r) => latestQuality.set(r.shot_index, r));

  return (
    <Collapse
      size="small"
      style={{ marginTop: 12 }}
      items={[{
        key: 'storyboard',
        label: (
          <span>
            <VideoCameraOutlined style={{ marginRight: 6 }} />
            分镜 · {storyboard.shots.length} 个镜头 · {totalDuration}秒
          </span>
        ),
        children: (
          <Row gutter={[8, 8]}>
            {storyboard.shots.map((shot, i) => {
              const entry = shotEntries.get(i);
              const statusInfo = entry ? SHOT_STATUS[entry.status] : undefined;
              return (
              <Col key={i} span={24}>
                <Card
                  size="small"
                  style={{ background: accents.neutral.bg }}
                  title={
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
                      <Text strong>镜头 {i + 1}</Text>
                      <Tag>{shot.duration}秒</Tag>
                      {shot.shot_type && <Tag color="blue">{shot.shot_type}</Tag>}
                      {shot.camera_movement && <Tag color="cyan">{shot.camera_movement}</Tag>}
                      {shot.emotion && <Tag color={EMOTION_COLORS[shot.emotion] || 'default'}>{shot.emotion}</Tag>}
                      {shot.transition && <Tag>转场: {shot.transition}</Tag>}
                      {statusInfo && <Tag color={statusInfo.color}>{statusInfo.label}</Tag>}
                    </div>
                  }
                >
                  {shot.visual_description && (
                    <Paragraph style={{ margin: '4px 0', fontSize: 13 }}>
                      <Text type="secondary">画面: </Text>{shot.visual_description}
                    </Paragraph>
                  )}
                  {shot.character_action && (
                    <Paragraph style={{ margin: '4px 0', fontSize: 13 }}>
                      <Text type="secondary">动作: </Text>{shot.character_action}
                    </Paragraph>
                  )}
                  {shot.voiceover && (
                    <Paragraph style={{ margin: '4px 0', fontSize: 13 }}>
                      <Text type="secondary">旁白: </Text>{shot.voiceover}
                    </Paragraph>
                  )}
                  {shot.subtitle && (
                    <Paragraph style={{ margin: '4px 0', fontSize: 13 }}>
                      <Text type="secondary">字幕: </Text>{shot.subtitle}
                    </Paragraph>
                  )}
                  {entry && (
                    <ShotContinuityInfo
                      entry={entry}
                      decision={latestDecisions.get(i)}
                      quality={latestQuality.get(i)}
                      hasPrev={entry.prev_shot !== null && entry.prev_shot !== undefined}
                      hasNext={entry.next_shot !== null && entry.next_shot !== undefined}
                    />
                  )}
                  {shot.image_prompt && (
                    <div style={{ marginTop: 4, padding: '4px 8px', background: accents.info.bg, borderRadius: 4 }}>
                      <Text type="secondary" style={{ fontSize: 11 }}>文生图 Prompt: </Text>
                      <Text style={{ fontSize: 11, fontFamily: 'monospace' }}>{shot.image_prompt}</Text>
                    </div>
                  )}
                  {shot.video_prompt && (
                    <div style={{ marginTop: 2, padding: '4px 8px', background: accents.brand.bg, borderRadius: 4 }}>
                      <Text type="secondary" style={{ fontSize: 11 }}>文生视频 Prompt: </Text>
                      <Text style={{ fontSize: 11, fontFamily: 'monospace' }}>{shot.video_prompt}</Text>
                    </div>
                  )}
                  {shot.negative_prompt && (
                    <div style={{ marginTop: 2, padding: '4px 8px', background: accents.error.bg, borderRadius: 4 }}>
                      <Text type="secondary" style={{ fontSize: 11 }}>Negative: </Text>
                      <Text style={{ fontSize: 11, fontFamily: 'monospace' }}>{shot.negative_prompt}</Text>
                    </div>
                  )}
                </Card>
              </Col>
              );
            })}
          </Row>
        ),
      }]}
    />
  );
}
