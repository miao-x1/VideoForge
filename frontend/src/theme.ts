/**
 * VideoForge 统一设计令牌(Design Tokens)
 * 所有颜色/圆角/间距/阴影的唯一来源,禁止在组件中硬编码。
 */
import type { ThemeConfig } from 'antd';

/** 品牌色 */
export const brand = {
  /** 主品牌色(紫罗兰):按钮/链接/选中态/焦点 */
  primary: '#667eea',
  /** 品牌渐变终点(深紫):Logo/装饰渐变 */
  gradientEnd: '#764ba2',
  /** 品牌渐变 */
  gradient: 'linear-gradient(135deg, #667eea, #764ba2)',
  /** 品牌色浅背景(选中导航底色等) */
  tint: 'rgba(102,126,234,0.15)',
};

/** 中性色 */
export const colors = {
  /** 页面背景 */
  bg: '#f0f2f5',
  /** 卡片/面板背景 */
  surface: '#ffffff',
  /** 分隔线 */
  border: '#e8e8e8',
  /** 侧边栏深色底 */
  sidebar: '#1a1a2e',
  /** 侧边栏未激活图标 */
  sidebarMuted: '#6c6c8c',
  /** 次级文字 */
  textMuted: '#666666',
};

/** 圆角(卡片 12 / 控件 8 / 小元素 6) */
export const radius = { card: 12, control: 8, item: 6 } as const;

/** 语义强调色(提示框/徽标底色,与 antd 调色板对齐) */
export const accents = {
  /** 警示(如 Hook 提示) */
  warning: { bg: '#fffbe6', border: '#ffe58f' },
  /** 成功(如结尾提示) */
  success: { bg: '#f6ffed', border: '#b7eb8f' },
  /** 信息(如画面描述) */
  info: { bg: '#e6f7ff', border: '#91d5ff' },
  /** 品牌/模型相关(Prompt/模型信息) */
  brand: { bg: '#f9f0ff', border: '#d3adf7', text: '#722ed1' },
  /** 错误(如 Negative Prompt) */
  error: { bg: '#fff1f0', border: '#ffa39e' },
  /** 中性底(列表项/折叠内容) */
  neutral: { bg: '#fafafa', border: '#f0f0f0' },
} as const;

/** 统一提示框样式(语义强调信息的浅底容器) */
export const calloutStyle = (accent: { bg: string; border: string }): React.CSSProperties => ({
  padding: '6px 10px',
  background: accent.bg,
  border: `1px solid ${accent.border}`,
  borderRadius: radius.item,
});

/** 统一卡片容器样式(中央工作区/右侧面板的白色圆角容器) */
export const cardStyle: React.CSSProperties = {
  background: colors.surface,
  borderRadius: radius.card,
  padding: 20,
};

/** 面板标题行(图标 + 标题 + 右侧徽标) */
export const panelTitleStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  marginBottom: 16,
};

/** Ant Design 全局主题:统一所有组件的主色/圆角/字体 */
export const antdTheme: ThemeConfig = {
  token: {
    colorPrimary: brand.primary,
    colorLink: brand.primary,
    colorInfo: brand.primary,
    borderRadius: radius.control,
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif",
  },
  components: {
    Button: { borderRadius: radius.control },
    Card: { borderRadiusLG: radius.card },
  },
};
