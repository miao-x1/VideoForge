import { useRef, useState } from 'react';
import { Button, Typography } from 'antd';
import { PlusOutlined, VideoCameraOutlined } from '@ant-design/icons';
import { useDirectorStore } from '../store/useDirectorStore';
import { useAgentStore } from '../agent/useAgentStore';
import { mediaUrl } from '../../api/client';
import { directorDark } from '../../theme';
import type { DirectorSceneState } from '../types';

const { Text } = Typography;

const NODE_W = 280;
const NODE_H = 320;
const GAP = 36;

export default function StoryboardCanvas({
  onOpenStage,
}: {
  onOpenStage: (sceneId: string) => void;
}) {
  const scenes = useDirectorStore((s) => s.scenes);
  const sceneId = useDirectorStore((s) => s.sceneId);
  const switchScene = useDirectorStore((s) => s.switchScene);
  const createShotScene = useDirectorStore((s) => s.createShotScene);
  const setCanvasPos = useDirectorStore((s) => s.setCanvasPos);
  const send = useAgentStore((s) => s.send);
  const running = useAgentStore((s) => s.running);
  const messages = useAgentStore((s) => s.messages);
  const persistNow = useDirectorStore((s) => s.persistNow);
  const brief = [...messages].reverse().find((m) => m.role === 'user')?.text || '';
  const [pan, setPan] = useState({ x: 56, y: 72 });
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null);

  const createAndOpen = () => {
    const id = createShotScene();
    onOpenStage(id);
  };

  return (
    <div
      style={{
        flex: 1,
        minWidth: 0,
        minHeight: 0,
        position: 'relative',
        overflow: 'hidden',
        backgroundColor: directorDark.bg,
        backgroundImage: 'radial-gradient(rgba(255,255,255,0.06) 1px, transparent 1px)',
        backgroundSize: '24px 24px',
        cursor: 'grab',
      }}
      onPointerDown={(e) => {
        if (e.target !== e.currentTarget) return;
        drag.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y };
        (e.currentTarget as HTMLDivElement).setPointerCapture(e.pointerId);
      }}
      onPointerMove={(e) => {
        if (!drag.current) return;
        setPan({
          x: drag.current.px + (e.clientX - drag.current.x),
          y: drag.current.py + (e.clientY - drag.current.y),
        });
      }}
      onPointerUp={() => {
        drag.current = null;
      }}
    >
      <div style={{ position: 'absolute', left: 20, top: 16, zIndex: 2, pointerEvents: 'none' }}>
        <Text style={{ color: directorDark.text, fontSize: 15, fontWeight: 600 }}>项目画布</Text>
        <div>
          <Text style={{ color: directorDark.muted, fontSize: 12 }}>
            双击导演台节点进入 3D。摆好站位和机位后发送构图，再生成画面 / 视频。
          </Text>
        </div>
      </div>

      <div style={{ position: 'absolute', left: pan.x, top: pan.y }}>
        <svg
          width={1}
          height={1}
          style={{ position: 'absolute', left: 0, top: 0, overflow: 'visible', pointerEvents: 'none' }}
        >
          {scenes.map((scene, index) => {
            const pos = nodePos(scene, index);
            const prev = index === 0
              ? { x: 220, y: 56 }
              : (() => {
                  const p = nodePos(scenes[index - 1], index - 1);
                  return { x: p.left + NODE_W, y: p.top + 75 };
                })();
            const x2 = pos.left;
            const y2 = pos.top + 75;
            const mid = (prev.x + x2) / 2;
            return (
              <path
                key={scene.sceneId}
                d={`M ${prev.x} ${prev.y} C ${mid} ${prev.y}, ${mid} ${y2}, ${x2} ${y2}`}
                fill="none"
                stroke="#3a3a55"
                strokeWidth={1.5}
              />
            );
          })}
        </svg>
        <ScriptNode brief={brief} />

        <button
          type="button"
          onClick={createAndOpen}
          style={{
            position: 'absolute',
            left: 0,
            top: 168,
            width: 220,
            height: NODE_H,
            border: `1px dashed ${directorDark.border}`,
            borderRadius: 14,
            background: 'rgba(255,255,255,0.03)',
            color: '#d9d9d9',
            cursor: 'pointer',
          }}
        >
          <PlusOutlined style={{ fontSize: 26 }} />
          <div style={{ marginTop: 8 }}>新建导演台</div>
        </button>

        {scenes.map((scene, index) => {
          const { left, top } = nodePos(scene, index);
          return (
            <ShotNode
              key={scene.sceneId}
              scene={scene}
              index={index}
              left={left}
              top={top}
              active={scene.sceneId === sceneId}
              disabled={running}
              onSelect={() => switchScene(scene.sceneId)}
              onOpen={() => onOpenStage(scene.sceneId)}
              onMove={(x, y) => setCanvasPos(scene.sceneId, x, y)}
              onMoveEnd={() => persistNow()}
              onGenerateImage={() => {
                switchScene(scene.sceneId);
                void send('生成这个镜头的画面。');
              }}
              onGenerateVideo={() => {
                switchScene(scene.sceneId);
                void send('把这个画面做成 5 秒视频。');
              }}
            />
          );
        })}
      </div>
    </div>
  );
}

function nodePos(scene: DirectorSceneState, index: number) {
  return {
    left: scene.canvasX ?? 248 + (index % 3) * (NODE_W + GAP),
    top: scene.canvasY ?? Math.floor(index / 3) * (NODE_H + GAP),
  };
}

function ScriptNode({ brief }: { brief: string }) {
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 220,
        borderRadius: 14,
        background: directorDark.panel,
        border: `1px solid ${directorDark.border}`,
        padding: 12,
      }}
    >
      <div style={{ color: directorDark.accent, fontSize: 11, fontWeight: 600 }}>剧本 / 创意</div>
      <div style={{ color: directorDark.text, fontSize: 13, marginTop: 6, lineHeight: 1.45 }}>
        {brief || '在底部告诉 Agent 你要拍什么，镜头节点会出现在画布上。'}
      </div>
    </div>
  );
}

function ShotNode({
  scene,
  index,
  left,
  top,
  active,
  disabled,
  onSelect,
  onOpen,
  onMove,
  onMoveEnd,
  onGenerateImage,
  onGenerateVideo,
}: {
  scene: DirectorSceneState;
  index: number;
  left: number;
  top: number;
  active: boolean;
  disabled: boolean;
  onSelect: () => void;
  onOpen: () => void;
  onMove: (x: number, y: number) => void;
  onMoveEnd: () => void;
  onGenerateImage: () => void;
  onGenerateVideo: () => void;
}) {
  const drag = useRef<{ x: number; y: number; left: number; top: number } | null>(null);
  const composition = scene.compositionUrl || null;
  const preview = scene.imageUrl || composition;
  const video = scene.videoUrl || null;

  return (
    <div
      onPointerDown={(e) => {
        if ((e.target as HTMLElement).closest('button')) return;
        e.stopPropagation();
        drag.current = { x: e.clientX, y: e.clientY, left, top };
        (e.currentTarget as HTMLDivElement).setPointerCapture(e.pointerId);
      }}
      onPointerMove={(e) => {
        if (!drag.current) return;
        onMove(drag.current.left + e.clientX - drag.current.x, drag.current.top + e.clientY - drag.current.y);
      }}
      onPointerUp={() => {
        if (drag.current) onMoveEnd();
        drag.current = null;
      }}
      onClick={onSelect}
      onDoubleClick={onOpen}
      style={{
        position: 'absolute',
        left,
        top,
        width: NODE_W,
        borderRadius: 14,
        overflow: 'hidden',
        background: directorDark.panel,
        border: active ? `2px solid ${directorDark.accent}` : `1px solid ${directorDark.border}`,
        boxShadow: '0 12px 32px rgba(0,0,0,0.4)',
        cursor: 'grab',
      }}
    >
      <div style={{ height: 150, background: '#000', position: 'relative' }}>
        {video ? (
          <video src={mediaUrl(video)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        ) : preview ? (
          <img src={mediaUrl(preview)} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        ) : (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#595959', gap: 6 }}>
            <VideoCameraOutlined /> 打开导演台摆站位
          </div>
        )}
        <span
          style={{
            position: 'absolute',
            left: 8,
            top: 8,
            fontSize: 11,
            color: '#fff',
            background: 'rgba(102,126,234,0.9)',
            borderRadius: 4,
            padding: '1px 6px',
          }}
        >
          导演台 · Shot {String(index + 1).padStart(2, '0')}
        </span>
      </div>
      <div style={{ display: 'flex', gap: 4, padding: '6px 8px 0', alignItems: 'center' }}>
        <PipeTag label="构图" on={!!composition} />
        <PipeTag label="画面" on={!!scene.imageUrl} />
        <PipeTag label="视频" on={!!video} />
      </div>
      {(composition || scene.imageUrl || video) && (
        <div style={{ display: 'flex', gap: 4, padding: '4px 8px 0' }}>
          <MiniFrame src={composition} label="构图" />
          <MiniFrame src={scene.imageUrl || null} label="画面" />
          <MiniFrame src={video} label="视频" video />
        </div>
      )}
      <div style={{ padding: 10 }}>
        <div style={{ color: directorDark.text, fontSize: 13, fontWeight: 600 }}>{scene.sceneName || `分镜 ${index + 1}`}</div>
        <div style={{ color: directorDark.muted, fontSize: 11, marginTop: 4 }}>
          {scene.shotDuration ?? 4}s · {scene.shotType || 'medium shot'}
          {scene.shotDescription ? ` · ${scene.shotDescription}` : ''}
        </div>
        <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
          <Button size="small" type="primary" onClick={(e) => { e.stopPropagation(); onOpen(); }}>
            打开导演台
          </Button>
          <Button size="small" disabled={disabled} onClick={(e) => { e.stopPropagation(); onGenerateImage(); }}>
            生成画面
          </Button>
          <Button size="small" disabled={disabled} onClick={(e) => { e.stopPropagation(); onGenerateVideo(); }}>
            生成视频
          </Button>
        </div>
      </div>
    </div>
  );
}

function MiniFrame({ src, label, video }: { src: string | null; label: string; video?: boolean }) {
  return (
    <div
      title={label}
      style={{
        flex: 1,
        height: 36,
        borderRadius: 4,
        overflow: 'hidden',
        background: '#0a0a12',
        border: `1px solid ${directorDark.border}`,
      }}
    >
      {src && video ? (
        <video src={mediaUrl(src)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
      ) : src ? (
        <img src={mediaUrl(src)} alt={label} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
      ) : null}
    </div>
  );
}

function PipeTag({ label, on }: { label: string; on: boolean }) {
  return (
    <span
      style={{
        fontSize: 10,
        padding: '1px 6px',
        borderRadius: 99,
        color: on ? '#fff' : directorDark.muted,
        background: on ? directorDark.accent : '#222236',
      }}
    >
      {label}
    </span>
  );
}
