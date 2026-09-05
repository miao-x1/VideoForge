import { useNavigate, useLocation } from 'react-router-dom';
import { Tooltip } from 'antd';
import {
  FolderOpenOutlined, HistoryOutlined, HomeOutlined,
} from '@ant-design/icons';
import { colors, radius } from '../theme';

/**
 * 工作区视图键:
 * - flow 流程节点(由顶部流程条路由): 创意/方案/设定/剧本/分镜/Prompt/生成/成片
 * - resource 资源节点(由左侧导航路由): 素材库/生成记录
 */
export type NodeKey =
  | 'creative' | 'intent' | 'bible' | 'script' | 'storyboard' | 'prompt'
  | 'videos' | 'final'
  | 'assets' | 'versions';

/** 左侧导航只承载资源,流程步骤由顶部流程条承担(消除双导航重复) */
const NAV_ITEMS: { key: NodeKey; label: string; icon: React.ReactNode }[] = [
  { key: 'assets', label: '素材库', icon: <FolderOpenOutlined /> },
  { key: 'versions', label: '生成记录', icon: <HistoryOutlined /> },
];

interface Props {
  /** 当前工作区视图(高亮资源项) */
  active: NodeKey;
  /** 各资源是否可用(无内容则禁用) */
  available: Partial<Record<NodeKey, boolean>>;
  onSelect: (key: NodeKey) => void;
  /** 返回项目工作台 */
  onBackHome: () => void;
}

export default function NodeNav({ active, available, onSelect, onBackHome }: Props) {
  const navigate = useNavigate();
  const location = useLocation();

  const renderItem = (def: (typeof NAV_ITEMS)[number]) => {
    const isEnabled = available[def.key] ?? false;
    const isActive = active === def.key;
    return (
      <div
        key={def.key}
        onClick={() => isEnabled && onSelect(def.key)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '8px 12px',
          borderRadius: radius.control,
          cursor: isEnabled ? 'pointer' : 'not-allowed',
          background: isActive ? 'rgba(199, 184, 156, 0.14)' : 'transparent',
          color: !isEnabled
            ? 'rgba(244,241,234,0.22)'
            : isActive
              ? '#c7b89c'
              : 'rgba(244,241,234,0.62)',
          fontSize: 13,
          transition: 'all 0.2s',
          marginBottom: 2,
        }}
      >
        <span style={{ fontSize: 15 }}>{def.icon}</span>
        <span style={{ flex: 1 }}>{def.label}</span>
      </div>
    );
  };

  return (
    <div
      style={{
        width: 184,
        height: '100vh',
        background: colors.sidebar,
        display: 'flex',
        flexDirection: 'column',
        padding: '16px 12px',
        flexShrink: 0,
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: 6,
            border: '1px solid rgba(199, 184, 156, 0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#c7b89c',
            fontSize: 10,
            letterSpacing: '0.04em',
            fontWeight: 500,
          }}
        >
          VF
        </div>
        <span style={{ color: '#f4f1ea', fontWeight: 500, fontSize: 13, letterSpacing: '0.08em' }}>VIDEOFORGE</span>
      </div>

      {/* 返回工作台 */}
      <div
        onClick={onBackHome}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '8px 12px',
          borderRadius: radius.control,
          cursor: 'pointer',
          background: 'rgba(255,255,255,0.06)',
          color: 'rgba(255,255,255,0.8)',
          fontSize: 13,
          marginBottom: 16,
        }}
      >
        <HomeOutlined />
        <span>项目工作台</span>
      </div>

      {/* 资源导航 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <div
          style={{
            color: 'rgba(255,255,255,0.35)',
            fontSize: 11,
            padding: '0 12px 6px',
            letterSpacing: 1,
          }}
        >
          资源
        </div>
        {NAV_ITEMS.map(renderItem)}
      </div>

      {/* 底部:历史入口 */}
      <Tooltip title="历史视频" placement="right">
        <div
          onClick={() => navigate('/history')}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: 36,
            borderRadius: radius.control,
            cursor: 'pointer',
            background: location.pathname === '/history' ? 'rgba(199, 184, 156, 0.14)' : 'transparent',
            color: location.pathname === '/history' ? '#c7b89c' : 'rgba(244,241,234,0.62)',
            fontSize: 15,
          }}
        >
          <HistoryOutlined />
        </div>
      </Tooltip>
    </div>
  );
}
