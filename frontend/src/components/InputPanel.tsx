import { useState } from 'react';
import { Button, Input, InputNumber, Select, Space, Typography } from 'antd';

const { TextArea } = Input;
const { Title } = Typography;

export interface InputPanelValue {
  user_input: string;
  duration: number;
  style: string;
}

interface Props {
  loading: boolean;
  onSubmit: (value: InputPanelValue) => void;
}

const DEFAULT_INPUT = '假如古代人有手机，做一个30秒轻松搞笑的短视频。';
const STYLES = [
  { label: '轻松搞笑', value: '轻松搞笑' },
  { label: '古装喜剧', value: '古装喜剧' },
  { label: '纪录片', value: '纪录片' },
  { label: '悬疑', value: '悬疑' },
];

export default function InputPanel({ loading, onSubmit }: Props) {
  const [input, setInput] = useState(DEFAULT_INPUT);
  const [duration, setDuration] = useState(30);
  const [style, setStyle] = useState('轻松搞笑');

  return (
    <div>
      <Title level={4}>输入你的视频创意</Title>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          rows={4}
          placeholder="例如：假如古代人有手机，做一个30秒轻松搞笑的短视频。"
        />
        <Space size="large">
          <div>
            <Typography.Text type="secondary">视频时长(秒)</Typography.Text>
            <InputNumber
              min={5}
              max={120}
              value={duration}
              onChange={(v) => setDuration(Number(v) || 30)}
              style={{ width: 120, display: 'block', marginTop: 4 }}
            />
          </div>
          <div>
            <Typography.Text type="secondary">视频风格</Typography.Text>
            <Select
              value={style}
              onChange={setStyle}
              style={{ width: 180, display: 'block', marginTop: 4 }}
              options={STYLES}
            />
          </div>
        </Space>
        <Button
          type="primary"
          size="large"
          loading={loading}
          onClick={() => onSubmit({ user_input: input, duration, style })}
          block
        >
          开始生成
        </Button>
      </Space>
    </div>
  );
}
