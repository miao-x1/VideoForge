import { Select, Switch, Typography, Space, Input, Button } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useCreativeStore } from '../../store/useCreativeStore';

const { Text } = Typography;

const QUALITY_PRIORITIES = [
  { label: '均衡', value: 'balanced' },
  { label: '高质量', value: 'high-quality' },
  { label: '快速', value: 'fast' },
];

export default function AdvancedPanel() {
  const advanced = useCreativeStore((s) => s.spec.advanced);
  const updateSpec = useCreativeStore((s) => s.updateSpec);

  const update = (field: string, value: any) => {
    updateSpec({
      advanced: { ...(advanced ?? { quality_priority: 'balanced', compliance_enabled: true }), [field]: value },
    });
  };

  const customParams = advanced?.custom_params ?? {};
  const updateParam = (key: string, value: string) => {
    update('custom_params', { ...customParams, [key]: value });
  };
  const removeParam = (key: string) => {
    const next = { ...customParams };
    delete next[key];
    update('custom_params', next);
  };
  const addParam = () => {
    const key = `param_${Object.keys(customParams).length + 1}`;
    update('custom_params', { ...customParams, [key]: '' });
  };

  const paramEntries = Object.entries(customParams);

  return (
    <div>
      <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
        高级参数控制视频生成的质量与安全策略
      </Text>

      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        {/* 质量优先级 */}
        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>质量优先级</Text>
          <Select
            value={advanced?.quality_priority ?? 'balanced'}
            onChange={(v) => update('quality_priority', v)}
            style={{ width: '100%', display: 'block', marginTop: 4 }}
            size="small"
            options={QUALITY_PRIORITIES}
          />
        </div>

        {/* 合规预审 */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '8px 0',
          }}
        >
          <div>
            <Text style={{ fontSize: 13 }}>内容安全预审</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              规则 + LLM 语义双层合规预审
            </Text>
          </div>
          <Switch
            checked={advanced?.compliance_enabled ?? true}
            onChange={(v) => update('compliance_enabled', v)}
          />
        </div>

        {/* 自定义参数 */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>自定义参数</Text>
            <Button
              type="primary"
              ghost
              icon={<PlusOutlined />}
              size="small"
              onClick={addParam}
            >
              添加
            </Button>
          </div>
          {paramEntries.length === 0 ? (
            <Text type="secondary" style={{ fontSize: 12, opacity: 0.5 }}>
              暂无自定义参数
            </Text>
          ) : (
            <Space direction="vertical" size={6} style={{ width: '100%' }}>
              {paramEntries.map(([key, value]) => (
                <div key={key} style={{ display: 'flex', gap: 6 }}>
                  <Input
                    value={key}
                    onChange={(e) => {
                      const next = { ...customParams };
                      delete next[key];
                      next[e.target.value] = value as string;
                      update('custom_params', next);
                    }}
                    size="small"
                    style={{ width: 100 }}
                  />
                  <Input
                    value={value as string}
                    onChange={(e) => updateParam(key, e.target.value)}
                    size="small"
                    style={{ flex: 1 }}
                  />
                  <Button
                    danger
                    ghost
                    icon={<DeleteOutlined />}
                    size="small"
                    onClick={() => removeParam(key)}
                  />
                </div>
              ))}
            </Space>
          )}
        </div>
      </Space>
    </div>
  );
}
