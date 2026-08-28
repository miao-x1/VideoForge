import { Card, Empty, Typography } from 'antd';
import type { ResultResp } from '../api/client';

const { Title, Paragraph, Text } = Typography;

interface Props {
  result: ResultResp | null;
}

export default function VideoResult({ result }: Props) {
  if (!result || !result.video_url) {
    return <Empty description="视频尚未生成" />;
  }
  const time = new Date(result.created_at * 1000).toLocaleString('zh-CN');
  return (
    <Card>
      <video
        src={result.video_url}
        controls
        style={{ width: '100%', borderRadius: 8, background: '#000' }}
      />
      <div style={{ marginTop: 16 }}>
        <Title level={4} style={{ marginBottom: 4 }}>
          {result.title || 'AI 生成的视频'}
        </Title>
        <Paragraph type="secondary" style={{ marginBottom: 4 }}>
          通过 Agent Pipeline 自动生成：需求理解 → 脚本 → 分镜 → 素材 → 合成
        </Paragraph>
        <Text type="secondary" style={{ fontSize: 13 }}>生成时间：{time}</Text>
      </div>
    </Card>
  );
}
