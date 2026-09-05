import { useEffect, useState } from 'react';
import { ConfigProvider, Spin, theme, message } from 'antd';
import Sidebar from '../components/Sidebar';
import { useDirectorStore } from './store/useDirectorStore';
import AssetCenter from './components/AssetCenter';
import DirectorConsole from './components/DirectorConsole';
import AgentDock from './components/AgentDock';
import ShotTimeline from './components/ShotTimeline';
import Viewport from './components/Viewport';
import StudioOverlay from './components/StudioOverlay';
import ProjectTopBar from './components/ProjectTopBar';
import GenerationDrawer from './components/GenerationDrawer';
import OnboardingModal, { hasFinishedOnboarding, markOnboardingDone } from './components/OnboardingModal';
import AutoStageModal from './components/AutoStageModal';
import SettingsDrawer from './components/SettingsDrawer';
import { ensureDirectorProject, getDirectorProjectId } from './scope';
import { applyScopedLocalCaches, hydrateDirectorFromBackend } from './sync';
import { useGenerationRunner } from './generationRunner';
import { useAuth } from '../hooks/useAuth';
import { cinema } from '../theme';

export default function DirectorDeskPage() {
  const [hydrating, setHydrating] = useState(true);
  const [projectId, setProjectId] = useState(getDirectorProjectId());
  const [onboardOpen, setOnboardOpen] = useState(false);
  const [stageOpen, setStageOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const generateOpen = useGenerationRunner((s) => s.open);
  const setGenerateOpen = useGenerationRunner((s) => s.setOpen);
  const { user, loading: authLoading } = useAuth();

  const selectedId = useDirectorStore((s) => s.selectedId);
  const undo = useDirectorStore((s) => s.undo);
  const redo = useDirectorStore((s) => s.redo);
  const requestFocus = useDirectorStore((s) => s.requestFocus);
  const setTransformMode = useDirectorStore((s) => s.setTransformMode);
  const objects = useDirectorStore((s) => s.objects) ?? [];

  useEffect(() => {
    if (authLoading) return;
    message.config({ top: 72, duration: 1.4, maxCount: 2 });
    (async () => {
      try {
        const id = await ensureDirectorProject();
        setProjectId(id);
        applyScopedLocalCaches();
        await hydrateDirectorFromBackend();
      } catch {
        applyScopedLocalCaches();
        message.error('项目未就绪，保存和生成都会失败。请登录后刷新。');
      } finally {
        setHydrating(false);
        if (user?.id && !hasFinishedOnboarding(user.id)) {
          setOnboardOpen(true);
        }
      }
    })();
  }, [authLoading, user?.id]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) return;
      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key.toLowerCase() === 'z' && !e.shiftKey) {
        e.preventDefault();
        undo();
      } else if ((mod && e.key.toLowerCase() === 'y') || (mod && e.shiftKey && e.key.toLowerCase() === 'z')) {
        e.preventDefault();
        redo();
      } else if (!mod && e.key.toLowerCase() === 'f' && selectedId) {
        e.preventDefault();
        requestFocus();
      } else if (!mod && e.key.toLowerCase() === 'v') {
        e.preventDefault();
        setTransformMode('translate');
      } else if (!mod && e.key.toLowerCase() === 'r') {
        e.preventDefault();
        setTransformMode('rotate');
      } else if (!mod && e.key.toLowerCase() === 's') {
        e.preventDefault();
        setTransformMode('scale');
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [undo, redo, requestFocus, selectedId, setTransformMode]);

  const closeOnboard = () => {
    markOnboardingDone(user?.id || '');
    setOnboardOpen(false);
  };

  return (
    <div style={{ display: 'flex', height: '100vh', background: cinema.bg }}>
      <Sidebar />
      <ConfigProvider
        theme={{
          algorithm: theme.darkAlgorithm,
          token: {
            colorPrimary: cinema.gold,
            colorPrimaryHover: '#d4c7ae',
            colorBgContainer: cinema.raised,
            colorBgElevated: cinema.panel,
            colorBorder: '#3a3428',
            colorText: cinema.text,
          },
        }}
      >
        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
          <ProjectTopBar
            projectId={projectId}
            onProjectChanged={(id) => setProjectId(id)}
            onOpenGenerate={() => setGenerateOpen(true)}
            onOpenSettings={() => setSettingsOpen(true)}
          />
          <div style={{ flex: 1, display: 'flex', minHeight: 0, position: 'relative' }}>
            <AssetCenter />
            <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', position: 'relative', background: cinema.stage }}>
              <Viewport directorResetKey={0} />
              <StudioOverlay />
              {objects.length === 0 && !hydrating && (
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    pointerEvents: 'none',
                  }}
                >
                  <div
                    style={{
                      padding: '18px 22px',
                      borderRadius: 14,
                      background: 'rgba(11,10,15,0.72)',
                      color: cinema.text,
                      textAlign: 'center',
                      border: `1px solid ${cinema.line}`,
                    }}
                  >
                    <div style={{ fontWeight: 700, marginBottom: 6, letterSpacing: 1 }}>3D 摄影棚</div>
                    <div style={{ fontSize: 12, color: cinema.muted }}>资产入棚 → 摆场景 → 定镜头 → AI 生成</div>
                  </div>
                </div>
              )}
              <ShotTimeline />
              <AgentDock />
            </div>
            <DirectorConsole onOpenStage={() => setStageOpen(true)} />
            {hydrating && (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  background: 'rgba(11,10,15,0.55)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  zIndex: 8,
                }}
              >
                <Spin tip="正在打开项目…" />
              </div>
            )}
          </div>
        </div>
        <GenerationDrawer open={generateOpen} onClose={() => setGenerateOpen(false)} />
        <AutoStageModal open={stageOpen} onClose={() => setStageOpen(false)} />
        <SettingsDrawer open={settingsOpen} onClose={() => setSettingsOpen(false)} />
        <OnboardingModal open={onboardOpen} onClose={closeOnboard} />
        <style>{`
          .ant-message, .ant-message-notice, .ant-message-notice-content { pointer-events: none !important; }
          .director-header .ant-typography, .director-user .ant-typography, .director-user .ant-btn { color: #fff !important; }
          .cinema-chip {
            border: 1px solid rgba(232,196,120,0.22);
            background: rgba(232,196,120,0.10);
            color: #f4efe6;
            border-radius: 99px;
            padding: 4px 10px;
            font-size: 12px;
            cursor: pointer;
          }
          .cinema-chip:hover { border-color: #e8c478; }
          .cinema-topbar .ant-input { color: #f4efe6 !important; }
        `}</style>
      </ConfigProvider>
    </div>
  );
}
