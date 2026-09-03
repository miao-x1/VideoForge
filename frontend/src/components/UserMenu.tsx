import { Dropdown, Space, Typography, Button } from 'antd';
import { UserOutlined, LogoutOutlined, HistoryOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { MenuProps } from 'antd';
import { useAuth } from '../hooks/useAuth';

export default function UserMenu() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const items: MenuProps['items'] = [
    {
      key: 'history',
      icon: <HistoryOutlined />,
      label: '我的视频',
      onClick: () => navigate('/history'),
    },
    { type: 'divider' },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: logout,
    },
  ];

  if (!user) return null;

  return (
    <Dropdown menu={{ items }} placement="bottomRight">
      <Button type="text" icon={<UserOutlined />}>
        <Space>
          <Typography.Text>{user.display_name || user.email}</Typography.Text>
        </Space>
      </Button>
    </Dropdown>
  );
}
