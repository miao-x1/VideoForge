import { Input, Form, Typography } from 'antd';
import { useCreativeStore } from '../../store/useCreativeStore';

const { Text } = Typography;

export default function MotionPanel() {
  const motion = useCreativeStore((s) => s.spec.motion);
  const updateSpec = useCreativeStore((s) => s.updateSpec);

  const update = (field: string, value: string) => {
    updateSpec({
      motion: { ...(motion ?? {}), [field]: value },
    });
  };

  return (
    <Form layout="vertical" size="small">
      <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
        分别控制主体运动、镜头运动和环境运动
      </Text>
      <Form.Item label="主体运动">
        <Input.TextArea
          value={motion?.subject_motion ?? ''}
          onChange={(e) => update('subject_motion', e.target.value)}
          placeholder="如：奔跑、转身、微笑"
          rows={2}
        />
      </Form.Item>
      <Form.Item label="镜头运动">
        <Input.TextArea
          value={motion?.camera_motion ?? ''}
          onChange={(e) => update('camera_motion', e.target.value)}
          placeholder="如：缓慢推进、快速摇摄、航拍"
          rows={2}
        />
      </Form.Item>
      <Form.Item label="环境运动">
        <Input.TextArea
          value={motion?.environment_motion ?? ''}
          onChange={(e) => update('environment_motion', e.target.value)}
          placeholder="如：风吹树叶、水流、云移动"
          rows={2}
        />
      </Form.Item>
    </Form>
  );
}
