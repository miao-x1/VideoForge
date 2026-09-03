import { useNavigate, useLocation } from 'react-router-dom';
import { Tooltip } from 'antd';
import { ClockCircleOutlined, VideoCameraOutlined } from '@ant-design/icons';
import { brand, colors, radius } from '../theme';

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();

  const isStudio = location.pathname === '/';
  const isHistory = location.pathname === '/history';

  const navItemStyle = (active: boolean): React.CSSProperties => ({
    width: 40,
    height: 40,
    borderRadius: radius.control,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    background: active ? brand.tint : 'transparent',
    color: active ? brand.primary : colors.sidebarMuted,
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
      {/* Logo */}
      <div
        style={{
          width: 40,
          height: 40,
          borderRadius: radius.control,
          background: brand.gradient,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          fontSize: 18,
          fontWeight: 'bold',
          marginBottom: 24,
        }}
      >
        V
      </div>

      {/* 导航 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <Tooltip title="创作工作台" placement="right">
          <div onClick={() => navigate('/')} style={navItemStyle(isStudio)}>
            <VideoCameraOutlined />
          </div>
        </Tooltip>
        <Tooltip title="历史视频" placement="right">
          <div onClick={() => navigate('/history')} style={navItemStyle(isHistory)}>
            <ClockCircleOutlined />
          </div>
        </Tooltip>
      </div>

      {/* 底部留空，UserMenu 由 Header 承载 */}
      <div style={{ flex: 1 }} />
    </div>
  );
}
