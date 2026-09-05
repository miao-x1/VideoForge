/**
 * VideoForge 设计令牌
 * 高级简约：墨色、暖纸、细线。不用紫渐变，也不堆装饰。
 */
import type { ThemeConfig } from 'antd';

export const brand = {
  primary: '#1c1b19',
  accent: '#8f7350',
  gradientEnd: '#3a3530',
  gradient: 'linear-gradient(180deg, #161513 0%, #1c1b19 100%)',
  tint: 'rgba(28, 27, 25, 0.06)',
};

export const directorDark = {
  bg: '#0e0d0b',
  surface: '#161513',
  panel: '#181714',
  border: '#2c2924',
  text: '#f4f1ea',
  muted: '#8a8680',
  accent: '#8f7350',
} as const;

export const cinema = {
  bg: '#0e0d0b',
  stage: '#12110f',
  panel: '#161513',
  raised: '#1c1b18',
  line: 'rgba(199, 184, 156, 0.16)',
  gold: '#c7b89c',
  goldDim: 'rgba(199, 184, 156, 0.12)',
  text: '#f4f1ea',
  muted: '#8a8680',
  danger: '#c47a6e',
  ok: '#7d9a7c',
} as const;

export const colors = {
  bg: '#f3f1ec',
  surface: '#fffcf7',
  border: '#e6e1d8',
  sidebar: '#141311',
  sidebarMuted: '#8a8680',
  textMuted: '#7a766f',
};

export const radius = { card: 10, control: 6, item: 4 } as const;

export const accents = {
  warning: { bg: '#faf6ee', border: '#e6d7b8' },
  success: { bg: '#f3f6f2', border: '#c9d6c6' },
  info: { bg: '#f4f3f0', border: '#ddd8ce' },
  brand: { bg: '#f7f3ec', border: '#ddd2c0', text: '#8f7350' },
  error: { bg: '#faf4f3', border: '#e4c8c4' },
  neutral: { bg: '#f7f5f1', border: '#ebe6dc' },
} as const;

export const calloutStyle = (accent: { bg: string; border: string }): React.CSSProperties => ({
  padding: '8px 12px',
  background: accent.bg,
  border: `1px solid ${accent.border}`,
  borderRadius: radius.item,
});

export const cardStyle: React.CSSProperties = {
  background: colors.surface,
  borderRadius: radius.card,
  padding: 24,
  border: `1px solid ${colors.border}`,
  boxShadow: 'none',
};

export const panelTitleStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  marginBottom: 16,
};

export const antdTheme: ThemeConfig = {
  token: {
    colorPrimary: brand.primary,
    colorLink: brand.accent,
    colorInfo: brand.accent,
    colorBgLayout: colors.bg,
    colorBgContainer: colors.surface,
    colorBorder: colors.border,
    colorText: '#1c1b19',
    colorTextSecondary: colors.textMuted,
    borderRadius: radius.control,
    fontFamily:
      "'PingFang SC', 'Hiragino Sans GB', 'Noto Serif SC', 'Songti SC', 'Microsoft YaHei', -apple-system, BlinkMacSystemFont, sans-serif",
    controlHeight: 36,
  },
  components: {
    Button: { borderRadius: radius.control, primaryShadow: 'none' },
    Card: { borderRadiusLG: radius.card, boxShadowTertiary: 'none' },
    Input: { borderRadius: radius.control },
    Tag: { borderRadiusSM: 4 },
  },
};
