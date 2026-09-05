import { useEffect, useRef } from 'react';
import { TransformControls } from '@react-three/drei';
import { useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useDirectorStore } from '../store/useDirectorStore';
import { useCapturing } from '../hooks/useCapturing';

export function TransformGizmo() {
  const selectedId = useDirectorStore((s) => s.selectedId);
  const objects = useDirectorStore((s) => s.objects);
  const cameras = useDirectorStore((s) => s.cameras);
  const mode = useDirectorStore((s) => s.transformMode);
  const updateTransform = useDirectorStore((s) => s.updateTransform);
  const updateCamera = useDirectorStore((s) => s.updateCamera);
  const capturing = useCapturing();
  const viewMode = useDirectorStore((s) => s.viewMode);
  const { scene } = useThree();
  const controlsRef = useRef<THREE.Object3D | null>(null);

  const selectedObject = objects.find((o) => o.id === selectedId);
  const selectedCamera = cameras.find((c) => c.id === selectedId);

  useEffect(() => {
    if (!selectedId) return;
    const target = scene.getObjectByName(selectedId);
    const controls = controlsRef.current as unknown as {
      attach: (obj: THREE.Object3D) => void;
      detach: () => void;
      addEventListener: (type: string, fn: (e: { value: boolean }) => void) => void;
      removeEventListener: (type: string, fn: (e: { value: boolean }) => void) => void;
      object?: THREE.Object3D;
    } | null;
    if (!controls || !target) return;

    controls.attach(target);

    const onDrag = (event: { value: boolean }) => {
      if (event.value) return;
      const obj = controls.object ?? target;
      const position: [number, number, number] = [obj.position.x, obj.position.y, obj.position.z];
      const rotation: [number, number, number] = [obj.rotation.x, obj.rotation.y, obj.rotation.z];
      const scale: [number, number, number] = [obj.scale.x, obj.scale.y, obj.scale.z];
      if (selectedObject) {
        updateTransform(selectedId, { position, rotation, scale });
      } else if (selectedCamera) {
        updateCamera(selectedId, { position, rotation });
      }
    };

    controls.addEventListener('dragging-changed', onDrag);
    return () => {
      controls.removeEventListener('dragging-changed', onDrag);
      controls.detach();
    };
  }, [selectedId, selectedObject, selectedCamera, scene, updateTransform, updateCamera, mode]);

  if (capturing || viewMode === 'final' || !selectedId || (!selectedObject && !selectedCamera)) return null;

  return (
    <TransformControls
      ref={controlsRef as never}
      mode={mode}
      onMouseUp={() => {
        const target = scene.getObjectByName(selectedId);
        if (!target) return;
        const position: [number, number, number] = [target.position.x, target.position.y, target.position.z];
        const rotation: [number, number, number] = [target.rotation.x, target.rotation.y, target.rotation.z];
        const scale: [number, number, number] = [target.scale.x, target.scale.y, target.scale.z];
        if (selectedObject) updateTransform(selectedId, { position, rotation, scale });
        else if (selectedCamera) updateCamera(selectedId, { position, rotation });
      }}
    />
  );
}
