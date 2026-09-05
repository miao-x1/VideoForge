import { Tag, Typography } from 'antd';
import { directorDark } from '../../theme';

const { Text } = Typography;

export default function ComingSoon({ title, reason }: { title: string; reason: string }) {
  return (
    <div
      style={{
        padding: 16,
        border: `1px dashed ${directorDark.border}`,
        borderRadius: 8,
        background: directorDark.surface,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <Text style={{ color: directorDark.text, fontWeight: 500 }}>{title}</Text>
        <Tag>即将开放</Tag>
      </div>
      <Text style={{ color: directorDark.muted, fontSize: 12 }}>{reason}</Text>
    </div>
  );
}
