import { Button, Input, Space, Tooltip } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  HistoryOutlined,
  LoadingOutlined,
  RedoOutlined,
  SaveOutlined,
  SettingOutlined,
  UndoOutlined,
} from '@ant-design/icons';
import UserMenu from '../../components/UserMenu';
import { cinema } from '../../theme';
import { useDirectorStore } from '../store/useDirectorStore';
import { useSaveStatus } from '../saveStatus';
import ProjectSwitcher from './ProjectSwitcher';
import { message } from 'antd';

export default function ProjectTopBar({
  projectId,
  onProjectChanged,
  onOpenGenerate,
  onOpenSettings,
}: {
  projectId: string;
  onProjectChanged: (id: string, title: string) => void;
  onOpenGenerate: () => void;
  onOpenSettings: () => void;
  onOpenStage?: () => void;
}) {
  const phase = useSaveStatus((s) => s.phase);
  const saveError = useSaveStatus((s) => s.error);
  const persistNow = useDirectorStore((s) => s.persistNow);
  const undo = useDirectorStore((s) => s.undo);
  const redo = useDirectorStore((s) => s.redo);
  const historyPast = useDirectorStore((s) => s.historyPast);
  const historyFuture = useDirectorStore((s) => s.historyFuture);
  const projectName = useDirectorStore((s) => s.projectName);
  const locationName = useDirectorStore((s) => s.locationName);
  const sceneName = useDirectorStore((s) => s.sceneName);
  const setProjectMeta = useDirectorStore((s) => s.setProjectMeta);

  return (
    <div
      className="cinema-topbar"
      style={{
        height: 52,
        flexShrink: 0,
        background: cinema.panel,
        borderBottom: `1px solid ${cinema.line}`,
        display: 'flex',
        alignItems: 'center',
        padding: '0 14px',
        gap: 12,
      }}
    >
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: 8,
          background: `linear-gradient(135deg, ${cinema.gold}, #8a6a32)`,
          color: '#1a140c',
          fontWeight: 800,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 14,
        }}
      >
        导
      </div>
      <div style={{ minWidth: 240, display: 'flex', gap: 8, alignItems: 'center' }}>
        <MetaField
          label="项目"
          value={projectName}
          extra={<ProjectSwitcher projectId={projectId} onChanged={onProjectChanged} />}
          onChange={(v) => setProjectMeta({ projectName: v })}
        />
        <MetaField
          label="场景"
          value={locationName || sceneName}
          onChange={(v) => setProjectMeta({ locationName: v })}
        />
      </div>

      <SaveBadge phase={phase} error={saveError} onRetry={() => persistNow()} />

      <div style={{ flex: 1 }} />

      <Space size={6}>
        <Button size="small" icon={<UndoOutlined />} disabled={!historyPast.length} onClick={() => undo()}>
          撤销
        </Button>
        <Button size="small" icon={<RedoOutlined />} disabled={!historyFuture.length} onClick={() => redo()}>
          恢复
        </Button>
        <Button size="small" icon={<SaveOutlined />} onClick={() => { persistNow(); message.success('已保存'); }}>
          保存
        </Button>
        <Tooltip title="查看出片历史，生成中也可打开">
          <Button size="small" icon={<HistoryOutlined />} onClick={onOpenGenerate}>
            历史记录
          </Button>
        </Tooltip>
        <Button size="small" icon={<SettingOutlined />} onClick={onOpenSettings} />
        <div className="director-user">
          <UserMenu />
        </div>
      </Space>
    </div>
  );
}

function MetaField({
  label,
  value,
  onChange,
  extra,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  extra?: React.ReactNode;
}) {
  return (
    <div style={{ minWidth: 86 }}>
      <div style={{ fontSize: 10, letterSpacing: 1, color: cinema.gold, marginBottom: 2 }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <Input
          size="small"
          variant="borderless"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          style={{ color: cinema.text, padding: 0, height: 20, fontWeight: 600, maxWidth: 120 }}
        />
        {extra}
      </div>
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
      <span style={{ color: cinema.gold, fontSize: 12 }}>
        <LoadingOutlined /> 正在保存场景
      </span>
    );
  }
  if (phase === 'error') {
    return (
      <span style={{ color: cinema.danger, fontSize: 12, cursor: 'pointer' }} onClick={onRetry} title={error || ''}>
        <CloseCircleOutlined /> 场景未存上
      </span>
    );
  }
  return (
    <span style={{ color: cinema.ok, fontSize: 12 }}>
      <CheckCircleOutlined /> 场景已存
    </span>
  );
}
