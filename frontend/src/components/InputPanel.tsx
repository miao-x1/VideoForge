import { useState } from 'react';
import { Button, Input, InputNumber, Select, Space, Switch, Typography } from 'antd';

const { TextArea } = Input;
const { Title, Text } = Typography;

export interface InputPanelValue {
  user_input: string;
  duration: number;
  style: string;
  aspect_ratio: string;
  compliance_enabled: boolean;
}

interface Props {
  loading: boolean;
  onSubmit: (value: InputPanelValue) => void;
}

const DEFAULT_INPUT = '假如古代人有手机，他第一次刷短视频会发生什么？';
const STYLES = [
  { label: '轻松搞笑', value: '轻松搞笑' },
  { label: '古装喜剧', value: '古装喜剧' },
  { label: '古风', value: '古风' },
  { label: '现代', value: '现代' },
  { label: '动漫', value: '动漫' },
  { label: '纪录片', value: '纪录片' },
  { label: '悬疑', value: '悬疑' },
];
const RATIOS = [{ label: '9:16 竖屏', value: '9:16' }];

export default function InputPanel({ loading, onSubmit }: Props) {
  const [input, setInput] = useState(DEFAULT_INPUT);
  const [duration, setDuration] = useState(30);
  const [style, setStyle] = useState('轻松搞笑');
  const [aspectRatio, setAspectRatio] = useState('9:16');
  const [complianceEnabled, setComplianceEnabled] = useState(true);

  return (
    <div>
      <Title level={4}>输入你的视频创意</Title>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          rows={4}
          placeholder="例如：假如古代人有手机，他第一次刷短视频会发生什么？"
        />
        <div>
          <Text type="secondary">视频时长(秒)</Text>
          <InputNumber
            min={5}
            max={120}
            value={duration}
            onChange={(v) => setDuration(Number(v) || 30)}
            style={{ width: 120, display: 'block', marginTop: 4 }}
          />
        </div>
        <div>
          <Text type="secondary">视频风格</Text>
          <Select
            value={style}
            onChange={setStyle}
            style={{ width: '100%', display: 'block', marginTop: 4 }}
            options={STYLES}
          />
        </div>
        <div>
          <Text type="secondary">视频比例</Text>
          <Select
            value={aspectRatio}
            onChange={setAspectRatio}
            style={{ width: '100%', display: 'block', marginTop: 4 }}
            options={RATIOS}
          />
        </div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '8px 0',
          }}
        >
          <div>
            <Text>内容安全检查</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              规则 + LLM 语义双层合规预审
            </Text>
          </div>
          <Switch checked={complianceEnabled} onChange={setComplianceEnabled} />
        </div>
        <Button
          type="primary"
          size="large"
          loading={loading}
          onClick={() =>
            onSubmit({
              user_input: input,
              duration,
              style,
              aspect_ratio: aspectRatio,
              compliance_enabled: complianceEnabled,
            })
          }
          block
        >
          开始生成
        </Button>
      </Space>
    </div>
  );
}
