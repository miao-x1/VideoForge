import { Input, Form, Typography, Select } from 'antd';
import { useCreativeStore } from '../../store/useCreativeStore';

const { Text } = Typography;

const BGM_MODES = [
  { label: '自动', value: 'auto' },
  { label: '指定', value: 'custom' },
  { label: '无', value: 'none' },
];

const VOICE_STYLES = [
  { label: '男声-沉稳', value: 'male-calm' },
  { label: '女声-温柔', value: 'female-gentle' },
  { label: '男声-活力', value: 'male-energetic' },
  { label: '女声-清脆', value: 'female-crisp' },
];

export default function AudioPanel() {
  const audio = useCreativeStore((s) => s.spec.audio);
  const updateSpec = useCreativeStore((s) => s.updateSpec);

  const update = (field: string, value: string) => {
    updateSpec({
      audio: { ...(audio ?? {}), [field]: value },
    });
  };

  return (
    <Form layout="vertical" size="small">
      <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
        背景音乐、音效与配音设置
      </Text>
      <Form.Item label="背景音乐">
        <Select
          value={audio?.bgm_mode ?? 'auto'}
          onChange={(v) => update('bgm_mode', v)}
          options={BGM_MODES}
        />
      </Form.Item>
      <Form.Item label="音效描述">
        <Input.TextArea
          value={audio?.sfx_description ?? ''}
          onChange={(e) => update('sfx_description', e.target.value)}
          placeholder="如：风声、脚步声、欢笑声"
          rows={2}
        />
      </Form.Item>
      <Form.Item label="台词">
        <Input.TextArea
          value={audio?.dialogue_text ?? ''}
          onChange={(e) => update('dialogue_text', e.target.value)}
          placeholder="角色台词或旁白文本"
          rows={3}
        />
      </Form.Item>
      <Form.Item label="配音风格">
        <Select
          value={audio?.voice_style ?? ''}
          onChange={(v) => update('voice_style', v)}
          options={[{ label: '自动', value: '' }, ...VOICE_STYLES]}
          allowClear
        />
      </Form.Item>
    </Form>
  );
}
