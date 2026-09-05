import { useMemo, useState } from 'react';
import { Button, Collapse, Input, Select, Typography, Upload, message } from 'antd';
import { CopyOutlined, DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import { CATALOG, CATALOG_GROUPS } from '../catalog';
import { CHARACTER_TEMPLATES } from '../characters/templates';
import { useCharacterLibrary } from '../characters/useCharacterLibrary';
import { useDirectorStore } from '../store/useDirectorStore';
import { applySceneCanvasFile } from '../sceneCanvas';
import { SCENE_PRESETS } from '../scenePresets';
import { directorDark, radius } from '../../theme';
import CreateCharacterModal from './CreateCharacterModal';
import MediaLibrary from './MediaLibrary';

const { Text } = Typography;

function typeLabel(type?: string) {
  if (type === 'animal') return '动物';
  if (type === 'special') return '特殊';
  return '人物';
}

function modelStatus(rig?: string, anim?: string) {
  if (rig === 'ready' && (anim === 'ready' || anim === 'partial')) return '模型就绪';
  if (rig === 'failed' || anim === 'failed') return '绑定失败';
  return '未就绪';
}

export function CharacterLibrary({ onEdit }: { onEdit?: () => void }) {
  const addOfficialTemplate = useDirectorStore((s) => s.addOfficialTemplate);
  const instanceCharacter = useDirectorStore((s) => s.instanceCharacter);
  const scenes = useDirectorStore((s) => s.scenes);
  const characters = useCharacterLibrary((s) => s.characters);
  const remove = useCharacterLibrary((s) => s.remove);
  const duplicate = useCharacterLibrary((s) => s.duplicate);
  const [query, setQuery] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const q = query.trim().toLowerCase();
  const ready = CHARACTER_TEMPLATES.filter((t) => t.available && (!q || t.name.toLowerCase().includes(q)));
  const mine = characters.filter((c) => !q || c.name.toLowerCase().includes(q));

  const usage = (id: string) =>
    scenes.reduce((n, scene) => n + scene.objects.filter((o) => o.characterId === id).length, 0);

  if (mine.length === 0 && !q) {
    return (
      <div style={{ padding: 12 }}>
        <EmptyCharacter onCreate={() => setCreateOpen(true)} />
        <CreateCharacterModal open={createOpen} onClose={() => setCreateOpen(false)} />
        <div style={{ marginTop: 16 }}>
          <Text style={{ color: directorDark.muted, fontSize: 12, display: 'block', marginBottom: 8 }}>
            或从官方模板开始
          </Text>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            {ready.slice(0, 6).map((t) => (
              <CardButton
                key={t.id}
                name={t.name}
                note={typeLabel(t.characterType)}
                onClick={() => {
                  if (addOfficialTemplate(t.id)) message.success(`已加入镜头：${t.name}`);
                }}
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: 8 }}>
      <Input.Search
        allowClear
        size="small"
        placeholder="搜索角色"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        style={{ marginBottom: 8 }}
      />
      <Button type="primary" size="small" block style={{ marginBottom: 10 }} onClick={() => setCreateOpen(true)}>
        创建角色
      </Button>
      <CreateCharacterModal open={createOpen} onClose={() => setCreateOpen(false)} />

      {mine.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
          {mine.map((c) => (
            <div
              key={c.id}
              style={{
                border: `1px solid ${directorDark.border}`,
                borderRadius: 8,
                padding: 10,
                background: directorDark.panel,
              }}
            >
              <div style={{ display: 'flex', gap: 10 }}>
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 8,
                    background: '#2a2a48',
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                >
                  {c.name.slice(0, 1)}
                </div>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ color: directorDark.text, fontWeight: 600, fontSize: 13 }}>{c.name}</div>
                  <div style={{ color: directorDark.muted, fontSize: 11 }}>
                    {typeLabel(c.characterType)} · {modelStatus(c.rigStatus, c.animationStatus)}
                  </div>
                  <div style={{ color: directorDark.muted, fontSize: 11 }}>使用 {usage(c.id)} 次</div>
                </div>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                <Button size="small" icon={<PlusOutlined />} onClick={() => instanceCharacter(c.id)}>
                  使用
                </Button>
                <Button
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => {
                    const id = instanceCharacter(c.id);
                    if (id) onEdit?.();
                  }}
                >
                  编辑
                </Button>
                <Button
                  size="small"
                  icon={<CopyOutlined />}
                  onClick={() => {
                    const copy = duplicate(c.id);
                    if (copy) message.success(`已复制 ${copy.name}`);
                  }}
                >
                  复制
                </Button>
                <Button size="small" danger icon={<DeleteOutlined />} onClick={() => remove(c.id)}>
                  删除
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Text style={{ color: directorDark.muted, fontSize: 12, display: 'block', marginBottom: 6 }}>系统角色库</Text>
      {[
        { label: '男', items: ready.filter((t) => t.gender === 'male' && t.ageGroup !== 'elder' && t.ageGroup !== 'child') },
        { label: '女', items: ready.filter((t) => t.gender === 'female' && t.ageGroup !== 'elder') },
        { label: '老人', items: ready.filter((t) => t.ageGroup === 'elder') },
        { label: '小孩', items: ready.filter((t) => t.ageGroup === 'child' || t.ageGroup === 'teen') },
        { label: '风格 / 其他', items: ready.filter((t) => t.characterType !== 'human') },
      ].filter((g) => g.items.length).map((group) => (
        <div key={group.label} style={{ marginBottom: 10 }}>
          <Text style={{ color: directorDark.muted, fontSize: 11, display: 'block', marginBottom: 6 }}>{group.label}</Text>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            {group.items.map((t) => (
              <CardButton
                key={t.id}
                name={t.name}
                note={typeLabel(t.characterType)}
                onClick={() => {
                  if (addOfficialTemplate(t.id)) message.success(`已使用 ${t.name}`);
                }}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyCharacter({ onCreate }: { onCreate: () => void }) {
  return (
    <div
      style={{
        padding: 16,
        border: `1px dashed ${directorDark.border}`,
        borderRadius: 10,
        textAlign: 'center',
      }}
    >
      <div style={{ color: directorDark.text, fontWeight: 600, marginBottom: 6 }}>还没有角色</div>
      <div style={{ color: directorDark.muted, fontSize: 12, marginBottom: 12 }}>上传模型创建角色，或从官方模板开始</div>
      <Button type="primary" size="small" onClick={onCreate}>
        创建角色
      </Button>
    </div>
  );
}

export function SceneLibrary() {
  const applyScenePreset = useDirectorStore((s) => s.applyScenePreset);
  const applyEnvironmentLook = useDirectorStore((s) => s.applyEnvironmentLook);
  const environment = useDirectorStore((s) => s.environment);
  const objects = useDirectorStore((s) => s.objects);
  const createShotScene = useDirectorStore((s) => s.createShotScene);

  return (
    <div style={{ padding: 8 }}>
      {objects.length === 0 && (
        <div
          style={{
            padding: 16,
            border: `1px dashed ${directorDark.border}`,
            borderRadius: 10,
            textAlign: 'center',
            marginBottom: 12,
          }}
        >
          <div style={{ color: directorDark.text, fontWeight: 600, marginBottom: 6 }}>创建你的第一个场景</div>
          <div style={{ color: directorDark.muted, fontSize: 12, marginBottom: 12 }}>选择预设，或先新建一个空镜头再摆道具</div>
          <Button size="small" type="primary" onClick={() => createShotScene()}>
            新建镜头
          </Button>
        </div>
      )}
      <Text style={{ color: directorDark.muted, fontSize: 12, display: 'block', marginBottom: 6 }}>系统场景</Text>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 12 }}>
        {SCENE_PRESETS.map((preset) => (
          <CardButton
            key={preset.id}
            name={preset.name}
            onClick={() => {
              applyScenePreset(preset.id);
              message.success(`已放入 ${preset.name}`);
            }}
          />
        ))}
      </div>
      <Text style={{ color: directorDark.muted, fontSize: 12, display: 'block', marginBottom: 6 }}>时间 / 天气 / 氛围</Text>
      <Select
        size="small"
        style={{ width: '100%', marginBottom: 6 }}
        value={environment.timeOfDay || 'day'}
        options={[
          { value: 'dawn', label: '清晨' },
          { value: 'day', label: '白天' },
          { value: 'dusk', label: '黄昏' },
          { value: 'night', label: '夜晚' },
        ]}
        onChange={(v) => applyEnvironmentLook(undefined, v, undefined)}
      />
      <Select
        size="small"
        style={{ width: '100%', marginBottom: 6 }}
        value={environment.weather || 'clear'}
        options={[
          { value: 'clear', label: '晴' },
          { value: 'cloudy', label: '阴' },
          { value: 'rain', label: '雨天' },
          { value: 'snow', label: '雪' },
          { value: 'fog', label: '雾' },
        ]}
        onChange={(v) => applyEnvironmentLook(v, undefined, undefined)}
      />
      <Select
        size="small"
        style={{ width: '100%', marginBottom: 10 }}
        value={environment.atmosphere || 'neutral'}
        options={[
          { value: 'neutral', label: '日常' },
          { value: 'tense', label: '紧张' },
          { value: 'romantic', label: '浪漫' },
          { value: 'oppressive', label: '压抑' },
          { value: 'joyful', label: '明快' },
          { value: 'melancholy', label: '伤感' },
        ]}
        onChange={(v) => applyEnvironmentLook(undefined, undefined, v)}
      />
      <Upload
        accept="image/*"
        showUploadList={false}
        beforeUpload={(file) => {
          void applySceneCanvasFile(file)
            .then(() => message.success('已贴到 3D 画布'))
            .catch((err: unknown) => message.error(err instanceof Error ? err.message : '贴图失败'));
          return false;
        }}
      >
        <Button size="small" block style={{ marginBottom: 10 }}>上传场景图片</Button>
      </Upload>
    </div>
  );
}

export function PropLibrary() {
  const addFromCatalog = useDirectorStore((s) => s.addFromCatalog);
  const [query, setQuery] = useState('');
  const q = query.trim().toLowerCase();
  const visible = useMemo(
    () => (q ? CATALOG.filter((item) => item.name.toLowerCase().includes(q) || item.id.includes(q)) : CATALOG),
    [q],
  );
  const groups = CATALOG_GROUPS.filter((group) => visible.some((item) => item.category === group.key));

  return (
    <div style={{ padding: 8 }}>
      <Input.Search
        allowClear
        size="small"
        placeholder="搜索道具"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        style={{ marginBottom: 8 }}
      />
      <Collapse
        size="small"
        defaultActiveKey={['furniture', 'shape']}
        items={groups.map((group) => ({
          key: group.key,
          label: `${group.label} (${visible.filter((item) => item.category === group.key).length})`,
          children: (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
              {visible
                .filter((item) => item.category === group.key)
                .map((item) => (
                  <CardButton key={item.id} name={item.name} onClick={() => addFromCatalog(item.id)} />
                ))}
            </div>
          ),
        }))}
      />
    </div>
  );
}

function CardButton({ name, note, onClick }: { name: string; note?: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        border: `1px solid ${directorDark.border}`,
        borderRadius: radius.item,
        background: '#1c1c32',
        color: directorDark.text,
        padding: '8px 6px',
        cursor: 'pointer',
        textAlign: 'left',
        fontSize: 12,
      }}
    >
      {name}
      {note && <div style={{ color: directorDark.muted, fontSize: 10, marginTop: 4 }}>{note}</div>}
    </button>
  );
}

export default function AssetLibrary({ section }: { section: 'characters' | 'scenes' | 'props' | 'assets' }) {
  if (section === 'characters') return <CharacterLibrary />;
  if (section === 'scenes') return <SceneLibrary />;
  if (section === 'props') return <PropLibrary />;
  return <MediaLibrary />;
}
