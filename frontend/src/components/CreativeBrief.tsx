import { useEffect, useState } from 'react';
import { Button, Collapse, Input, InputNumber, Select, Switch, Typography } from 'antd';
import { CaretRightOutlined, SettingOutlined } from '@ant-design/icons';
import MultiModalInput from './MultiModalInput';
import SpecControls from './SpecControls';
import { useCreativeStore } from '../store/useCreativeStore';
import { api } from '../api/client';
import type { InputSourceItem, ProjectInfo } from '../api/client';

const { TextArea } = Input;
const { Title, Text } = Typography;

const RATIOS = [
  { label: '9:16 竖屏', value: '9:16' },
  { label: '16:9 横屏', value: '16:9' },
  { label: '1:1 正方', value: '1:1' },
];

export interface CreativeBriefValue {
  user_input: string;
  duration: number;
  aspect_ratio: string;
  compliance_enabled: boolean;
  input_sources: InputSourceItem[];
  /** 关联作品 ID:空则自动新建作品 */
  project_id?: string;
}

interface Props {
  loading: boolean;
  onSubmit: (value: CreativeBriefValue) => void;
}

/**
 * 创作输入第一层:用户先表达"想创作什么"。
 * 专业创作控制(风格/元素/镜头/音频)折叠收纳,提交时作为结构化 spec 传给后端。
 */
export default function CreativeBrief({ loading, onSubmit }: Props) {
  const [input, setInput] = useState('');
  const [duration, setDuration] = useState(30);
  const [aspectRatio, setAspectRatio] = useState('9:16');
  const [complianceEnabled, setComplianceEnabled] = useState(true);
  const [inputSources, setInputSources] = useState<InputSourceItem[]>([]);
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [projectId, setProjectId] = useState('');

  const spec = useCreativeStore((s) => s.spec);
  const updateSpec = useCreativeStore((s) => s.updateSpec);
  const setSpec = useCreativeStore((s) => s.setSpec);
  const resetSpec = useCreativeStore((s) => s.resetSpec);

  // 加载用户作品列表(关联创作到已有作品,如系列短剧)
  useEffect(() => {
    api.listProjects()
      .then((list) => setProjects(list))
      .catch(() => setProjects([]));
    resetSpec();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const syncSpec = (partial: Partial<{ prompt: string; duration: number; aspect_ratio: string }>) => {
    updateSpec(partial);
  };

  const handleSubmit = () => {
    if (!input.trim()) {
      return;
    }
    // 基础字段与 spec 保持一致(prompt/duration/aspect_ratio 由上方控件维护)
    setSpec({
      ...spec,
      prompt: input,
      duration,
      aspect_ratio: aspectRatio,
    });
    onSubmit({
      user_input: input,
      duration,
      aspect_ratio: aspectRatio,
      compliance_enabled: complianceEnabled,
      input_sources: inputSources,
      project_id: projectId,
    });
  };

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '48px 8px' }}>
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <Title level={2} style={{ marginBottom: 8 }}>
          你想创作什么？
        </Title>
        <Text type="secondary" style={{ fontSize: 15 }}>
          用自然语言描述你的创意,参考素材可选。AI 会先理解并整理创作方案,再由你确认后开始生成。
        </Text>
      </div>

      <TextArea
        value={input}
        onChange={(e) => {
          setInput(e.target.value);
          syncSpec({ prompt: e.target.value });
        }}
        rows={5}
        placeholder={'例如:一场暴雨中的未来城市,霓虹灯在积水中倒映,镜头缓慢推进……\n或:假如古代人有手机,他第一次刷短视频会发生什么?'}
        style={{ fontSize: 15, marginBottom: 16 }}
        maxLength={2000}
        showCount
      />

      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">参考素材(可选):上传图片 / 视频,或添加链接,并标注用途</Text>
        <div style={{ marginTop: 4 }}>
          <MultiModalInput sources={inputSources} onChange={setInputSources} />
        </div>
      </div>

      <Collapse
        ghost
        items={[
          {
            key: 'advanced',
            label: <span><SettingOutlined /> 高级设置</span>,
            children: (
              <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center' }}>
                <div>
                  <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                    时长(秒) — 不填由 AI 推断
                  </Text>
                  <InputNumber
                    min={5}
                    max={120}
                    value={duration}
                    onChange={(v) => {
                      setDuration(Number(v) || 30);
                      syncSpec({ duration: Number(v) || 30 });
                    }}
                    style={{ width: 120 }}
                  />
                </div>
                <div>
                  <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                    画面比例
                  </Text>
                  <Select
                    value={aspectRatio}
                    onChange={(v) => {
                      setAspectRatio(v);
                      syncSpec({ aspect_ratio: v });
                    }}
                    options={RATIOS}
                    style={{ width: 140 }}
                  />
                </div>
                <div>
                  <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                    关联作品
                  </Text>
                  <Select
                    value={projectId}
                    onChange={setProjectId}
                    style={{ width: 200 }}
                    options={[
                      { label: '自动新建作品', value: '' },
                      ...projects.map((p) => ({ label: p.title, value: p.id })),
                    ]}
                  />
                </div>
                <div>
                  <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                    内容安全检查
                  </Text>
                  <Switch checked={complianceEnabled} onChange={setComplianceEnabled} />
                </div>
              </div>
            ),
          },
          {
            key: 'spec',
            label: <span><SettingOutlined /> 专业创作控制(风格 / 元素 / 镜头 / 音频)</span>,
            children: (
              <SpecControls value={spec} onChange={setSpec} />
            ),
          },
        ]}
        expandIcon={({ isActive }) => <CaretRightOutlined rotate={isActive ? 90 : 0} />}
      />

      <Button
        type="primary"
        size="large"
        icon={<CaretRightOutlined />}
        loading={loading}
        disabled={!input.trim()}
        onClick={handleSubmit}
        block
        style={{ marginTop: 8, height: 48, fontSize: 16 }}
      >
        开始创作
      </Button>
    </div>
  );
}
