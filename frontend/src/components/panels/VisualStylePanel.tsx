import { Input, Typography, Tag } from 'antd';
import { useCreativeStore } from '../../store/useCreativeStore';
import type { StyleItem } from '../../api/client';

const { Text } = Typography;

const STYLE_CATEGORIES: { category: string; items: { name: string; value: string }[] }[] = [
  {
    category: '电影感',
    items: [
      { name: '电影感', value: 'cinematic' },
      { name: '纪录片', value: 'documentary' },
      { name: '胶片质感', value: 'film-grain' },
    ],
  },
  {
    category: '艺术风格',
    items: [
      { name: '动漫', value: 'anime' },
      { name: '水彩', value: 'watercolor' },
      { name: '油画', value: 'oil-painting' },
      { name: '3D 渲染', value: '3d-render' },
    ],
  },
  {
    category: '写实',
    items: [
      { name: '写实', value: 'realistic' },
      { name: '超写实', value: 'hyperrealistic' },
      { name: '微距', value: 'macro' },
    ],
  },
  {
    category: '色调',
    items: [
      { name: '暖色调', value: 'warm-tone' },
      { name: '冷色调', value: 'cool-tone' },
      { name: '高对比', value: 'high-contrast' },
      { name: '低饱和', value: 'desaturated' },
    ],
  },
  {
    category: '氛围',
    items: [
      { name: '梦幻', value: 'dreamy' },
      { name: '暗黑', value: 'dark' },
      { name: '明亮', value: 'bright' },
      { name: '复古', value: 'vintage' },
    ],
  },
];

export default function VisualStylePanel() {
  const visualStyle = useCreativeStore((s) => s.spec.visual_style ?? []);
  const customStyle = useCreativeStore((s) => s.spec.custom_style ?? '');
  const updateSpec = useCreativeStore((s) => s.updateSpec);

  const selectedValues = new Set(visualStyle.map((s) => s.name));

  const toggle = (category: string, name: string) => {
    const exists = selectedValues.has(name);
    if (exists) {
      updateSpec({
        visual_style: visualStyle.filter((s) => s.name !== name),
      });
    } else {
      const next: StyleItem[] = [...visualStyle, { category, name }];
      updateSpec({ visual_style: next });
    }
  };

  return (
    <div>
      <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
        选择视觉风格（可多选组合），或输入自定义风格
      </Text>

      {STYLE_CATEGORIES.map((cat) => (
        <div key={cat.category} style={{ marginBottom: 12 }}>
          <Text strong style={{ fontSize: 12, marginRight: 8 }}>
            {cat.category}
          </Text>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
            {cat.items.map((item) => {
              const checked = selectedValues.has(item.name);
              return (
                <Tag.CheckableTag
                  key={item.value}
                  checked={checked}
                  onChange={() => toggle(cat.category, item.name)}
                >
                  {item.name}
                </Tag.CheckableTag>
              );
            })}
          </div>
        </div>
      ))}

      <div style={{ marginTop: 16 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          自定义风格描述
        </Text>
        <Input
          value={customStyle}
          onChange={(e) => updateSpec({ custom_style: e.target.value })}
          placeholder="如：赛博朋克 + 日系动漫混合"
          size="small"
          style={{ marginTop: 4 }}
        />
      </div>
    </div>
  );
}
