import { Suspense, useMemo, useState, type DragEvent } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { ContactShadows, GizmoHelper, GizmoViewport, Grid, OrbitControls } from '@react-three/drei';
import { useDirectorStore } from '../store/useDirectorStore';
import { registerCaptureContext } from '../captureRegistry';
import { applySceneCanvasFile } from '../sceneCanvas';
import { parseAspect } from '../types';
import { useCapturing } from '../hooks/useCapturing';
import { SceneObjectMesh } from './SceneObjectMesh';
import { SoftLoadBoundary } from './ErrorFallback';
import SceneBackdrop from './SceneBackdrop';
import { ShotCameraRig } from './ShotCameraRig';
import { TransformGizmo } from './TransformGizmo';
import { cinema } from '../../theme';

interface Props {
  directorResetKey: number;
}

function CaptureBinder() {
  const { gl, scene } = useThree();
  useFrame(() => {
    registerCaptureContext({ gl, scene });
  });
  return null;
}

function SceneContent({ directorResetKey }: Props) {
  const objects = useDirectorStore((s) => s.objects) ?? [];
  const viewMode = useDirectorStore((s) => s.viewMode);
  const environment = useDirectorStore((s) => s.environment) ?? { sky: '#141428', showGrid: true, ambientIntensity: 0.55 };
  const selectObject = useDirectorStore((s) => s.selectObject);
  const capturing = useCapturing();

  return (
    <>
      <CaptureBinder />
      <color attach="background" args={[environment.sky || '#141428']} />
      <ambientLight intensity={environment.ambientIntensity ?? 0.55} />
      <directionalLight position={[6, 10, 4]} intensity={1.8} castShadow />
      <directionalLight position={[-4, 3, -2]} intensity={0.45} />
      <hemisphereLight args={['#ffffff', '#444466', 0.35]} />
      <ContactShadows opacity={0.35} scale={20} blur={2.2} far={8} />
      {!capturing && environment.showGrid && viewMode !== 'final' && (
        <Grid
          args={[24, 24]}
          cellSize={0.5}
          cellColor="#2a2824"
          sectionSize={2}
          sectionColor="#4a453c"
          fadeDistance={30}
          infiniteGrid
        />
      )}
      {environment.backdropUrl && (
        <Suspense fallback={null}>
          <SoftLoadBoundary>
            <SceneBackdrop key={environment.backdropUrl.slice(0, 80)} url={environment.backdropUrl} />
          </SoftLoadBoundary>
        </Suspense>
      )}
      {objects.map((obj) => (
        <SceneObjectMesh key={obj.id} object={obj} />
      ))}
      <ShotCameraRig />
      {!capturing && <TransformGizmo />}
      {viewMode === 'director' && !capturing && (
        <OrbitControls
          key={directorResetKey}
          makeDefault
          enableDamping
          onStart={() => undefined}
        />
      )}
      {!capturing && viewMode === 'director' && (
        <GizmoHelper alignment="bottom-right" margin={[64, 64]}>
          <GizmoViewport />
        </GizmoHelper>
      )}
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, -0.01, 0]}
        onClick={() => selectObject(null)}
      >
        <planeGeometry args={[80, 80]} />
        <meshBasicMaterial transparent opacity={0} />
      </mesh>
    </>
  );
}

export default function Viewport({ directorResetKey }: Props) {
  const aspectRatio = useDirectorStore((s) => s.aspectRatio);
  const backdropUrl = useDirectorStore((s) => s.environment.backdropUrl);
  const aspect = useMemo(() => parseAspect(aspectRatio), [aspectRatio]);
  const [dragging, setDragging] = useState(false);

  const onDropImage = async (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (!file) return;
    await applySceneCanvasFile(file);
  };

  return (
    <div
      style={{
        flex: 1,
        minWidth: 0,
        minHeight: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#0d0d18',
        position: 'relative',
      }}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => void onDropImage(event)}
    >
      {dragging && (
        <div
          style={{
            position: 'absolute',
            inset: 12,
            zIndex: 6,
            border: `1.5px dashed ${cinema.gold}`,
            borderRadius: 12,
            background: 'rgba(14,13,11,0.55)',
            color: cinema.text,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
            fontSize: 14,
          }}
        >
          松开即可贴到 3D 画布
        </div>
      )}
      {!backdropUrl && !dragging && (
        <div
          style={{
            position: 'absolute',
            left: '50%',
            bottom: 16,
            transform: 'translateX(-50%)',
            zIndex: 3,
            color: cinema.muted,
            fontSize: 12,
            pointerEvents: 'none',
          }}
        >
          把实拍图拖进摄影棚，直接当场景画布
        </div>
      )}
      <div
        style={{
          width: aspect < 1 ? `min(100%, calc((100% - 0px) * ${aspect} * 1.15))` : '100%',
          height: aspect >= 1 ? '100%' : '100%',
          maxWidth: '100%',
          maxHeight: '100%',
          aspectRatio: `${aspect}`,
          background: '#141428',
        }}
      >
        <Canvas
          shadows
          gl={{ preserveDrawingBuffer: true, antialias: true }}
          camera={{ position: [5.5, 3.6, 6.5], fov: 50, near: 0.1, far: 200 }}
          onPointerMissed={() => useDirectorStore.getState().selectObject(null)}
        >
          <Suspense fallback={null}>
            <SceneContent directorResetKey={directorResetKey} />
          </Suspense>
        </Canvas>
      </div>
    </div>
  );
}
