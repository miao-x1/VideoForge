import { useState } from 'react';
import { cinema } from '../../theme';
import AssetLibrary from './AssetLibrary';
import ActionLibrary from './ActionLibrary';
import SceneTree from './SceneTree';

const SECTIONS = [
  { key: 'characters', label: '角色' },
  { key: 'scenes', label: '场景' },
  { key: 'props', label: '道具' },
  { key: 'actions', label: '动作' },
] as const;

export default function AssetCenter() {
  const [section, setSection] = useState<(typeof SECTIONS)[number]['key']>('characters');

  return (
    <div
      style={{
        width: 248,
        flexShrink: 0,
        background: cinema.panel,
        borderRight: `1px solid ${cinema.line}`,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
      }}
    >
      <div style={{ padding: '12px 12px 8px' }}>
        <div style={{ fontSize: 11, letterSpacing: 1.4, color: cinema.gold }}>导演资产库</div>
        <div style={{ fontSize: 12, color: cinema.muted, marginTop: 2 }}>角色 · 场景 · 道具 · 动作</div>
      </div>
      <div style={{ display: 'flex', padding: '0 8px 8px', gap: 4 }}>
        {SECTIONS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setSection(item.key)}
            style={{
              flex: 1,
              height: 28,
              border: `1px solid ${section === item.key ? cinema.gold : 'transparent'}`,
              borderRadius: 6,
              cursor: 'pointer',
              color: section === item.key ? cinema.gold : cinema.muted,
              background: section === item.key ? cinema.goldDim : 'transparent',
              fontSize: 12,
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
        {section === 'actions' ? (
          <ActionLibrary />
        ) : (
          <AssetLibrary section={section === 'characters' ? 'characters' : section === 'scenes' ? 'scenes' : 'props'} />
        )}
      </div>
      <div style={{ height: 96, borderTop: `1px solid ${cinema.line}`, overflow: 'auto' }}>
        <div style={{ padding: '8px 10px', color: cinema.muted, fontSize: 11 }}>当前摄影棚对象</div>
        <SceneTree embedded />
      </div>
    </div>
  );
}
