import { Input, Form, Typography, Select } from 'antd';
import { useCreativeStore } from '../../store/useCreativeStore';

const { Text } = Typography;

const LIGHTING_TYPE_OPTIONS = [
  { label: '自然光', value: 'natural' },
  { label: '影棚灯光', value: 'studio' },
  { label: '霓虹灯', value: 'neon' },
  { label: '烛光', value: 'candlelight' },
  { label: '混合光源', value: 'mixed' },
];

const COLOR_TEMPERATURE_OPTIONS = [
  { label: '不指定', value: '' },
  { label: '暖色 3200K', value: 'warm 3200K' },
  { label: '中性 4500K', value: 'neutral 4500K' },
  { label: '冷色 5600K', value: 'cool 5600K' },
  { label: '自定义', value: '__custom__' },
];

const COLOR_GRADING_OPTIONS = [
  { label: '不指定', value: '' },
  { label: '电影感青橙调', value: 'cinematic teal-orange' },
  { label: '去饱和低饱和', value: 'desaturated' },
  { label: '鲜艳高饱和', value: 'vivid' },
  { label: '复古褪色', value: 'vintage faded' },
  { label: '黑白', value: 'black and white' },
  { label: '自定义', value: '__custom__' },
];

export default function EnvironmentPanel() {
  const env = useCreativeStore((s) => s.spec.environment);
  const updateSpec = useCreativeStore((s) => s.updateSpec);

  const update = (field: string, value: string) => {
    updateSpec({
      environment: { ...(env ?? {}), [field]: value },
    });
  };

  const colorTempValue = env?.color_temperature ?? '';
  const colorGradeValue = env?.color_grading ?? '';
  const isCustomTemp = colorTempValue && !COLOR_TEMPERATURE_OPTIONS.some((o) => o.value === colorTempValue);
  const isCustomGrade = colorGradeValue && !COLOR_GRADING_OPTIONS.some((o) => o.value === colorGradeValue);

  return (
    <Form layout="vertical" size="small">
      <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
        定义视频的场景与环境,光线与色彩参数将真实影响生成画面
      </Text>
      <Form.Item label="地点">
        <Input
          value={env?.location ?? ''}
          onChange={(e) => update('location', e.target.value)}
          placeholder="如：屋顶、街道、室内"
        />
      </Form.Item>
      <Form.Item label="时间">
        <Input
          value={env?.time_of_day ?? ''}
          onChange={(e) => update('time_of_day', e.target.value)}
          placeholder="如：夜晚、黄昏、清晨"
        />
      </Form.Item>
      <Form.Item label="天气">
        <Input
          value={env?.weather ?? ''}
          onChange={(e) => update('weather', e.target.value)}
          placeholder="如：晴朗、下雨、雪"
        />
      </Form.Item>
      <Form.Item label="光照描述">
        <Input
          value={env?.lighting ?? ''}
          onChange={(e) => update('lighting', e.target.value)}
          placeholder="如：月光、逆光、暖色光"
        />
      </Form.Item>
      <Form.Item label="光源类型">
        <Select
          value={env?.lighting_type || undefined}
          onChange={(v) => update('lighting_type', v ?? '')}
          options={LIGHTING_TYPE_OPTIONS}
          placeholder="选择光源类型"
          allowClear
        />
      </Form.Item>
      <Form.Item label="氛围">
        <Input
          value={env?.atmosphere ?? ''}
          onChange={(e) => update('atmosphere', e.target.value)}
          placeholder="如：神秘、温馨、紧张"
        />
      </Form.Item>
      <Form.Item label="色彩方案">
        <Input
          value={env?.color_palette ?? ''}
          onChange={(e) => update('color_palette', e.target.value)}
          placeholder="如：暖橙与深蓝、柔和粉调"
        />
      </Form.Item>
      <Form.Item label="色温">
        <Select
          value={isCustomTemp ? '__custom__' : colorTempValue}
          onChange={(v) => update('color_temperature', v === '__custom__' ? '' : v)}
          options={COLOR_TEMPERATURE_OPTIONS}
          placeholder="选择色温"
          allowClear
        />
        {isCustomTemp && (
          <Input
            value={colorTempValue}
            onChange={(e) => update('color_temperature', e.target.value)}
            placeholder="自定义色温,如 warm 3000K"
            style={{ marginTop: 4 }}
          />
        )}
      </Form.Item>
      <Form.Item label="调色风格">
        <Select
          value={isCustomGrade ? '__custom__' : colorGradeValue}
          onChange={(v) => update('color_grading', v === '__custom__' ? '' : v)}
          options={COLOR_GRADING_OPTIONS}
          placeholder="选择调色风格"
          allowClear
        />
        {isCustomGrade && (
          <Input
            value={colorGradeValue}
            onChange={(e) => update('color_grading', e.target.value)}
            placeholder="自定义调色,如 warm vintage"
            style={{ marginTop: 4 }}
          />
        )}
      </Form.Item>
    </Form>
  );
}
