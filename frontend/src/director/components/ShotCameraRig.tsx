import { PerspectiveCamera } from '@react-three/drei';
import { useDirectorStore } from '../store/useDirectorStore';
import { parseAspect } from '../types';
import { useCapturing } from '../hooks/useCapturing';

export function ShotCameraRig() {
  const camera = useDirectorStore((s) => s.cameras.find((c) => c.id === s.activeCamera));
  const aspectRatio = useDirectorStore((s) => s.aspectRatio);
  const viewMode = useDirectorStore((s) => s.viewMode);
  const selectedId = useDirectorStore((s) => s.selectedId);
  const selectObject = useDirectorStore((s) => s.selectObject);
  const capturing = useCapturing();

  if (!camera) return null;

  return (
    <group>
      <PerspectiveCamera
        makeDefault={viewMode === 'shot' || viewMode === 'final'}
        fov={camera.fov}
        aspect={parseAspect(aspectRatio)}
        near={0.1}
        far={200}
        position={camera.position}
        rotation={camera.rotation}
      />
      {viewMode === 'director' && !capturing && (
        <group
          name={camera.id}
          position={camera.position}
          rotation={camera.rotation}
          onClick={(e) => {
            e.stopPropagation();
            selectObject(camera.id);
          }}
        >
          <mesh>
            <boxGeometry args={[0.28, 0.2, 0.36]} />
            <meshStandardMaterial color={selectedId === camera.id ? '#36cfc9' : '#595959'} />
          </mesh>
          <mesh position={[0, 0, -0.28]} rotation={[Math.PI / 2, 0, 0]}>
            <coneGeometry args={[0.12, 0.28, 8]} />
            <meshStandardMaterial color="#ff4d4f" />
          </mesh>
        </group>
      )}
    </group>
  );
}
