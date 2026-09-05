import { directorDark } from '../../theme';
import Inspector from './Inspector';

export default function RightDock() {
  return (
    <div
      style={{
        width: 320,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        background: directorDark.surface,
        borderLeft: `1px solid ${directorDark.border}`,
      }}
    >
      <div style={{ padding: '10px 12px', color: directorDark.text, fontWeight: 600, borderBottom: `1px solid ${directorDark.border}` }}>
        属性
      </div>
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
        <Inspector embedded dark />
      </div>
    </div>
  );
}
