import { Button, Input, Select, Space, Typography, Empty } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useCreativeStore } from '../../store/useCreativeStore';
import type { CreativeElement } from '../../api/client';

const { Text } = Typography;

const ELEMENT_TYPES = [
  { label: '角色', value: 'character' },
  { label: '动物', value: 'animal' },
  { label: '车辆', value: 'vehicle' },
  { label: '产品', value: 'product' },
  { label: '建筑', value: 'building' },
  { label: '风景', value: 'landscape' },
  { label: '物品', value: 'object' },
  { label: '生物', value: 'creature' },
  { label: '抽象', value: 'abstract' },
  { label: '自定义', value: 'custom' },
];

export default function CreativeElementsPanel() {
  const elements = useCreativeStore((s) => s.spec.creative_elements ?? []);
  const updateSpec = useCreativeStore((s) => s.updateSpec);

  const update = (index: number, patch: Partial<CreativeElement>) => {
    const next = [...elements];
    next[index] = { ...next[index], ...patch };
    updateSpec({ creative_elements: next });
  };

  const add = () => {
    updateSpec({
      creative_elements: [
        ...elements,
        { type: 'character', name: '', description: '', action: '', sort_order: elements.length },
      ],
    });
  };

  const remove = (index: number) => {
    const next = elements.filter((_, i) => i !== index);
    updateSpec({ creative_elements: next });
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <Text type="secondary">定义视频中的创作元素（角色、物体、场景元素等）</Text>
        <Button type="primary" ghost icon={<PlusOutlined />} size="small" onClick={add}>
          添加元素
        </Button>
      </div>
      {elements.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无创作元素" />
      ) : (
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          {elements.map((el, i) => (
            <div
              key={i}
              style={{
                border: '1px solid #f0f0f0',
                borderRadius: 8,
                padding: 12,
              }}
            >
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <Select
                  value={el.type}
                  onChange={(v) => update(i, { type: v })}
                  style={{ width: 100 }}
                  options={ELEMENT_TYPES}
                  size="small"
                />
                <Input
                  value={el.name}
                  onChange={(e) => update(i, { name: e.target.value })}
                  placeholder="名称"
                  size="small"
                  style={{ flex: 1 }}
                />
                <Button
                  danger
                  ghost
                  icon={<DeleteOutlined />}
                  size="small"
                  onClick={() => remove(i)}
                />
              </div>
              <Input.TextArea
                value={el.description}
                onChange={(e) => update(i, { description: e.target.value })}
                placeholder="描述外观、身份等"
                rows={2}
                size="small"
              />
              <Input
                value={el.action ?? ''}
                onChange={(e) => update(i, { action: e.target.value })}
                placeholder="动作/行为（可选）"
                size="small"
                style={{ marginTop: 8 }}
              />
            </div>
          ))}
        </Space>
      )}
    </div>
  );
}
