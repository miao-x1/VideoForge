import { Button, Dropdown, Space, Tag, Typography } from 'antd';
import {
  CameraOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  RedoOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  UndoOutlined,
} from '@ant-design/icons';
import UserMenu from '../../components/UserMenu';
import { directorDark } from '../../theme';
import { useDirectorStore } from '../store/useDirectorStore';
import { useSaveStatus } from '../saveStatus';
import { useGenerationRunner } from '../generationRunner';
import { sendCompositionToCanvas } from '../workspace';
import ProjectSwitcher from './ProjectSwitcher';
import type { AspectRatio, ViewMode } from '../types';
import { message } from 'antd';

const { Text } = Typography;

export default function DirectorHeader({
  projectId,
  onProjectChanged,
  onOpenGenerate,
}: {
  projectId: string;
  onProjectChanged: (id: string, title: string) => void;
  onOpenGenerate: () => void;
}) {
  const phase = useSaveStatus((s) => s.phase);
  const saveError = useSaveStatus((s) => s.error);
  const persistNow = useDirectorStore((s) => s.persistNow);
  const undo = useDirectorStore((s) => s.undo);
  const redo = useDirectorStore((s) => s.redo);
  const historyPast = useDirectorStore((s) => s.historyPast);
  const historyFuture = useDirectorStore((s) => s.historyFuture);
  const selectedId = useDirectorStore((s) => s.selectedId);
  const objects = useDirectorStore((s) => s.objects);
  const cameras = useDirectorStore((s) => s.cameras);
  const sceneName = useDirectorStore((s) => s.sceneName);
  const viewMode = useDirectorStore((s) => s.viewMode);
  const aspectRatio = useDirectorStore((s) => s.aspectRatio);
  const environment = useDirectorStore((s) => s.environment);
  const setViewMode = useDirectorStore((s) => s.setViewMode);
  const setAspectRatio = useDirectorStore((s) => s.setAspectRatio);
  const setEnvironment = useDirectorStore((s) => s.setEnvironment);
  const running = useGenerationRunner((s) => s.running);
  const generate = useGenerationRunner((s) => s.generate);

  const selected = objects.find((o) => o.id === selectedId);
  const camera = cameras.find((c) => c.id === selectedId);

  const preview = async () => {
    try {
      await sendCompositionToCanvas();
      message.success('已保存当前构图，可作为生成参考');
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : '预览失败，请等 3D 视口就绪');
    }
  };

  return (
    <div
      style={{
        height: 52,
        flexShrink: 0,
        background: directorDark.surface,
        borderBottom: `1px solid ${directorDark.border}`,
        display: 'flex',
        alignItems: 'center',
        padding: '0 12px',
        gap: 10,
      }}
    >
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: 8,
          border: '1px solid rgba(199, 184, 156, 0.35)',
          color: '#c7b89c',
          fontWeight: 500,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        V
      </div>
      <Text style={{ color: directorDark.text, fontWeight: 600 }}>导演台</Text>
      <ProjectSwitcher projectId={projectId} onChanged={onProjectChanged} />
      <SaveBadge
        phase={phase}
        error={saveError}
        onRetry={() => persistNow()}
      />
      <Button size="small" icon={<UndoOutlined />} disabled={!historyPast.length} onClick={() => undo()}>
        撤销
      </Button>
      <Button size="small" icon={<RedoOutlined />} disabled={!historyFuture.length} onClick={() => redo()}>
        恢复
      </Button>

      <div
        style={{
          flex: 1,
          minWidth: 0,
          display: 'flex',
          justifyContent: 'center',
          gap: 8,
          color: directorDark.muted,
          fontSize: 12,
        }}
      >
        <SelectionChip label="角色" value={selected?.characterId ? selected.name : '未选中'} active={!!selected?.characterId} />
        <SelectionChip label="场景" value={sceneName || '镜头 1'} active />
        <SelectionChip label="镜头" value={sceneName || 'Shot 01'} active />
        {camera && <SelectionChip label="机位" value={camera.name} active />}
      </div>

      <Space size={8}>
        <Button size="small" icon={<CameraOutlined />} onClick={() => void preview()}>
          预览
        </Button>
        <Dropdown
          menu={{
            items: [
              { key: 'image', label: '生成图片', onClick: () => void generate('image') },
              { key: 'video', label: '生成视频', onClick: () => void generate('video') },
              { key: 'history', label: '查看历史版本', onClick: onOpenGenerate },
            ],
          }}
        >
          <Button type="primary" size="small" icon={<ThunderboltOutlined />} loading={running}>
            生成
          </Button>
        </Dropdown>
        <Dropdown
          menu={{
            items: [
              {
                key: 'ar',
                label: `画幅 ${aspectRatio}`,
                children: (['9:16', '16:9', '1:1'] as AspectRatio[]).map((v) => ({
                  key: v,
                  label: v,
                  onClick: () => setAspectRatio(v),
                })),
              },
              {
                key: 'view',
                label: viewMode === 'director' ? '导演视角' : '机位视角',
                children: [
                  { key: 'director', label: '导演视角', onClick: () => setViewMode('director' as ViewMode) },
                  { key: 'shot', label: '机位视角', onClick: () => setViewMode('shot' as ViewMode) },
                ],
              },
              {
                key: 'grid',
                label: environment.showGrid ? '隐藏网格' : '显示网格',
                onClick: () => setEnvironment({ showGrid: !environment.showGrid }),
              },
            ],
          }}
        >
          <Button size="small" icon={<SettingOutlined />} />
        </Dropdown>
        <div className="director-user">
          <UserMenu />
        </div>
      </Space>
    </div>
  );
}

function SaveBadge({
  phase,
  error,
  onRetry,
}: {
  phase: 'saved' | 'saving' | 'error';
  error: string | null;
  onRetry: () => void;
}) {
  if (phase === 'saving') {
    return (
      <Tag icon={<LoadingOutlined />} color="processing">
        正在保存
      </Tag>
    );
  }
  if (phase === 'error') {
    return (
      <Tag
        icon={<CloseCircleOutlined />}
        color="error"
        style={{ cursor: 'pointer' }}
        onClick={onRetry}
        title={error || '保存失败，点击重试'}
      >
        保存失败
      </Tag>
    );
  }
  return (
    <Tag icon={<CheckCircleOutlined />} color="success">
      已保存
    </Tag>
  );
}

function SelectionChip({ label, value, active }: { label: string; value: string; active?: boolean }) {
  return (
    <span
      style={{
        padding: '2px 8px',
        borderRadius: 99,
        background: active ? 'rgba(102,126,234,0.16)' : '#1a1a2c',
        color: active ? directorDark.text : directorDark.muted,
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        maxWidth: 160,
      }}
    >
      {label}：{value}
    </span>
  );
}
