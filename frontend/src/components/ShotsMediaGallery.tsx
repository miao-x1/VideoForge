import { Card, Col, Empty, Row, Tag, Typography } from 'antd';
import { LockFilled } from '@ant-design/icons';
import { mediaUrl as withAccessToken, type InputSourceItem } from '../api/client';

const { Text, Paragraph } = Typography;

export interface GalleryShot {
  shot_id?: number | string;
  visual_description?: string;
  voiceover?: string;
  duration?: number;
  locked?: boolean;
  image_path?: string | null;
  video_path?: string | null;
  audio_path?: string | null;
}

/** 本地素材路径 → 静态访问 URL */
export function mediaUrl(
  path: string | null | undefined,
  kind: 'images' | 'videos' | 'audio',
): string | null {
  if (!path) return null;
  const name = path.split(/[\\/]/).pop();
  return name ? withAccessToken(`/storage/${kind}/${name}`) : null;
}

interface Props {
  shots: GalleryShot[];
  kind: 'image' | 'video' | 'audio';
}

const KIND_META = {
  image: { title: '镜头图片', urlKind: 'images' as const },
  video: { title: '镜头视频片段', urlKind: 'videos' as const },
  audio: { title: '镜头音频', urlKind: 'audio' as const },
};

/**
 * 镜头素材画廊:按节点类型(图片/视频/音频)展示每个镜头已生成的素材。
 * 数据来自任务真实状态,未生成的镜头显示占位。
 */
export default function ShotsMediaGallery({ shots, kind }: Props) {
  if (!shots.length) {
    return <Empty description="暂无分镜数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  const meta = KIND_META[kind];

  return (
    <div>
      <Paragraph type="secondary" style={{ marginBottom: 12 }}>
        {meta.title} · 共 {shots.length} 个镜头
      </Paragraph>
      <Row gutter={[12, 12]}>
        {shots.map((shot, i) => {
          const url = mediaUrl(
            kind === 'image' ? shot.image_path : kind === 'video' ? shot.video_path : shot.audio_path,
            meta.urlKind,
          );
          return (
            <Col key={i} xs={24} sm={12} md={8}>
              <Card size="small" style={{ height: '100%' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                  <Text strong style={{ fontSize: 13 }}>镜头 {shot.shot_id ?? i + 1}</Text>
                  {shot.duration != null && <Tag style={{ fontSize: 11 }}>{shot.duration}s</Tag>}
                  {shot.locked && <LockFilled style={{ color: '#faad14', fontSize: 12 }} />}
                </div>
                {url ? (
                  kind === 'image' ? (
                    <img
                      src={url}
                      alt={`镜头 ${i + 1} 关键帧`}
                      style={{ width: '100%', borderRadius: 6, display: 'block' }}
                    />
                  ) : kind === 'video' ? (
                    <video src={url} controls style={{ width: '100%', borderRadius: 6, display: 'block' }} />
                  ) : (
                    <audio src={url} controls style={{ width: '100%', display: 'block', height: 36 }} />
                  )
                ) : (
                  <div
                    style={{
                      padding: '24px 0',
                      textAlign: 'center',
                      color: 'rgba(0,0,0,0.25)',
                      fontSize: 12,
                      background: '#fafafa',
                      borderRadius: 6,
                    }}
                  >
                    未生成
                  </div>
                )}
                {kind === 'audio' && shot.voiceover && (
                  <Paragraph
                    style={{ marginTop: 8, marginBottom: 0, fontSize: 12 }}
                    ellipsis={{ rows: 2, expandable: true, symbol: '展开' }}
                  >
                    {shot.voiceover}
                  </Paragraph>
                )}
                {kind === 'image' && shot.visual_description && (
                  <Paragraph
                    type="secondary"
                    style={{ marginTop: 8, marginBottom: 0, fontSize: 12 }}
                    ellipsis={{ rows: 2, expandable: true, symbol: '展开' }}
                  >
                    {shot.visual_description}
                  </Paragraph>
                )}
              </Card>
            </Col>
          );
        })}
      </Row>
    </div>
  );
}

/** 素材库节点:创作输入的多模态参考素材 */
export function AssetsPanel({ sources }: { sources: InputSourceItem[] }) {
  if (!sources.length) {
    return <Empty description="本次创作未添加参考素材" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  const TYPE_LABELS: Record<string, { label: string; color: string }> = {
    text: { label: '文本', color: 'default' },
    image: { label: '图片', color: 'blue' },
    video: { label: '视频', color: 'purple' },
    url: { label: '链接', color: 'cyan' },
  };
  return (
    <div>
      <Paragraph type="secondary" style={{ marginBottom: 12 }}>
        参考素材 · 共 {sources.length} 项(已在 AI 理解与 Prompt 编译中使用)
      </Paragraph>
      <Row gutter={[12, 12]}>
        {sources.map((s, i) => {
          const meta = TYPE_LABELS[s.type] ?? { label: s.type, color: 'default' };
          return (
            <Col key={i} xs={24} md={12}>
              <Card size="small">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Tag color={meta.color}>{meta.label}</Tag>
                  {s.purpose && <Text type="secondary" style={{ fontSize: 12 }}>{s.purpose}</Text>}
                </div>
                <Paragraph
                  style={{ marginTop: 8, marginBottom: 0, fontSize: 13 }}
                  ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
                >
                  {s.type === 'image' || s.type === 'video'
                    ? s.content.split(/[\\/]/).pop() || s.content
                    : s.content}
                </Paragraph>
              </Card>
            </Col>
          );
        })}
      </Row>
    </div>
  );
}
