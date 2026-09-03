import { Input, Form, Typography } from 'antd';
import { useCreativeStore } from '../../store/useCreativeStore';

const { Text } = Typography;

export default function CameraPanel() {
  const camera = useCreativeStore((s) => s.spec.camera);
  const updateSpec = useCreativeStore((s) => s.updateSpec);

  const update = (field: string, value: string) => {
    updateSpec({
      camera: { ...(camera ?? {}), [field]: value },
    });
  };

  return (
    <Form layout="vertical" size="small">
      <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
        镜头景别、角度、运动与节奏
      </Text>
      <Form.Item label="景别">
        <Input
          value={camera?.shot_type ?? ''}
          onChange={(e) => update('shot_type', e.target.value)}
          placeholder="如：close-up / medium / wide"
        />
      </Form.Item>
      <Form.Item label="角度">
        <Input
          value={camera?.angle ?? ''}
          onChange={(e) => update('angle', e.target.value)}
          placeholder="如：eye-level / high / low"
        />
      </Form.Item>
      <Form.Item label="运动">
        <Input
          value={camera?.movement ?? ''}
          onChange={(e) => update('movement', e.target.value)}
          placeholder="如：static / push-in / pan"
        />
      </Form.Item>
      <Form.Item label="节奏">
        <Input
          value={camera?.rhythm ?? ''}
          onChange={(e) => update('rhythm', e.target.value)}
          placeholder="如：slow / medium / fast"
        />
      </Form.Item>
    </Form>
  );
}
