import { useState } from 'react';
import { Button, Dropdown, Input, InputNumber, Modal, Popconfirm, Tag, Typography, message } from 'antd';
import {
  ArrowLeftOutlined,
  CheckOutlined,
  DeleteOutlined,
  FileTextOutlined,
  PlusOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { brand } from '../theme';
import { api } from '../api/client';
import RegenerateWithFeedback from './RegenerateWithFeedback';

const { Title, Text, Paragraph } = Typography;

export interface ScriptScene {
  scene_id: number;
  duration: number;
  location: string;
  characters: string[];
  visual: string;
  dialogue: string;
  voiceover: string;
}

export interface ScriptData {
  title: string;
  hook: string;
  scenes: ScriptScene[];
  ending: string | null;
}

/** 局部 AI 操作类型 */
type SceneAction = 'continue' | 'rewrite' | 'expand' | 'condense';

const ACTION_META: Record<SceneAction, { label: string; hint: string }> = {
  continue: { label: 'AI 续写', hint: '承接本场景剧情,在其后插入一个新场景' },
  rewrite: { label: 'AI 改写', hint: '保持剧情走向,重新创作本场景' },
  expand: { label: 'AI 扩写', hint: '保留原有内容,扩充画面与对白细节' },
  condense: { label: 'AI 缩写', hint: '精简本场景,保留核心剧情' },
};

interface Props {
  script: ScriptData;
  targetDuration: number;
  regenerating: boolean;
  submitting: boolean;
  /** 提供 taskId 时启用场景级局部 AI(续写/改写/扩写/缩写) */
  taskId?: string;
  onRegenerate: (feedback?: string) => void;
  onConfirm: (edited: ScriptData) => void;
  onBack: () => void;
}

/** 可点击编辑的脚本文本字段 */
function EditableField({
  label,
  value,
  onChange,
  placeholder,
  multiline,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  multiline?: boolean;
}) {
  const content = value || <span style={{ color: '#bbb' }}>{placeholder || '未填写'}</span>;
  const editable = {
    icon: <span style={{ color: brand.primary }}>编辑</span>,
    onChange,
    tooltip: '点击编辑',
  };
  return (
    <div>
      <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>
        {label}
      </Text>
      {multiline ? (
        <Paragraph
          editable={editable}
          style={{ margin: 0, fontSize: 14, lineHeight: 1.6, minHeight: 22, whiteSpace: 'pre-wrap' }}
        >
          {content}
        </Paragraph>
      ) : (
        <Text
          editable={editable}
          style={{ fontSize: 14, minHeight: 22, display: 'inline-block' }}
        >
          {content}
        </Text>
      )}
    </div>
  );
}

/**
 * Gate 2 脚本审核页:脚本已生成,等待用户确认。
 * 支持:编辑字段 / 删除场景 / 新增场景 / 重新生成 / 确认进入分镜。
 */
export default function ScriptReview({
  script,
  targetDuration,
  regenerating,
  submitting,
  taskId,
  onRegenerate,
  onConfirm,
  onBack,
}: Props) {
  const [draft, setDraft] = useState<ScriptData>({ ...script, ending: script.ending ?? '' });
  // 局部 AI 状态
  const [aiAction, setAiAction] = useState<{ action: SceneAction; sceneIndex: number } | null>(null);
  const [aiInstruction, setAiInstruction] = useState('');
  const [aiLoading, setAiLoading] = useState(false);

  const totalDuration = draft.scenes.reduce((s, sc) => s + (sc.duration || 0), 0);

  const updateScene = (index: number, patch: Partial<ScriptScene>) => {
    setDraft((d) => ({
      ...d,
      scenes: d.scenes.map((sc, i) => (i === index ? { ...sc, ...patch } : sc)),
    }));
  };

  const deleteScene = (index: number) => {
    setDraft((d) => ({
      ...d,
      scenes: d.scenes
        .filter((_, i) => i !== index)
        .map((sc, i) => ({ ...sc, scene_id: i + 1 })),
    }));
  };

  const addScene = () => {
    setDraft((d) => ({
      ...d,
      scenes: [
        ...d.scenes,
        {
          scene_id: d.scenes.length + 1,
          duration: 5,
          location: '',
          characters: [],
          visual: '',
          dialogue: '',
          voiceover: '',
        },
      ],
    }));
  };

  const handleConfirm = () => {
    if (!draft.title?.trim()) {
      message.warning('请补充脚本标题');
      return;
    }
    if (draft.scenes.length === 0) {
      message.warning('至少需要一个场景');
      return;
    }
    onConfirm(draft);
  };

  // 局部 AI 执行:结果只更新草稿,用户可继续编辑(保有最终编辑权)
  const runSceneAI = async () => {
    if (!aiAction || !taskId) return;
    setAiLoading(true);
    try {
      const cur = draft.scenes[aiAction.sceneIndex];
      const resp = await api.scriptSceneAI(taskId, {
        scene_index: aiAction.sceneIndex,
        action: aiAction.action,
        instruction: aiInstruction.trim() || undefined,
        scene: { ...cur },
      });
      const newScene: ScriptScene = {
        scene_id: Number(resp.scene.scene_id) || cur.scene_id,
        duration: Number(resp.scene.duration) || cur.duration,
        location: resp.scene.location || '',
        characters: Array.isArray(resp.scene.characters) ? resp.scene.characters : [],
        visual: resp.scene.visual || '',
        dialogue: resp.scene.dialogue || '',
        voiceover: resp.scene.voiceover || '',
      };
      setDraft((d) => {
        if (aiAction.action === 'continue') {
          // 续写:在目标场景后插入新场景,并重排编号
          const scenes = [...d.scenes];
          scenes.splice(aiAction.sceneIndex + 1, 0, newScene);
          return { ...d, scenes: scenes.map((sc, i) => ({ ...sc, scene_id: i + 1 })) };
        }
        // 改写/扩写/缩写:替换目标场景
        return {
          ...d,
          scenes: d.scenes.map((sc, i) => (i === aiAction.sceneIndex ? newScene : sc)),
        };
      });
      message.success(
        aiAction.action === 'continue' ? '已续写新场景,可继续编辑' : '场景已更新,可继续编辑',
      );
      setAiAction(null);
      setAiInstruction('');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'AI 处理失败,请稍后重试');
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 860, margin: '0 auto', padding: '32px 8px' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 4 }}>
          <FileTextOutlined style={{ color: brand.primary, marginRight: 8 }} />
          脚本已生成
        </Title>
        <Text type="secondary">
          以下是 AI 根据创作方案生成的脚本。你可以直接编辑任意字段、增删场景,或让 AI 重新生成。确认后才进入分镜阶段。
        </Text>
      </div>

      {/* 脚本元信息 */}
      <div
        style={{
          background: '#fff',
          borderRadius: 12,
          padding: 20,
          border: '1px solid #f0f0f0',
          marginBottom: 16,
        }}
      >
        <EditableField label="标题" value={draft.title} onChange={(v) => setDraft((d) => ({ ...d, title: v }))} />
        {draft.hook && (
          <div style={{ marginTop: 16, padding: '10px 12px', background: '#fffbe6', border: '1px solid #ffe58f', borderRadius: 6 }}>
            <EditableField label="Hook(前 3 秒)" value={draft.hook} onChange={(v) => setDraft((d) => ({ ...d, hook: v }))} multiline />
          </div>
        )}
      </div>

      {/* 场景列表 */}
      {draft.scenes.map((scene, i) => (
        <div
          key={i}
          style={{
            background: '#fff',
            borderRadius: 12,
            padding: 16,
            border: '1px solid #f0f0f0',
            marginBottom: 12,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <Tag color="blue" style={{ fontSize: 13, padding: '2px 10px' }}>
                场景 {scene.scene_id}
              </Tag>
              <InputNumber
                min={1}
                max={60}
                value={scene.duration}
                onChange={(v) => updateScene(i, { duration: Number(v) || 5 })}
                addonAfter="秒"
                style={{ width: 100 }}
              />
              {taskId && (
                <Dropdown
                  menu={{
                    items: (Object.keys(ACTION_META) as SceneAction[]).map((a) => ({
                      key: a,
                      label: (
                        <div>
                          <div>{ACTION_META[a].label}</div>
                          <Text type="secondary" style={{ fontSize: 11 }}>{ACTION_META[a].hint}</Text>
                        </div>
                      ),
                    })),
                    onClick: ({ key }) => {
                      setAiAction({ action: key as SceneAction, sceneIndex: i });
                      setAiInstruction('');
                    },
                  }}
                  trigger={['click']}
                >
                  <Button size="small" icon={<RobotOutlined />} style={{ color: brand.primary }}>
                    AI
                  </Button>
                </Dropdown>
              )}
            </div>
            <Popconfirm
              title="删除该场景?"
              description="删除后不可恢复(可重新新增)"
              onConfirm={() => deleteScene(i)}
              okText="删除"
              cancelText="取消"
            >
              <Button type="text" danger icon={<DeleteOutlined />} size="small">
                删除场景
              </Button>
            </Popconfirm>
          </div>

          <EditableField label="地点" value={scene.location} onChange={(v) => updateScene(i, { location: v })} placeholder="如:城市街道 / 室内 / 外星荒漠" />
          <div style={{ height: 12 }} />
          <EditableField label="画面" value={scene.visual} onChange={(v) => updateScene(i, { visual: v })} multiline placeholder="这一场的画面内容" />
          <div style={{ height: 12 }} />
          <EditableField label="对白" value={scene.dialogue} onChange={(v) => updateScene(i, { dialogue: v })} multiline placeholder="角色说的话(可留空)" />
          <div style={{ height: 12 }} />
          <EditableField label="旁白" value={scene.voiceover} onChange={(v) => updateScene(i, { voiceover: v })} multiline placeholder="画外音(可留空)" />
        </div>
      ))}

      <Button
        block
        type="dashed"
        icon={<PlusOutlined />}
        onClick={addScene}
        style={{ marginBottom: 16, height: 44 }}
      >
        新增场景
      </Button>

      {/* 结尾 */}
      {draft.ending !== '' && draft.ending !== null && (
        <div
          style={{
            background: '#fff',
            borderRadius: 12,
            padding: 16,
            border: '1px solid #f0f0f0',
            marginBottom: 16,
          }}
        >
          <EditableField label="结尾" value={draft.ending ?? ''} onChange={(v) => setDraft((d) => ({ ...d, ending: v }))} multiline />
        </div>
      )}

      {/* 时长提示 */}
      <div style={{ marginBottom: 20, textAlign: 'center' }}>
        {totalDuration !== targetDuration ? (
          <Text type="warning" style={{ fontSize: 13 }}>
            场景总时长 {totalDuration} 秒,目标时长 {targetDuration} 秒(分镜将按各场景时长生成)
          </Text>
        ) : (
          <Text type="secondary" style={{ fontSize: 13 }}>
            场景总时长 {totalDuration} 秒,与目标一致
          </Text>
        )}
      </div>

      {/* 操作区 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <Button size="large" icon={<ArrowLeftOutlined />} onClick={onBack}>
          返回修改创意
        </Button>
        <div style={{ display: 'flex', gap: 12 }}>
          <RegenerateWithFeedback
            label="重新生成脚本"
            title="脚本哪里不满意?"
            placeholder="例如:人物动机不合理,第二场冲突太突兀"
            loading={regenerating}
            onRegenerate={(fb) => onRegenerate(fb)}
          />
          <Button
            type="primary"
            size="large"
            icon={<CheckOutlined />}
            loading={submitting}
            onClick={handleConfirm}
            style={{ minWidth: 160 }}
          >
            确认脚本
          </Button>
        </div>
      </div>

      {/* 局部 AI 指令弹窗 */}
      <Modal
        open={!!aiAction}
        title={aiAction ? `${ACTION_META[aiAction.action].label} — 场景 ${aiAction.sceneIndex + 1}` : ''}
        onCancel={() => { if (!aiLoading) { setAiAction(null); setAiInstruction(''); } }}
        onOk={runSceneAI}
        okText="开始生成"
        cancelText="取消"
        confirmLoading={aiLoading}
        okButtonProps={{ disabled: !taskId }}
      >
        {aiAction && (
          <>
            <Paragraph type="secondary" style={{ marginBottom: 8 }}>
              {ACTION_META[aiAction.action].hint}。生成结果会更新到下方草稿,你仍可继续编辑。
            </Paragraph>
            <Input.TextArea
              value={aiInstruction}
              onChange={(e) => setAiInstruction(e.target.value)}
              rows={3}
              maxLength={300}
              showCount
              placeholder="具体要求(可选),例如:对白更幽默一些 / 强调雨天氛围 / 节奏更快"
              disabled={aiLoading}
            />
          </>
        )}
      </Modal>
    </div>
  );
}
