import { Input, Form, Typography } from 'antd';
import { useCreativeStore } from '../../store/useCreativeStore';

const { Text } = Typography;

export default function NarrativePanel() {
  const narrative = useCreativeStore((s) => s.spec.narrative);
  const updateSpec = useCreativeStore((s) => s.updateSpec);

  const update = (field: string, value: string) => {
    updateSpec({
      narrative: { ...(narrative ?? {}), [field]: value },
    });
  };

  return (
    <Form layout="vertical" size="small">
      <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
        定义视频的叙事结构与主题
      </Text>
      <Form.Item label="叙事结构">
        <Input
          value={narrative?.structure ?? ''}
          onChange={(e) => update('structure', e.target.value)}
          placeholder="如：linear / non-linear / montage"
        />
      </Form.Item>
      <Form.Item label="主题">
        <Input
          value={narrative?.theme ?? ''}
          onChange={(e) => update('theme', e.target.value)}
          placeholder="如：成长、冒险、日常"
        />
      </Form.Item>
      <Form.Item label="情绪基调">
        <Input
          value={narrative?.mood ?? ''}
          onChange={(e) => update('mood', e.target.value)}
          placeholder="如：欢快、忧伤、震撼"
        />
      </Form.Item>
    </Form>
  );
}
