import { Button, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useDirectorStore } from '../store/useDirectorStore';
import { directorDark } from '../../theme';

const { Text } = Typography;

export default function ShotTimelineBar() {
  const scenes = useDirectorStore((s) => s.scenes);
  const sceneId = useDirectorStore((s) => s.sceneId);
  const switchScene = useDirectorStore((s) => s.switchScene);
  const createShotScene = useDirectorStore((s) => s.createShotScene);
  const objects = useDirectorStore((s) => s.objects);
  const shotType = useDirectorStore((s) => s.shotType);
  const cameraMovement = useDirectorStore((s) => s.cameraMovement);
  const duration = useDirectorStore((s) => s.shotDuration ?? 4);
  const lead = objects.find((o) => o.characterId);

  return (
    <div
      style={{
        minHeight: 72,
        flexShrink: 0,
        borderTop: `1px solid ${directorDark.border}`,
        background: directorDark.surface,
        padding: '8px 12px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflowX: 'auto' }}>
        {scenes.map((scene, index) => {
          const active = scene.sceneId === sceneId;
          return (
            <button
              key={scene.sceneId}
              type="button"
              onClick={() => switchScene(scene.sceneId)}
              style={{
                flexShrink: 0,
                minWidth: 120,
                textAlign: 'left',
                padding: '8px 10px',
                borderRadius: 8,
                border: active ? `1px solid ${directorDark.accent}` : `1px solid ${directorDark.border}`,
                background: active ? 'rgba(102,126,234,0.16)' : '#121222',
                color: directorDark.text,
                cursor: 'pointer',
              }}
            >
              <div style={{ fontSize: 11, color: directorDark.accent }}>Shot {String(index + 1).padStart(2, '0')}</div>
              <div style={{ fontSize: 12, fontWeight: 600 }}>{scene.sceneName || `镜头 ${index + 1}`}</div>
              <div style={{ fontSize: 11, color: directorDark.muted }}>{scene.shotDuration ?? 4}s · {scene.shotType || '中景'}</div>
            </button>
          );
        })}
        <Button size="small" icon={<PlusOutlined />} onClick={() => createShotScene()}>
          新建镜头
        </Button>
      </div>
      <div style={{ marginTop: 6, color: directorDark.muted, fontSize: 11 }}>
        <Text style={{ color: directorDark.muted, fontSize: 11 }}>
          Camera · {shotType || 'medium shot'} · {cameraMovement || 'static'} · {duration}s
          {lead ? `　　角色动作 · ${lead.name} · ${lead.animation || lead.pose || 'stand'}` : ''}
        </Text>
      </div>
    </div>
  );
}
