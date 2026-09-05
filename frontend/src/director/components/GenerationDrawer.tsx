import { useEffect, useState } from 'react';
import { Button, Drawer, Progress, Typography } from 'antd';
import { CheckCircleOutlined, ClockCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { cinema, directorDark } from '../../theme';
import { estimateGenProgress, useGenerationRunner } from '../generationRunner';
import GenerationVersions from './GenerationVersions';
import { mediaUrl } from '../../api/client';

const { Text } = Typography;

export default function GenerationDrawer({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const running = useGenerationRunner((s) => s.running);
  const kind = useGenerationRunner((s) => s.kind);
  const steps = useGenerationRunner((s) => s.steps);
  const error = useGenerationRunner((s) => s.error);
  const last = useGenerationRunner((s) => s.lastVersion);
  const generate = useGenerationRunner((s) => s.generate);
  const startedAt = useGenerationRunner((s) => s.startedAt);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!running || !startedAt) {
      setElapsed(0);
      return;
    }
    const tick = () => setElapsed(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)));
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [running, startedAt]);

  return (
    <Drawer
      title="历史记录"
      open={open}
      onClose={onClose}
      width={380}
      styles={{ body: { background: directorDark.surface, color: directorDark.text } }}
    >
      <div style={{ color: directorDark.muted, fontSize: 12, marginBottom: 16 }}>
        出片请用下方「生成视频」。这里只看历史和结果。
      </div>

      {(running || steps.length > 0) && (
        <div style={{ marginBottom: 16 }}>
          <Text style={{ color: directorDark.text, fontWeight: 600 }}>
            {running ? '正在生成' : error ? '生成失败' : '已完成'}
          </Text>
          {running && (
            <div style={{ marginTop: 10 }}>
              <Progress
                percent={estimateGenProgress(elapsed)}
                status="active"
                strokeColor={cinema.gold}
                trailColor="rgba(199,184,156,0.12)"
                strokeWidth={10}
              />
              <div style={{ color: cinema.gold, fontSize: 12 }}>
                已等 {Math.floor(elapsed / 60) > 0 ? `${Math.floor(elapsed / 60)}:${(elapsed % 60).toString().padStart(2, '0')}` : `${elapsed}s`} · 通常 2–4 分钟
              </div>
            </div>
          )}
          <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {steps.map((step) => (
              <div key={step.key} style={{ display: 'flex', gap: 8, alignItems: 'center', color: directorDark.text }}>
                {step.status === 'done' && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
                {step.status === 'active' && <ClockCircleOutlined style={{ color: '#c7b89c' }} />}
                {step.status === 'error' && <CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
                {step.status === 'pending' && <ClockCircleOutlined style={{ color: directorDark.muted }} />}
                <span>{step.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div
          style={{
            marginBottom: 16,
            padding: 10,
            borderRadius: 8,
            border: '1px solid #a61d24',
            background: 'rgba(255,77,79,0.08)',
          }}
        >
          <div style={{ color: '#ffccc7', fontSize: 12, marginBottom: 8 }}>{error}</div>
          <Button size="small" onClick={() => void generate(kind || 'image')}>
            重试
          </Button>
        </div>
      )}

      {last?.url && last.kind === 'image' && (
        <img src={mediaUrl(last.url)} alt="最新生成" style={{ width: '100%', borderRadius: 8, marginBottom: 16 }} />
      )}
      {last?.url && last.kind === 'video' && (
        <video src={mediaUrl(last.url)} controls style={{ width: '100%', borderRadius: 8, marginBottom: 16 }} />
      )}

      <GenerationVersions dark />
    </Drawer>
  );
}
