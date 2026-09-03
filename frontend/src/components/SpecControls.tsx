import { useState } from 'react';
import type { CSSProperties } from 'react';
import { Button, Collapse, Empty, Input, Select, Tag, Typography, message } from 'antd';
import type { CollapseProps } from 'antd';
import {
  AppstoreOutlined,
  BgColorsOutlined,
  CaretRightOutlined,
  DeleteOutlined,
  PlusOutlined,
  SlidersOutlined,
  SoundOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons';
import type {
  AudioControl,
  CameraControl,
  CreativeElement,
  Environment,
  MotionControl,
  Narrative,
  StyleItem,
  VideoSpecification,
} from '../api/client';
import { brand, colors, radius } from '../theme';

const { TextArea } = Input;
const { Text } = Typography;

/** 预置风格分类:点击 chip 即加入/移出 visual_style(category=分类名,name=选项名) */
const STYLE_GROUPS: { category: string; options: string[] }[] = [
  {
    category: '画面风格',
    options: ['三维动画', '二维动画', '真人实拍', '水墨国风', '赛博朋克', '吉卜力风', '像素风', '剪纸风'],
  },
  { category: '摄影质感', options: ['电影感', '胶片质感', '浅景深', '广角冲击', '微距特写'] },
  { category: '色调', options: ['暖色调', '冷色调', '高饱和', '低饱和莫兰迪', '黑白'] },
];

/** 创作元素类型(type 字段存中文类型名) */
const ELEMENT_TYPES = ['角色', '场景', '道具', '服装', '特效', '生物', '载具', '标志物'];

/** 字符串选项转 Select options */
const toOptions = (list: string[]) => list.map((s) => ({ label: s, value: s }));

const SHOT_TYPES = ['远景', '全景', '中景', '近景', '特写'];
const CAMERA_ANGLES = ['平视', '俯拍', '仰拍', '鸟瞰'];
const CAMERA_MOVEMENTS = ['固定', '推', '拉', '摇', '移', '跟', '环绕', '手持'];
const TIME_OF_DAY_OPTIONS = ['清晨', '白天', '黄昏', '夜晚'];
const BGM_MODE_OPTIONS = ['自动配乐', '无配乐', '指定音频'];
const VOICE_STYLE_OPTIONS = ['沉稳男声', '温柔女声', '活泼少女', '沧桑大叔', '无旁白'];
const MOOD_OPTIONS = ['热血', '治愈', '悬疑', '搞笑', '伤感', '史诗'];

interface Props {
  value: VideoSpecification;
  onChange: (v: VideoSpecification) => void;
}

/** 正在添加的创作元素草稿,点击"添加"后才写入 value.creative_elements */
interface ElementDraft {
  type: string;
  name: string;
  description: string;
  action: string;
}

const sectionLabelStyle: CSSProperties = {
  fontSize: 12,
  color: colors.textMuted,
  display: 'block',
  margin: '12px 0 8px',
};

const fieldRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '12px 16px',
};

const elementCardStyle: CSSProperties = {
  background: colors.bg,
  border: `1px solid ${colors.border}`,
  borderRadius: radius.item,
  padding: '8px 12px',
};

/**
 * 专业创作控制面板:提交创意前补充结构化创作规格(VideoSpecification)。
 * 视觉风格 / 创作元素 / 镜头场景 / 音频叙事四个维度全部受控编辑,
 * 经 onChange 回传新对象(不直接 mutate),后端会全量消费进 Prompt 编译。
 */
export default function SpecControls({ value, onChange }: Props): JSX.Element {
  const [elementDraft, setElementDraft] = useState<ElementDraft>({
    type: ELEMENT_TYPES[0],
    name: '',
    description: '',
    action: '',
  });

  const visualStyle = value.visual_style ?? [];
  const elements = value.creative_elements ?? [];

  // ---- 不可变更新辅助:始终基于当前 value 展开生成新对象 ----
  const patchSpec = (patch: Partial<VideoSpecification>) => onChange({ ...value, ...patch });
  const patchCamera = (patch: Partial<CameraControl>) => patchSpec({ camera: { ...value.camera, ...patch } });
  const patchEnvironment = (patch: Partial<Environment>) =>
    patchSpec({ environment: { ...value.environment, ...patch } });
  const patchAudio = (patch: Partial<AudioControl>) => patchSpec({ audio: { ...value.audio, ...patch } });
  const patchNarrative = (patch: Partial<Narrative>) => patchSpec({ narrative: { ...value.narrative, ...patch } });
  const patchMotion = (patch: Partial<MotionControl>) => patchSpec({ motion: { ...value.motion, ...patch } });

  const setStyleList = (list: StyleItem[]) => patchSpec({ visual_style: list.length > 0 ? list : undefined });

  const sameStyle = (item: StyleItem, category: string, name: string) =>
    item.category === category && item.name === name;

  const toggleStyle = (category: string, name: string, checked: boolean) => {
    const next = checked
      ? [...visualStyle, { category, name }]
      : visualStyle.filter((s) => !sameStyle(s, category, name));
    setStyleList(next);
  };

  const removeStyleAt = (index: number) => setStyleList(visualStyle.filter((_, i) => i !== index));

  const handleAddElement = () => {
    const name = elementDraft.name.trim();
    if (!name) {
      message.warning('请先填写元素名称');
      return;
    }
    const element: CreativeElement = {
      type: elementDraft.type,
      name,
      description: elementDraft.description.trim(),
      action: elementDraft.action.trim() || undefined,
    };
    patchSpec({ creative_elements: [...elements, element] });
    setElementDraft((d) => ({ ...d, name: '', description: '', action: '' }));
  };

  const removeElementAt = (index: number) => {
    const next = elements.filter((_, i) => i !== index);
    patchSpec({ creative_elements: next.length > 0 ? next : undefined });
  };

  /** 统一渲染"小标签 + 控件"的表单字段 */
  const renderField = (label: string, node: JSX.Element) => (
    <div style={{ flex: '1 1 180px', maxWidth: 300 }}>
      <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
        {label}
      </Text>
      {node}
    </div>
  );

  const countTag = (count: number) =>
    count > 0 ? (
      <Tag style={{ marginInlineEnd: 0, borderRadius: radius.item }}>{count}</Tag>
    ) : null;

  const collapseItems: CollapseProps['items'] = [
    {
      key: 'visual_style',
      label: (
        <span>
          <BgColorsOutlined style={{ marginRight: 6, color: brand.primary }} />
          视觉风格
        </span>
      ),
      extra: countTag(visualStyle.length),
      children: (
        <div>
          {STYLE_GROUPS.map((group) => (
            <div key={group.category} style={{ marginBottom: 12 }}>
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
                {group.category}
              </Text>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {group.options.map((name) => {
                  const checked = visualStyle.some((s) => sameStyle(s, group.category, name));
                  return (
                    <Tag.CheckableTag
                      key={name}
                      checked={checked}
                      onChange={(checkedNext) => toggleStyle(group.category, name, checkedNext)}
                      style={checked ? { background: brand.tint, color: brand.gradientEnd, fontWeight: 500 } : undefined}
                    >
                      {name}
                    </Tag.CheckableTag>
                  );
                })}
              </div>
            </div>
          ))}

          {visualStyle.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
                已选风格
              </Text>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {visualStyle.map((item, idx) => (
                  <Tag
                    key={`${item.category ?? ''}-${item.name}-${idx}`}
                    closable
                    onClose={() => removeStyleAt(idx)}
                    style={{ borderRadius: radius.item }}
                  >
                    {item.category ? `${item.category}·${item.name}` : item.name}
                  </Tag>
                ))}
              </div>
            </div>
          )}

          <Input
            value={value.custom_style ?? ''}
            onChange={(e) => patchSpec({ custom_style: e.target.value || undefined })}
            placeholder="补充自定义风格描述"
            maxLength={200}
          />
        </div>
      ),
    },
    {
      key: 'creative_elements',
      label: (
        <span>
          <AppstoreOutlined style={{ marginRight: 6, color: brand.primary }} />
          创作元素
        </span>
      ),
      extra: countTag(elements.length),
      children: (
        <div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <Select
              value={elementDraft.type}
              onChange={(t) => setElementDraft((d) => ({ ...d, type: t }))}
              options={toOptions(ELEMENT_TYPES)}
              style={{ width: 110 }}
            />
            <Input
              value={elementDraft.name}
              onChange={(e) => setElementDraft((d) => ({ ...d, name: e.target.value }))}
              placeholder="元素名称(必填),如:主角小雨"
              maxLength={50}
              style={{ flex: 1, minWidth: 160 }}
            />
          </div>
          <TextArea
            value={elementDraft.description}
            onChange={(e) => setElementDraft((d) => ({ ...d, description: e.target.value }))}
            placeholder="外观/特征描述,如:16岁少女,蓝色校服,长发及腰"
            rows={2}
            maxLength={500}
            style={{ marginTop: 8 }}
          />
          <div style={{ display: 'flex', gap: 8, marginTop: 8, alignItems: 'center' }}>
            <Input
              value={elementDraft.action}
              onChange={(e) => setElementDraft((d) => ({ ...d, action: e.target.value }))}
              placeholder="动作/行为(可选),如:撑伞走过雨巷"
              maxLength={100}
              style={{ flex: 1 }}
            />
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddElement}>
              添加
            </Button>
          </div>

          {elements.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="暂无创作元素,可在上方添加角色/场景/道具等"
              style={{ margin: '12px 0' }}
            />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
              {elements.map((el, idx) => (
                <div key={`${el.type}-${el.name}-${idx}`} style={elementCardStyle}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Tag color="geekblue" style={{ marginInlineEnd: 0, borderRadius: radius.item }}>
                      {el.type}
                    </Tag>
                    <Text strong>{el.name}</Text>
                    {el.action && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        动作: {el.action}
                      </Text>
                    )}
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => removeElementAt(idx)}
                      style={{ marginLeft: 'auto' }}
                    />
                  </div>
                  {el.description && (
                    <Text
                      type="secondary"
                      style={{ fontSize: 12, display: 'block', marginTop: 4, whiteSpace: 'pre-wrap' }}
                    >
                      {el.description}
                    </Text>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'camera_scene',
      label: (
        <span>
          <VideoCameraOutlined style={{ marginRight: 6, color: brand.primary }} />
          镜头与场景
        </span>
      ),
      children: (
        <div>
          <Text type="secondary" style={sectionLabelStyle}>
            镜头
          </Text>
          <div style={fieldRowStyle}>
            {renderField(
              '景别',
              <Select
                allowClear
                value={value.camera?.shot_type}
                onChange={(v) => patchCamera({ shot_type: v })}
                options={toOptions(SHOT_TYPES)}
                placeholder="请选择"
              />,
            )}
            {renderField(
              '机位',
              <Select
                allowClear
                value={value.camera?.angle}
                onChange={(v) => patchCamera({ angle: v })}
                options={toOptions(CAMERA_ANGLES)}
                placeholder="请选择"
              />,
            )}
            {renderField(
              '运镜',
              <Select
                allowClear
                value={value.camera?.movement}
                onChange={(v) => patchCamera({ movement: v })}
                options={toOptions(CAMERA_MOVEMENTS)}
                placeholder="请选择"
              />,
            )}
            {renderField(
              '节奏',
              <Input
                value={value.camera?.rhythm ?? ''}
                onChange={(e) => patchCamera({ rhythm: e.target.value || undefined })}
                placeholder="快切/慢摇"
                maxLength={50}
              />,
            )}
          </div>

          <Text type="secondary" style={sectionLabelStyle}>
            场景
          </Text>
          <div style={fieldRowStyle}>
            {renderField(
              '场景地点',
              <Input
                value={value.environment?.location ?? ''}
                onChange={(e) => patchEnvironment({ location: e.target.value || undefined })}
                placeholder="如:霓虹雨夜的街头"
                maxLength={100}
              />,
            )}
            {renderField(
              '时间',
              <Select
                allowClear
                value={value.environment?.time_of_day}
                onChange={(v) => patchEnvironment({ time_of_day: v })}
                options={toOptions(TIME_OF_DAY_OPTIONS)}
                placeholder="请选择"
              />,
            )}
            {renderField(
              '天气',
              <Input
                value={value.environment?.weather ?? ''}
                onChange={(e) => patchEnvironment({ weather: e.target.value || undefined })}
                placeholder="如:小雨/大雾"
                maxLength={50}
              />,
            )}
            {renderField(
              '光线',
              <Input
                value={value.environment?.lighting ?? ''}
                onChange={(e) => patchEnvironment({ lighting: e.target.value || undefined })}
                placeholder="柔和顶光/逆光剪影"
                maxLength={100}
              />,
            )}
            {renderField(
              '氛围',
              <Input
                value={value.environment?.atmosphere ?? ''}
                onChange={(e) => patchEnvironment({ atmosphere: e.target.value || undefined })}
                placeholder="如:静谧/紧张/热闹"
                maxLength={100}
              />,
            )}
          </div>
        </div>
      ),
    },
    {
      key: 'audio_narrative',
      label: (
        <span>
          <SoundOutlined style={{ marginRight: 6, color: brand.primary }} />
          音频与叙事
        </span>
      ),
      children: (
        <div>
          <Text type="secondary" style={sectionLabelStyle}>
            音频
          </Text>
          <div style={fieldRowStyle}>
            {renderField(
              'BGM',
              <Select
                allowClear
                value={value.audio?.bgm_mode}
                onChange={(v) => patchAudio({ bgm_mode: v })}
                options={toOptions(BGM_MODE_OPTIONS)}
                placeholder="请选择"
              />,
            )}
            {renderField(
              '音效描述',
              <Input
                value={value.audio?.sfx_description ?? ''}
                onChange={(e) => patchAudio({ sfx_description: e.target.value || undefined })}
                placeholder="如:雨声、脚步声、心跳声"
                maxLength={100}
              />,
            )}
            {renderField(
              '旁白风格',
              <Select
                allowClear
                value={value.audio?.voice_style}
                onChange={(v) => patchAudio({ voice_style: v })}
                options={toOptions(VOICE_STYLE_OPTIONS)}
                placeholder="请选择"
              />,
            )}
          </div>

          <Text type="secondary" style={sectionLabelStyle}>
            叙事
          </Text>
          <div style={fieldRowStyle}>
            {renderField(
              '情绪基调',
              <Select
                allowClear
                value={value.narrative?.mood}
                onChange={(v) => patchNarrative({ mood: v })}
                options={toOptions(MOOD_OPTIONS)}
                placeholder="请选择"
              />,
            )}
            {renderField(
              '主题',
              <Input
                value={value.narrative?.theme ?? ''}
                onChange={(e) => patchNarrative({ theme: e.target.value || undefined })}
                placeholder="如:孤独与救赎"
                maxLength={100}
              />,
            )}
          </div>

          <Text type="secondary" style={sectionLabelStyle}>
            运动
          </Text>
          <div style={fieldRowStyle}>
            {renderField(
              '整体镜头运动',
              <Input
                value={value.motion?.camera_motion ?? ''}
                onChange={(e) => patchMotion({ camera_motion: e.target.value || undefined })}
                placeholder="如:整体缓慢横移"
                maxLength={100}
              />,
            )}
          </div>
        </div>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <SlidersOutlined style={{ color: brand.primary }} />
        <Text strong style={{ fontSize: 15 }}>
          专业创作控制
        </Text>
      </div>
      <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
        可选。在此补充结构化创作规格,提交后将全量编译进 Prompt。
      </Text>

      <Collapse
        ghost
        defaultActiveKey={[]}
        items={collapseItems}
        expandIcon={({ isActive }) => <CaretRightOutlined rotate={isActive ? 90 : 0} />}
      />
    </div>
  );
}
