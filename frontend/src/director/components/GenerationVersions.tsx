import { Button, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { mediaUrl } from '../../api/client';
import { fetchGenerationHistory, restoreGeneration, type GenerationVersion } from '../generationApi';
import { useDirectorStore } from '../store/useDirectorStore';

const { Text } = Typography;

function formatTime(ts?: number): string {
  if (!ts) return '';
  const d = new Date(ts * 1000);
  if (Number.isNaN(d.getTime())) return '';
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes()
    .toString()
    .padStart(2, '0')}`;
}

export default function GenerationVersions({ dark = false }: { dark?: boolean }) {
  const sceneId = useDirectorStore((s) => s.sceneId);
  const currentId = useDirectorStore((s) => s.generationId);
  const updateShotMeta = useDirectorStore((s) => s.updateShotMeta);
  const [items, setItems] = useState<GenerationVersion[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!sceneId) {
      setItems([]);
      return;
    }
    setLoading(true);
    fetchGenerationHistory(sceneId)
      .then((rows) => {
        if (!cancelled) setItems(rows);
      })
      .catch(() => {
        if (!cancelled) setItems([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sceneId, currentId]);

  const apply = (row: GenerationVersion) => {
    updateShotMeta({
      generationId: row.generation_id,
      imageUrl: row.kind === 'image' ? row.url || null : undefined,
      videoUrl: row.kind === 'video' ? row.url || null : undefined,
    });
  };

  const onRestore = async (row: GenerationVersion) => {
    const restored = await restoreGeneration(row.generation_id);
    apply(restored);
  };

  if (!items.length && !loading) {
    return (
      <div style={{ marginTop: 12 }}>
        <Text type="secondary" style={{ fontSize: 12, color: dark ? '#8c8c8c' : undefined }}>
          生成版本
        </Text>
        <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 6 }}>还没有生成记录</div>
      </div>
    );
  }

  return (
    <div style={{ marginTop: 12 }}>
      <Text type="secondary" style={{ fontSize: 12, color: dark ? '#8c8c8c' : undefined }}>
        生成版本
      </Text>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
        {items.map((row) => {
          const current = row.generation_id === currentId;
          const preview = row.url ? mediaUrl(row.url) : '';
          return (
            <div
              key={row.generation_id}
              style={{
                border: current ? '1px solid #c7b89c' : '1px solid #2c2924',
                borderRadius: 8,
                padding: 8,
                background: current ? 'rgba(199,184,156,0.1)' : 'transparent',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <Text style={{ fontSize: 12, color: dark ? '#f0f0f0' : undefined }}>
                  版本{row.version || row.version_number || 1}
                  {current ? '  ✓ 当前' : ''}
                </Text>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {formatTime(row.created_at)}
                </Text>
              </div>
              {preview && row.kind === 'image' && (
                <img
                  src={preview}
                  alt={`版本${row.version}`}
                  style={{ width: '100%', borderRadius: 6, marginTop: 6, display: 'block' }}
                />
              )}
              {preview && row.kind === 'video' && (
                <video src={preview} controls style={{ width: '100%', marginTop: 6, borderRadius: 6 }} />
              )}
              <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                <Button size="small" onClick={() => apply(row)}>
                  查看
                </Button>
                {!current && row.status === 'completed' && (
                  <Button size="small" type="primary" onClick={() => onRestore(row)}>
                    设为当前版本
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
