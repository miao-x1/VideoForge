import { useState } from 'react';
import { directorDark } from '../../theme';
import AssetLibrary from './AssetLibrary';
import SceneTree from './SceneTree';

const SECTIONS = [
  { key: 'characters', label: '角色' },
  { key: 'scenes', label: '场景' },
  { key: 'props', label: '道具' },
  { key: 'assets', label: '素材' },
] as const;

export default function LeftPanel() {
  const [section, setSection] = useState<(typeof SECTIONS)[number]['key']>('characters');

  return (
    <div
      style={{
        width: 300,
        flexShrink: 0,
        background: directorDark.surface,
        borderRight: `1px solid ${directorDark.border}`,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
      }}
    >
      <div style={{ display: 'flex', padding: 8, gap: 4, borderBottom: `1px solid ${directorDark.border}` }}>
        {SECTIONS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setSection(item.key)}
            style={{
              flex: 1,
              height: 28,
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              color: section === item.key ? '#fff' : directorDark.muted,
              background: section === item.key ? directorDark.accent : 'transparent',
              fontSize: 12,
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
        <AssetLibrary section={section} />
      </div>
      <div style={{ height: 180, borderTop: `1px solid ${directorDark.border}`, overflow: 'auto' }}>
        <div style={{ padding: '8px 10px', color: directorDark.muted, fontSize: 11 }}>当前镜头对象</div>
        <SceneTree embedded />
      </div>
    </div>
  );
}
