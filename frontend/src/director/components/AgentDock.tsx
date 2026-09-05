import { useEffect, useMemo, useState } from 'react';
import { Button, Input, Progress, Select, Upload, message } from 'antd';
import { PictureOutlined, SendOutlined } from '@ant-design/icons';
import { billingApi, mediaUrl, type BillingStatus } from '../../api/client';
import { cinema } from '../../theme';
import { useAgentStore } from '../agent/useAgentStore';
import { estimateGenProgress, useGenerationRunner } from '../generationRunner';
import { applySceneCanvasFile } from '../sceneCanvas';
import { captureScene } from '../sceneApi';
import { useDirectorStore } from '../store/useDirectorStore';
import type { AspectRatio } from '../types';

function formatElapsed(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m > 0 ? `${m}:${s.toString().padStart(2, '0')}` : `${s}s`;
}

function asThumb(url: string): string {
  if (url.startsWith('data:') || url.startsWith('blob:') || url.startsWith('http')) return url;
  return mediaUrl(url);
}

function lastStatus(
  messages: ReturnType<typeof useAgentStore.getState>['messages'],
  running: boolean,
): string | null {
  const agent = [...messages].reverse().find((m) => m.role === 'agent');
  if (!agent) return running ? '正在理解当前镜头…' : null;
  const step = [...agent.steps].reverse().find((s) => s.text);
  if (step?.text) return step.text.split('\n')[0];
  if (agent.text) return agent.text.split('\n')[0];
  return running ? '正在理解当前镜头…' : null;
}

export default function AgentDock() {
  const running = useAgentStore((s) => s.running);
  const send = useAgentStore((s) => s.send);
  const genRunning = useGenerationRunner((s) => s.running);
  const genError = useGenerationRunner((s) => s.error);
  const generateVideo = useGenerationRunner((s) => s.generate);
  const resumeIfNeeded = useGenerationRunner((s) => s.resumeIfNeeded);
  const startedAt = useGenerationRunner((s) => s.startedAt);
  const busy = running || genRunning;
  const [elapsed, setElapsed] = useState(0);
  const messages = useAgentStore((s) => s.messages);
  const pendingConfirm = useAgentStore((s) => s.pendingConfirm);
  const confirmPending = useAgentStore((s) => s.confirmPending);
  const compositionUrl = useDirectorStore((s) => s.compositionUrl);
  const imageUrl = useDirectorStore((s) => s.imageUrl);
  const videoUrl = useDirectorStore((s) => s.videoUrl);
  const backdropUrl = useDirectorStore((s) => s.environment?.backdropUrl);
  const shotDuration = useDirectorStore((s) => s.shotDuration);
  const aspectRatio = useDirectorStore((s) => s.aspectRatio);
  const setAspectRatio = useDirectorStore((s) => s.setAspectRatio);
  const updateShotMeta = useDirectorStore((s) => s.updateShotMeta);

  const [text, setText] = useState('');
  const [uploads, setUploads] = useState<string[]>([]);
  const [billing, setBilling] = useState<BillingStatus | null>(null);

  useEffect(() => {
    if (!localStorage.getItem('vf_token')) return;
    billingApi.status().then(setBilling).catch(() => setBilling(null));
    void resumeIfNeeded();
  }, [resumeIfNeeded]);

  useEffect(() => {
    if (!genRunning || !startedAt) {
      setElapsed(0);
      return;
    }
    const tick = () => setElapsed(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)));
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [genRunning, startedAt]);

  const shotRef = imageUrl || compositionUrl || backdropUrl || null;
  const attachments = useMemo(() => {
    const urls = [shotRef, ...uploads].filter((u): u is string => Boolean(u));
    return [...new Set(urls)];
  }, [shotRef, uploads]);

  const status = lastStatus(messages, running);

  const ensureShotRef = async () => {
    const stored = (imageUrl || compositionUrl || backdropUrl || '').split('?')[0];
    if (stored && !stored.startsWith('data:')) return stored;
    try {
      const { sendCompositionToCanvas } = await import('../workspace');
      return await sendCompositionToCanvas();
    } catch {
      const shot = await captureScene();
      return shot.dataUrl;
    }
  };

  const startVideo = async () => {
    const brief = text.trim();
    if (brief) updateShotMeta({ shotDescription: brief });
    try {
      await ensureShotRef();
    } catch {
      message.warning('还没有镜头参考，将先按文字出片。');
    }
    await generateVideo('video');
  };

  const submit = async () => {
    const next = text.trim();
    if (!next) {
      await startVideo();
      return;
    }
    setText('');
    let refs = attachments.filter((url) => url && !url.startsWith('data:')).map((url) => url.split('?')[0]);
    if (!refs.length) {
      try {
        refs = [await ensureShotRef()];
      } catch {
        message.warning('还没有镜头参考，将只按文字出片。');
      }
    }
    void send(next, false, {
      attachments: refs,
      duration: shotDuration ?? 5,
      aspectRatio,
    });
  };

  return (
    <div
      style={{
        flexShrink: 0,
        background: cinema.panel,
        borderTop: `1px solid ${cinema.line}`,
        padding: '8px 12px 10px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minHeight: 40 }}>
        {shotRef ? <Thumb src={shotRef} label="镜头" /> : <EmptyChip>自动截取</EmptyChip>}
        {backdropUrl && backdropUrl !== shotRef && <Thumb src={backdropUrl} label="场景" />}
        {uploads.filter((u) => u !== shotRef && u !== backdropUrl).map((url) => (
          <Thumb
            key={url.slice(0, 48)}
            src={url}
            label="图"
            onRemove={() => setUploads((prev) => prev.filter((item) => item !== url))}
          />
        ))}
        <Upload
          accept="image/*"
          showUploadList={false}
          beforeUpload={(file) => {
            void applySceneCanvasFile(file)
              .then(() => {
                const next = useDirectorStore.getState().environment.backdropUrl
                  || useDirectorStore.getState().compositionUrl;
                if (next && !next.startsWith('data:')) {
                  setUploads((prev) => (prev.includes(next) ? prev : [...prev, next]));
                }
                message.success('场景照片已加入对话');
              })
              .catch((err: unknown) => message.error(err instanceof Error ? err.message : '上传失败'));
            return false;
          }}
        >
          <button type="button" className="cinema-chip">
            <PictureOutlined /> 场景照片
          </button>
        </Upload>
        <Select
          size="small"
          style={{ width: 78 }}
          value={shotDuration ?? 5}
          options={[4, 5, 6, 8, 10].map((sec) => ({ value: sec, label: `${sec}s` }))}
          onChange={(sec: number) => updateShotMeta({ shotDuration: sec })}
        />
        <Select
          size="small"
          style={{ width: 92 }}
          value={aspectRatio}
          options={[
            { value: '9:16', label: '9:16' },
            { value: '16:9', label: '16:9' },
            { value: '1:1', label: '1:1' },
          ]}
          onChange={(v: AspectRatio) => setAspectRatio(v)}
        />
        {billing && (
          <span style={{ color: cinema.muted, fontSize: 11, whiteSpace: 'nowrap' }}>
            {billing.video_source === 'own' ? '自己的 Key' : `¥${billing.wallet.balance_yuan}`}
          </span>
        )}
        {videoUrl && !genRunning && (
          <span className="cinema-chip">已出片</span>
        )}
        <Input
          value={text}
          disabled={busy}
          placeholder="输入文字场景，例如：女生晚上回到家，坐下。"
          onChange={(e) => setText(e.target.value)}
          onPressEnter={() => void submit()}
          style={{ flex: 1, minWidth: 180 }}
        />
        <Button type="primary" loading={busy} onClick={() => void startVideo()}>
          {genRunning ? `出片中 ${formatElapsed(elapsed)}` : '生成视频'}
        </Button>
        <Button icon={<SendOutlined />} disabled={busy} onClick={() => void submit()} />
      </div>
      {videoUrl && !genRunning && (
        <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 10 }}>
          <video
            src={asThumb(videoUrl)}
            controls
            playsInline
            style={{
              width: 168,
              height: 96,
              objectFit: 'cover',
              borderRadius: 8,
              background: '#000',
              border: `1px solid ${cinema.line}`,
            }}
          />
          <div style={{ color: cinema.muted, fontSize: 12, lineHeight: 1.6 }}>
            成片已在本页，点播放即可看。右上角「历史记录」里也有完整版本。
          </div>
        </div>
      )}
      {genRunning && (
        <div style={{ marginTop: 8 }}>
          <Progress
            percent={estimateGenProgress(elapsed)}
            status="active"
            strokeColor={cinema.gold}
            trailColor="rgba(199,184,156,0.12)"
            strokeWidth={10}
          />
          <div style={{ color: cinema.gold, fontSize: 12, marginTop: 2 }}>
            MiniMax 出片中 {formatElapsed(elapsed)} · 约 {estimateGenProgress(elapsed)}% · 通常 2–4 分钟，请不要关页面
          </div>
        </div>
      )}
      {(status || pendingConfirm || genError) && !genRunning && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
          {(status || genError) && (
            <div style={{ color: genError ? cinema.danger : cinema.muted, fontSize: 12, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {genError ? `出片失败：${genError}` : `Agent：${status}`}
            </div>
          )}
          {pendingConfirm && (
            <>
              <Button size="small" onClick={() => void confirmPending(false)}>取消</Button>
              <Button size="small" type="primary" onClick={() => void confirmPending(true)}>确认执行</Button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function Thumb({ src, label, onRemove }: { src: string; label: string; onRemove?: () => void }) {
  return (
    <div style={{ position: 'relative', flexShrink: 0 }}>
      <img
        src={asThumb(src)}
        alt={label}
        style={{
          width: 34,
          height: 42,
          objectFit: 'cover',
          borderRadius: 5,
          border: `1px solid ${cinema.gold}`,
          background: cinema.raised,
        }}
      />
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          style={{
            position: 'absolute',
            top: -5,
            right: -5,
            width: 14,
            height: 14,
            borderRadius: 99,
            border: 0,
            background: cinema.danger,
            color: '#fff',
            fontSize: 9,
            cursor: 'pointer',
          }}
        >
          ×
        </button>
      )}
    </div>
  );
}

function EmptyChip({ children }: { children: string }) {
  return (
    <span
      style={{
        fontSize: 11,
        color: cinema.muted,
        border: `1px dashed ${cinema.line}`,
        borderRadius: 8,
        padding: '6px 8px',
        flexShrink: 0,
      }}
    >
      {children}
    </span>
  );
}
