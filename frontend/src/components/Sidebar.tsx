import { useNavigate, useLocation } from 'react-router-dom';
import { Tooltip } from 'antd';
import { HistoryOutlined, VideoCameraOutlined } from '@ant-design/icons';
import { colors, radius } from '../theme';

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();

  const isHistory = location.pathname === '/history';
  const isDirector = location.pathname === '/director' || location.pathname === '/';

  const navItemStyle = (active: boolean): React.CSSProperties => ({
    width: 40,
    height: 40,
    borderRadius: radius.control,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    background: active ? 'rgba(199, 184, 156, 0.14)' : 'transparent',
    color: active ? '#c7b89c' : colors.sidebarMuted,
    fontSize: 18,
    transition: 'all 0.2s',
  });

  return (
    <div
      style={{
        width: 64,
        height: '100vh',
        background: colors.sidebar,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '16px 0',
        flexShrink: 0,
      }}
    >
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: 8,
          border: '1px solid rgba(199, 184, 156, 0.35)',
          background: 'transparent',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#c7b89c',
          fontSize: 13,
          letterSpacing: '0.04em',
          fontWeight: 500,
          marginBottom: 28,
        }}
      >
        VF
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <Tooltip title="导演台" placement="right">
          <div onClick={() => navigate('/director')} style={navItemStyle(isDirector)}>
            <VideoCameraOutlined />
          </div>
        </Tooltip>
        <Tooltip title="历史作品" placement="right">
          <div onClick={() => navigate('/history')} style={navItemStyle(isHistory)}>
            <HistoryOutlined />
          </div>
        </Tooltip>
      </div>
      <div style={{ flex: 1 }} />
    </div>
  );
}
