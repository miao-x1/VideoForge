/**
 * 作品设定面板(Bible 可视化)。
 * 展示 AI Director 建立的作品级设定:故事节拍/人物档案/世界观/视觉风格。
 * 面向用户隐藏内部术语(Bible/State),统一以"作品设定"呈现。
 * 提供 taskId 时支持编辑关键设定并保存到后端(任务处理中后端会返回 409)。
 */
import { useState } from 'react';
import {
  Button, Collapse, Input, Tag, Typography, Empty, Timeline, message,
} from 'antd';
import {
  BookOutlined, UserOutlined, GlobalOutlined, BgColorsOutlined,
  EditOutlined, PlusOutlined, DeleteOutlined,
} from '@ant-design/icons';
import { accents, calloutStyle } from '../theme';
import { api } from '../api/client';
import type { ProjectState, CharacterBible } from '../api/client';

const { Text, Paragraph } = Typography;

interface Props {
  projectState: ProjectState | null;
  /** 提供 taskId 时启用编辑能力 */
  taskId?: string;
  /** 保存成功后回调(父级用新数据刷新) */
  onUpdated?: (ps: ProjectState) => void;
}

/** 深拷贝草稿(ProjectState 来源于后端 JSON,可安全序列化往返) */
function cloneProjectState(ps: ProjectState): ProjectState {
  return JSON.parse(JSON.stringify(ps)) as ProjectState;
}

/** 编辑态字段:小字 label + 紧凑输入框 */
function EditField({ label, value, onChange, textarea }: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  textarea?: boolean;
}) {
  return (
    <div style={{ marginBottom: 6 }}>
      <Text type="secondary" style={{ fontSize: 12 }}>{label}</Text>
      {textarea ? (
        <Input.TextArea
          size="small"
          autoSize={{ minRows: 1, maxRows: 4 }}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          style={{ marginTop: 2, fontSize: 13 }}
        />
      ) : (
        <Input
          size="small"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          style={{ marginTop: 2, fontSize: 13 }}
        />
      )}
    </div>
  );
}

/** 文本字段行:字段存在才渲染;编辑模式下渲染为输入框,否则保持只读段落 */
function TextFieldRow({ label, value, editing, onChange, margin = '4px 0', textarea }: {
  label: string;
  value?: string;
  editing?: boolean;
  onChange: (v: string) => void;
  margin?: string;
  textarea?: boolean;
}) {
  if (!value) return null;
  if (editing) {
    return <EditField label={label} value={value} onChange={onChange} textarea={textarea} />;
  }
  return (
    <Paragraph style={{ margin, fontSize: 13 }}>
      <Text type="secondary">{label}: </Text>{value}
    </Paragraph>
  );
}

/** 人物档案中的文本字段(均为 string 类型,可安全读写) */
type CharacterTextField =
  'name' | 'age' | 'gender' | 'identity' | 'personality' | 'appearance'
  | 'hairstyle' | 'clothing' | 'body_type' | 'speech_style' | 'emotion_traits' | 'background';

/** 人物档案中允许编辑的字段 */
const CHARACTER_EDITABLE_FIELDS: CharacterTextField[] = ['name', 'appearance', 'clothing', 'personality', 'speech_style', 'background'];

const CHARACTER_TEXT_FIELDS: [string, CharacterTextField][] = [
  ['年龄', 'age'],
  ['性别', 'gender'],
  ['身份', 'identity'],
  ['性格', 'personality'],
  ['外貌', 'appearance'],
  ['发型', 'hairstyle'],
  ['服装', 'clothing'],
  ['体型', 'body_type'],
  ['说话方式', 'speech_style'],
  ['情绪特点', 'emotion_traits'],
  ['背景', 'background'],
];

/** 人物档案卡片 */
function CharacterCard({ bible, currentStatus, editing, onFieldChange }: {
  bible: CharacterBible;
  currentStatus?: string;
  editing?: boolean;
  onFieldChange?: (field: CharacterTextField, value: string) => void;
}) {
  return (
    <div
      style={{
        marginBottom: 8,
        padding: '10px 12px',
        background: accents.neutral.bg,
        border: `1px solid ${accents.neutral.border}`,
        borderRadius: 6,
      }}
    >
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', marginBottom: 6 }}>
        {editing && bible.name ? (
          <Input
            size="small"
            value={bible.name}
            onChange={(e) => onFieldChange?.('name', e.target.value)}
            style={{ width: 160, fontWeight: 600 }}
          />
        ) : (
          <Text strong style={{ fontSize: 14 }}>{bible.name}</Text>
        )}
        {bible.identity && <Tag color="blue">{bible.identity}</Tag>}
        {bible.status === 'exited' && <Tag>已离场</Tag>}
        {bible.status === 'background' && <Tag>背景人物</Tag>}
      </div>
      {bible.relations?.length > 0 && (
        <div style={{ marginBottom: 6, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {bible.relations.map((r, i) => (
            <Tag key={i} color="purple">
              {r.target_name} · {r.relation}
            </Tag>
          ))}
        </div>
      )}
      {CHARACTER_TEXT_FIELDS.map(([label, field]) => (
        <TextFieldRow
          key={label}
          label={label}
          value={bible[field]}
          editing={editing && CHARACTER_EDITABLE_FIELDS.includes(field)}
          margin="2px 0"
          textarea={field === 'appearance' || field === 'background' || field === 'personality'}
          onChange={(v) => onFieldChange?.(field, v)}
        />
      ))}
      {bible.visual_keywords?.length > 0 && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
          {bible.visual_keywords.map((k, i) => (
            <Tag key={i} color="cyan" style={{ fontSize: 11 }}>{k}</Tag>
          ))}
        </div>
      )}
      {currentStatus && (
        <div style={{ ...calloutStyle(accents.info), marginTop: 6 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>当前状态: </Text>
          <Text style={{ fontSize: 13 }}>{currentStatus}</Text>
        </div>
      )}
    </div>
  );
}

/** 故事中的文本字段(可编辑:theme / core_conflict) */
type StoryTextField = 'theme' | 'logline' | 'core_conflict' | 'ending_tone';

const STORY_FIELDS: [string, StoryTextField, boolean][] = [
  ['主题', 'theme', true],
  ['核心冲突', 'core_conflict', true],
  ['结局基调', 'ending_tone', false],
];

/** 世界观中的文本字段(可编辑:era / region) */
type WorldTextField = 'era' | 'region' | 'architecture' | 'weather_base' | 'time_span' | 'world_rules';

const WORLD_FIELDS: [string, WorldTextField, boolean][] = [
  ['时代', 'era', true],
  ['地域', 'region', true],
  ['建筑风格', 'architecture', false],
  ['基线天气', 'weather_base', false],
  ['时间跨度', 'time_span', false],
  ['世界观规则', 'world_rules', false],
];

/** 视觉风格中的文本字段(可编辑:visual_style / photography_style / color_palette / lighting_base) */
type StyleTextField =
  'visual_style' | 'photography_style' | 'color_palette' | 'color_temperature'
  | 'saturation' | 'contrast' | 'color_grading' | 'lighting_base' | 'lens_language' | 'texture';

const STYLE_FIELDS: [string, StyleTextField, boolean][] = [
  ['画面风格', 'visual_style', true],
  ['摄影风格', 'photography_style', true],
  ['主色调', 'color_palette', true],
  ['色温', 'color_temperature', false],
  ['饱和度', 'saturation', false],
  ['对比度', 'contrast', false],
  ['调色', 'color_grading', false],
  ['光线基调', 'lighting_base', true],
  ['镜头语言', 'lens_language', false],
  ['画面质感', 'texture', false],
];

export default function BiblePanel({ projectState, taskId, onUpdated }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<ProjectState | null>(null);
  const [saving, setSaving] = useState(false);

  if (!projectState) {
    return <Empty description="暂无作品设定" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  // 编辑模式渲染本地草稿,只读模式渲染原始数据
  const data = editing && draft ? draft : projectState;

  const startEdit = () => {
    setDraft(cloneProjectState(projectState));
    setEditing(true);
  };

  const cancelEdit = () => {
    setEditing(false);
    setDraft(null);
  };

  const saveEdit = async () => {
    if (!taskId || !draft) return;
    setSaving(true);
    try {
      await api.updateProjectState(taskId, draft);
      message.success('作品设定已保存');
      setEditing(false);
      setDraft(null);
      onUpdated?.(draft);
    } catch (e: any) {
      // 任务处理中后端返回 409 等,直接展示后端 detail
      message.error(e?.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  /** 从当前草稿整份克隆后修改,派生新草稿(避免直接变异状态) */
  const updateDraft = (mutate: (d: ProjectState) => void) => {
    if (!draft) return;
    const next = cloneProjectState(draft);
    mutate(next);
    setDraft(next);
  };

  const { story_state, character_state, world_state, style_state, project_info } = data;
  const world = world_state?.bible;
  const style = style_state?.bible;
  const hasStory =
    story_state?.theme || story_state?.logline || story_state?.beats?.length ||
    story_state?.character_arcs?.length;
  const hasCharacters = character_state?.bibles?.length > 0;
  const hasWorld = !!world && (world.era || world.region || world.scenes?.length || world.world_rules);
  const hasStyle = !!style && (style.visual_style || style.color_palette || style.lighting_base);

  const items = [];

  if (hasStory) {
    items.push({
      key: 'story',
      label: (
        <span><BookOutlined style={{ marginRight: 6 }} />故事 · {story_state.beats?.length || 0} 个节拍</span>
      ),
      children: (
        <div>
          {story_state.logline && (
            editing ? (
              <EditField
                label="一句话故事"
                value={story_state.logline}
                textarea
                onChange={(v) => updateDraft((d) => { if (d.story_state) d.story_state.logline = v; })}
              />
            ) : (
              <div style={{ ...calloutStyle(accents.brand), marginBottom: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>一句话故事: </Text>
                <Text strong style={{ fontSize: 13 }}>{story_state.logline}</Text>
              </div>
            )
          )}
          {STORY_FIELDS.map(([label, field, editable]) => (
            <TextFieldRow
              key={label}
              label={label}
              value={story_state[field]}
              editing={editing && editable}
              onChange={(v) => updateDraft((d) => { if (d.story_state) d.story_state[field] = v; })}
            />
          ))}
          {story_state.beats?.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>节拍脉络</Text>
              <Timeline
                style={{ marginTop: 8 }}
                items={story_state.beats.map((b) => ({
                  children: (
                    <div>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                        <Text strong style={{ fontSize: 13 }}>{b.name}</Text>
                        {b.emotion && <Tag color="gold">{b.emotion}</Tag>}
                      </div>
                      {b.summary && (
                        <Paragraph style={{ margin: '2px 0 0', fontSize: 13 }}>{b.summary}</Paragraph>
                      )}
                    </div>
                  ),
                }))}
              />
            </div>
          )}
          {story_state.character_arcs?.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>人物成长线</Text>
              {story_state.character_arcs.map((a, i) => {
                const name = character_state?.bibles?.find((b) => b.character_id === a.character_id)?.name;
                return (
                  <div key={i} style={{ ...calloutStyle(accents.success), marginTop: 6 }}>
                    <Text strong style={{ fontSize: 13 }}>{name || a.character_id}</Text>
                    <Paragraph style={{ margin: '2px 0', fontSize: 13 }}>
                      <Text type="secondary">起点: </Text>{a.start_state || '—'}
                    </Paragraph>
                    <Paragraph style={{ margin: '2px 0', fontSize: 13 }}>
                      <Text type="secondary">终点: </Text>{a.end_state || '—'}
                    </Paragraph>
                    {a.arc_summary && (
                      <Paragraph style={{ margin: '2px 0', fontSize: 13 }}>{a.arc_summary}</Paragraph>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ),
    });
  }

  if (hasCharacters) {
    items.push({
      key: 'characters',
      label: (
        <span><UserOutlined style={{ marginRight: 6 }} />人物 · {character_state.bibles.length} 位</span>
      ),
      children: (
        <div>
          {character_state.bibles.map((b) => (
            <CharacterCard
              key={b.character_id}
              bible={b}
              currentStatus={character_state.current_status?.[b.character_id]}
              editing={editing}
              onFieldChange={(field, v) => updateDraft((d) => {
                const target = d.character_state?.bibles?.find((c) => c.character_id === b.character_id);
                if (target) target[field] = v;
              })}
            />
          ))}
        </div>
      ),
    });
  }

  if (hasWorld) {
    items.push({
      key: 'world',
      label: (
        <span>
          <GlobalOutlined style={{ marginRight: 6 }} />
          世界观{world.scenes?.length ? ` · ${world.scenes.length} 个场景` : ''}
        </span>
      ),
      children: (
        <div>
          {WORLD_FIELDS.map(([label, field, editable]) => (
            <TextFieldRow
              key={label}
              label={label}
              value={world[field]}
              editing={editing && editable}
              onChange={(v) => updateDraft((d) => { const w = d.world_state?.bible; if (w) w[field] = v; })}
            />
          ))}
          {editing && Array.isArray(world.props_system) ? (
            <div style={{ margin: '6px 0' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>关键道具</Text>
              {world.props_system.map((p, j) => (
                <div key={j} style={{ display: 'flex', gap: 4, marginTop: 4, alignItems: 'center' }}>
                  <Input
                    size="small"
                    value={p}
                    onChange={(e) => updateDraft((d) => { const arr = d.world_state?.bible?.props_system; if (arr) arr[j] = e.target.value; })}
                  />
                  <Button
                    size="small"
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => updateDraft((d) => { const w = d.world_state?.bible; if (w?.props_system) w.props_system.splice(j, 1); })}
                  />
                </div>
              ))}
              <Button
                size="small"
                type="dashed"
                block
                icon={<PlusOutlined />}
                style={{ marginTop: 4 }}
                onClick={() => updateDraft((d) => { const w = d.world_state?.bible; if (w) w.props_system = [...(w.props_system || []), '']; })}
              >
                添加道具
              </Button>
            </div>
          ) : (world.props_system?.length > 0 && (
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', margin: '6px 0' }}>
              <Text type="secondary" style={{ fontSize: 13 }}>关键道具: </Text>
              {world.props_system.map((p, i) => (
                <Tag key={i} color="orange">{p}</Tag>
              ))}
            </div>
          ))}
          {world.scenes?.map((s, i) => (
            <div
              key={i}
              style={{
                marginBottom: 6,
                padding: '8px 10px',
                background: accents.neutral.bg,
                border: `1px solid ${accents.neutral.border}`,
                borderRadius: 4,
              }}
            >
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 4, alignItems: 'center' }}>
                {editing && s.name ? (
                  <Input
                    size="small"
                    value={s.name}
                    onChange={(e) => updateDraft((d) => { const sc = d.world_state?.bible?.scenes?.[i]; if (sc) sc.name = e.target.value; })}
                    style={{ width: 150, fontWeight: 600 }}
                  />
                ) : (
                  <Text strong style={{ fontSize: 13 }}>{s.name || s.scene_key}</Text>
                )}
                {s.location && <Tag color="cyan">{s.location}</Tag>}
                {s.time_of_day && <Tag>{s.time_of_day}</Tag>}
                {s.weather && <Tag>{s.weather}</Tag>}
                {s.lighting && <Tag color="gold">{s.lighting}</Tag>}
              </div>
              {editing && s.description ? (
                <Input.TextArea
                  size="small"
                  autoSize={{ minRows: 1, maxRows: 4 }}
                  value={s.description}
                  onChange={(e) => updateDraft((d) => { const sc = d.world_state?.bible?.scenes?.[i]; if (sc) sc.description = e.target.value; })}
                  style={{ fontSize: 13 }}
                />
              ) : s.description ? (
                <Paragraph style={{ margin: 0, fontSize: 13 }}>{s.description}</Paragraph>
              ) : null}
            </div>
          ))}
        </div>
      ),
    });
  }

  if (hasStyle) {
    items.push({
      key: 'style',
      label: <span><BgColorsOutlined style={{ marginRight: 6 }} />视觉风格</span>,
      children: (
        <div>
          {STYLE_FIELDS.map(([label, field, editable]) => (
            <TextFieldRow
              key={label}
              label={label}
              value={style[field]}
              editing={editing && editable}
              onChange={(v) => updateDraft((d) => { const st = d.style_state?.bible; if (st) st[field] = v; })}
            />
          ))}
          {style.negative_keywords?.length > 0 && (
            <div style={{ ...calloutStyle(accents.error), marginTop: 6 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>全片规避元素: </Text>
              {style.negative_keywords.map((k, i) => (
                <Tag key={i} style={{ fontSize: 11 }}>{k}</Tag>
              ))}
            </div>
          )}
        </div>
      ),
    });
  }

  if (!items.length) {
    return <Empty description="暂无作品设定" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  return (
    <div>
      {taskId && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginBottom: 8 }}>
          {editing ? (
            <>
              <Button size="small" onClick={cancelEdit}>取消</Button>
              <Button size="small" type="primary" loading={saving} onClick={saveEdit}>保存设定</Button>
            </>
          ) : (
            <Button size="small" icon={<EditOutlined />} onClick={startEdit}>编辑设定</Button>
          )}
        </div>
      )}
      {project_info?.title && (
        <div style={{ marginBottom: 10 }}>
          <Text strong style={{ fontSize: 15 }}>{project_info.title}</Text>
          {project_info.genre && <Tag color="purple" style={{ marginLeft: 8 }}>{project_info.genre}</Tag>}
        </div>
      )}
      <Collapse size="small" defaultActiveKey={items.map((i) => i.key)} items={items} />
    </div>
  );
}
