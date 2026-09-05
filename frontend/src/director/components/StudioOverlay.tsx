import { Radio, Upload, message } from 'antd';
import { useDirectorStore } from '../store/useDirectorStore';
import { applySceneCanvasFile, clearSceneCanvas } from '../sceneCanvas';
import type { TransformMode, ViewMode } from '../types';
import { cinema } from '../../theme';

export default function StudioOverlay() {
  const transformMode = useDirectorStore((s) => s.transformMode);
  const setTransformMode = useDirectorStore((s) => s.setTransformMode);
  const viewMode = useDirectorStore((s) => s.viewMode);
  const setViewMode = useDirectorStore((s) => s.setViewMode);
  const aspectRatio = useDirectorStore((s) => s.aspectRatio);
  const backdropUrl = useDirectorStore((s) => s.environment.backdropUrl);

  return (
    <>
      <div
        style={{
          position: 'absolute',
          left: 12,
          top: 12,
          zIndex: 4,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
      >
        <Radio.Group
          size="small"
          value={viewMode}
          onChange={(e) => setViewMode(e.target.value as ViewMode)}
        >
          <Radio.Button value="director">自由视角</Radio.Button>
          <Radio.Button value="shot">摄像机视角</Radio.Button>
          <Radio.Button value="final">最终画面</Radio.Button>
        </Radio.Group>
        <Radio.Group
          size="small"
          value={transformMode}
          onChange={(e) => setTransformMode(e.target.value as TransformMode)}
        >
          <Radio.Button value="translate">移动</Radio.Button>
          <Radio.Button value="rotate">旋转</Radio.Button>
          <Radio.Button value="scale">缩放</Radio.Button>
        </Radio.Group>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <Upload
            accept="image/*"
            showUploadList={false}
            beforeUpload={(file) => {
              void applySceneCanvasFile(file)
                .then(() => message.success('已贴到 3D 画布'))
                .catch((err: unknown) => message.error(err instanceof Error ? err.message : '贴图失败'));
              return false;
            }}
          >
            <button type="button" className="cinema-chip">{backdropUrl ? '更换实拍画布' : '贴实拍画布'}</button>
          </Upload>
          {backdropUrl && (
            <button type="button" className="cinema-chip" onClick={() => { clearSceneCanvas(); message.success('已撤下画布'); }}>
              撤下
            </button>
          )}
        </div>
      </div>
      {viewMode === 'final' && (
        <>
          <div style={{ position: 'absolute', left: 0, right: 0, top: 0, height: 28, background: 'rgba(0,0,0,0.55)', zIndex: 3, pointerEvents: 'none' }} />
          <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 28, background: 'rgba(0,0,0,0.55)', zIndex: 3, pointerEvents: 'none' }} />
        </>
      )}
      <div
        style={{
          position: 'absolute',
          right: 12,
          top: 12,
          zIndex: 4,
          padding: '4px 10px',
          borderRadius: 99,
          background: 'rgba(11,10,15,0.62)',
          color: cinema.text,
          fontSize: 12,
        }}
      >
        {viewMode === 'director' ? '自由视角' : viewMode === 'shot' ? '摄像机视角' : '最终画面'} · {aspectRatio}
      </div>
    </>
  );
}
