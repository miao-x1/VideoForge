import { PlusOutlined } from '@ant-design/icons';
import { useDirectorStore } from '../store/useDirectorStore';
import { cinema } from '../../theme';
import { SHOT_SIZE_LABEL } from '../directing/look';

export default function ShotTimeline() {
  const scenes = useDirectorStore((s) => s.scenes) ?? [];
  const sceneId = useDirectorStore((s) => s.sceneId);
  const switchScene = useDirectorStore((s) => s.switchScene);
  const createShotScene = useDirectorStore((s) => s.createShotScene);
  const duplicateShotScene = useDirectorStore((s) => s.duplicateShotScene);

  return (
    <div
      style={{
        flexShrink: 0,
        borderTop: `1px solid ${cinema.line}`,
        background: cinema.panel,
        padding: '6px 12px',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        minHeight: 46,
      }}
    >
      <div style={{ fontSize: 11, letterSpacing: 1.2, color: cinema.gold, flexShrink: 0 }}>镜头</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, overflowX: 'auto', flex: 1, minWidth: 0 }}>
        {scenes.map((scene, index) => {
          const active = scene.sceneId === sceneId;
          const lead = scene.objects.find((o) => o.characterId);
          const cam = scene.cameras.find((c) => c.id === scene.activeCamera) ?? scene.cameras[0];
          return (
            <button
              key={scene.sceneId}
              type="button"
              onClick={() => switchScene(scene.sceneId)}
              style={{
                flexShrink: 0,
                height: 32,
                padding: '0 10px',
                borderRadius: 8,
                border: active ? `1px solid ${cinema.gold}` : `1px solid ${cinema.line}`,
                background: active ? cinema.goldDim : cinema.raised,
                color: cinema.text,
                cursor: 'pointer',
                fontSize: 12,
              }}
            >
              {String(index + 1).padStart(2, '0')} · {lead?.name || '空镜'} · {SHOT_SIZE_LABEL[cam?.shotSize ?? 'medium']} · {scene.shotDuration ?? 4}s
            </button>
          );
        })}
        <button
          type="button"
          onClick={() => createShotScene()}
          style={{
            flexShrink: 0,
            height: 32,
            width: 32,
            borderRadius: 8,
            border: `1px dashed ${cinema.line}`,
            background: 'transparent',
            color: cinema.muted,
            cursor: 'pointer',
          }}
        >
          <PlusOutlined />
        </button>
      </div>
      <button
        type="button"
        onClick={() => duplicateShotScene()}
        style={{
          flexShrink: 0,
          border: 0,
          background: 'transparent',
          color: cinema.muted,
          cursor: 'pointer',
          fontSize: 12,
        }}
      >
        复制
      </button>
    </div>
  );
}
