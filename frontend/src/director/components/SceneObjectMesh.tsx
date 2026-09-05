import { useEffect, useMemo } from 'react';
import { useAnimations, useGLTF } from '@react-three/drei';
import * as SkeletonUtils from 'three/examples/jsm/utils/SkeletonUtils.js';
import type { Object3D } from 'three';
import { useDirectorStore } from '../store/useDirectorStore';
import { useCharacterLibrary } from '../characters/useCharacterLibrary';
import type { SceneObject } from '../types';
import { ModelErrorBoundary } from './ErrorFallback';
import { KitMesh } from './KitMesh';
import { CharacterActor } from './CharacterActor';

function GltfMesh({ url, object }: { url: string; object: SceneObject }) {
  const { scene, animations } = useGLTF(url);
  const cloned = useMemo(() => SkeletonUtils.clone(scene) as Object3D, [scene]);
  const { actions, names } = useAnimations(animations, cloned);
  const setAnimationNames = useDirectorStore((s) => s.setAnimationNames);

  useEffect(() => {
    if (names.length) setAnimationNames(object.id, names);
  }, [names, object.id, setAnimationNames]);

  useEffect(() => {
    Object.values(actions).forEach((action) => action?.stop());
    if (object.animation && actions[object.animation]) {
      actions[object.animation]?.reset().fadeIn(0.15).play();
    }
  }, [actions, object.animation]);

  return <primitive object={cloned} />;
}

export function SceneObjectMesh({ object }: { object: SceneObject }) {
  const selectedId = useDirectorStore((s) => s.selectedId);
  const selectObject = useDirectorStore((s) => s.selectObject);
  const asset = useCharacterLibrary((s) =>
    object.characterId ? s.characters.find((c) => c.id === object.characterId) : undefined,
  );
  const selected = selectedId === object.id;
  if (!object.visible) return null;

  const isCharacter = !!object.characterId;

  return (
    <group
      name={object.id}
      position={object.position}
      rotation={object.rotation}
      scale={object.scale}
      onClick={(e) => {
        e.stopPropagation();
        if (!object.locked) selectObject(object.id);
      }}
    >
      {isCharacter && asset ? (
        <ModelErrorBoundary>
          <CharacterActor object={object} asset={asset} />
        </ModelErrorBoundary>
      ) : isCharacter && !asset ? (
        <mesh>
          <boxGeometry args={[0.4, 0.4, 0.4]} />
          <meshStandardMaterial color="#ff4d4f" wireframe />
        </mesh>
      ) : object.modelUrl ? (
        <ModelErrorBoundary>
          <GltfMesh url={object.modelUrl} object={object} />
        </ModelErrorBoundary>
      ) : (
        <KitMesh object={object} />
      )}
      {selected && (
        <mesh>
          <sphereGeometry args={[isCharacter ? 1.4 : 1.15, 12, 12]} />
          <meshBasicMaterial color="#69c0ff" wireframe transparent opacity={0.28} />
        </mesh>
      )}
    </group>
  );
}
