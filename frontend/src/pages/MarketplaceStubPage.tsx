import { Button, Result } from 'antd';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import UserMenu from '../components/UserMenu';
import { colors } from '../theme';

export default function MarketplaceStubPage() {
  const navigate = useNavigate();
  return (
    <div style={{ display: 'flex', height: '100vh', background: colors.bg }}>
      <Sidebar />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ height: 56, background: colors.surface, borderBottom: `1px solid ${colors.border}`, display: 'flex', justifyContent: 'flex-end', alignItems: 'center', padding: '0 16px' }}>
          <UserMenu />
        </div>
        <Result
          status="info"
          title="角色市场尚未开放"
          subTitle="已预留 Community / Marketplace 数据结构（listed / visibility / price）。这一阶段只做角色生产系统，不开发商城。"
          extra={<Button type="primary" onClick={() => navigate('/director')}>返回导演台</Button>}
        />
      </div>
    </div>
  );
}
