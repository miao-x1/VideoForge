import type { SceneObject } from '../types';

function Surface({ object }: { object: SceneObject }) {
  return (
    <meshStandardMaterial
      color={object.color}
      metalness={object.metalness}
      roughness={object.roughness}
      transparent={object.opacity < 1}
      opacity={object.opacity}
      emissive={object.emissive}
    />
  );
}

function Humanoid({
  object,
  slim,
  short,
  baby,
  sit,
}: {
  object: SceneObject;
  slim?: boolean;
  short?: boolean;
  baby?: boolean;
  sit?: boolean;
}) {
  const s = baby ? 0.42 : short ? 0.78 : 1;
  const w = slim ? 0.28 : baby ? 0.22 : 0.35;
  return (
    <group>
      <mesh castShadow position={[0, (1.55 * s), 0]}>
        <sphereGeometry args={[0.22 * (short ? 0.95 : 1), 16, 16]} />
        <Surface object={object} />
      </mesh>
      <mesh castShadow position={[0, 0.95 * s, 0]}>
        <capsuleGeometry args={[w, 0.7 * s, 6, 12]} />
        <Surface object={object} />
      </mesh>
      <mesh castShadow position={[-(w + 0.12), 1.05 * s, 0]} rotation={[0, 0, 0.35]}>
        <capsuleGeometry args={[0.09, 0.45 * s, 4, 8]} />
        <Surface object={object} />
      </mesh>
      <mesh castShadow position={[w + 0.12, 1.05 * s, 0]} rotation={[0, 0, -0.35]}>
        <capsuleGeometry args={[0.09, 0.45 * s, 4, 8]} />
        <Surface object={object} />
      </mesh>
      <mesh
        castShadow
        position={sit ? [-0.14, 0.42 * s, 0.16] : [-0.14, 0.32 * s, 0]}
        rotation={sit ? [1.2, 0, 0] : [0, 0, 0]}
      >
        <capsuleGeometry args={[0.1, 0.38 * s, 4, 8]} />
        <Surface object={object} />
      </mesh>
      <mesh
        castShadow
        position={sit ? [0.14, 0.42 * s, 0.16] : [0.14, 0.32 * s, 0]}
        rotation={sit ? [1.2, 0, 0] : [0, 0, 0]}
      >
        <capsuleGeometry args={[0.1, 0.38 * s, 4, 8]} />
        <Surface object={object} />
      </mesh>
    </group>
  );
}

function QuadAnimal({ object, long }: { object: SceneObject; long?: boolean }) {
  const len = long ? 1.1 : 0.7;
  return (
    <group>
      <mesh castShadow position={[0, 0.38, 0]}>
        <capsuleGeometry args={[0.2, len, 6, 12]} />
        <Surface object={object} />
      </mesh>
      <mesh castShadow position={[len * 0.45, 0.48, 0]}>
        <sphereGeometry args={[0.18, 12, 12]} />
        <Surface object={object} />
      </mesh>
      {[
        [-0.22, -0.16] as const,
        [-0.22, 0.16] as const,
        [0.22, -0.16] as const,
        [0.22, 0.16] as const,
      ].map(([x, z], i) => (
        <mesh key={i} castShadow position={[x, 0.16, z]}>
          <cylinderGeometry args={[0.05, 0.05, 0.32, 8]} />
          <Surface object={object} />
        </mesh>
      ))}
    </group>
  );
}

export function KitMesh({ object }: { object: SceneObject }) {
  const kind = object.primitive ?? 'box';

  if (kind === 'human_male') return <Humanoid object={object} />;
  if (kind === 'human_female') return <Humanoid object={object} slim />;
  if (kind === 'human_teen') return <Humanoid object={object} short />;
  if (kind === 'human_child') return <Humanoid object={object} short />;
  if (kind === 'human_baby') return <Humanoid object={object} baby />;
  if (kind === 'human_elder') return <Humanoid object={object} />;
  if (kind === 'human_sit') return <Humanoid object={object} sit />;
  if (kind === 'mannequin') return <Humanoid object={object} />;
  if (kind === 'robot') {
    return (
      <group>
        <mesh castShadow position={[0, 1.55, 0]}>
          <boxGeometry args={[0.36, 0.36, 0.36]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 0.95, 0]}>
          <boxGeometry args={[0.55, 0.7, 0.32]} />
          <Surface object={object} />
        </mesh>
        {[-0.38, 0.38].map((x) => (
          <mesh key={x} castShadow position={[x, 0.95, 0]}>
            <boxGeometry args={[0.14, 0.55, 0.14]} />
            <Surface object={object} />
          </mesh>
        ))}
        {[-0.14, 0.14].map((x) => (
          <mesh key={`leg-${x}`} castShadow position={[x, 0.32, 0]}>
            <boxGeometry args={[0.16, 0.64, 0.16]} />
            <Surface object={object} />
          </mesh>
        ))}
      </group>
    );
  }
  if (kind === 'crowd') {
    return (
      <group>
        {[-0.45, 0, 0.45].map((x, i) => (
          <group key={x} position={[x, 0, i === 1 ? -0.12 : 0.08]} scale={i === 1 ? 0.85 : 0.7}>
            <Humanoid object={object} slim={i !== 1} />
          </group>
        ))}
      </group>
    );
  }
  if (kind === 'dog' || kind === 'cat' || kind === 'sheep') return <QuadAnimal object={object} />;
  if (kind === 'horse' || kind === 'cow' || kind === 'deer' || kind === 'bear') {
    return <QuadAnimal object={object} long />;
  }
  if (kind === 'rabbit') {
    return (
      <group>
        <QuadAnimal object={object} />
        {[-0.06, 0.06].map((x) => (
          <mesh key={x} castShadow position={[0.28, 0.72, x]} rotation={[0.15, 0, 0]}>
            <capsuleGeometry args={[0.03, 0.22, 4, 6]} />
            <Surface object={object} />
          </mesh>
        ))}
      </group>
    );
  }
  if (kind === 'bird') {
    return (
      <group>
        <mesh castShadow position={[0, 0.35, 0]}>
          <sphereGeometry args={[0.16, 12, 12]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0.2, 0.32, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[0.05, 0.16, 8]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 0.35, 0.18]} rotation={[0.4, 0, 0.4]}>
          <boxGeometry args={[0.22, 0.02, 0.12]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 0.35, -0.18]} rotation={[-0.4, 0, -0.4]}>
          <boxGeometry args={[0.22, 0.02, 0.12]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'chicken') {
    return (
      <group>
        <mesh castShadow position={[0, 0.22, 0]}>
          <sphereGeometry args={[0.16, 12, 12]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0.16, 0.3, 0]}>
          <sphereGeometry args={[0.1, 10, 10]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0.26, 0.28, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[0.03, 0.1, 6]} />
          <meshStandardMaterial color="#fa541c" />
        </mesh>
      </group>
    );
  }
  if (kind === 'fish') {
    return (
      <group>
        <mesh castShadow position={[0, 0.25, 0]} rotation={[0, 0, Math.PI / 2]}>
          <capsuleGeometry args={[0.1, 0.36, 6, 10]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[-0.28, 0.25, 0]} rotation={[0, 0, Math.PI / 2]}>
          <coneGeometry args={[0.1, 0.18, 6]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'snake') {
    return (
      <group>
        {[0, 1, 2, 3].map((i) => (
          <mesh key={i} castShadow position={[-0.28 + i * 0.18, 0.06, Math.sin(i) * 0.08]}>
            <sphereGeometry args={[0.07, 10, 10]} />
            <Surface object={object} />
          </mesh>
        ))}
      </group>
    );
  }

  if (kind === 'table') {
    return (
      <group>
        <mesh castShadow position={[0, 0.72, 0]}>
          <boxGeometry args={[1.2, 0.08, 0.7]} />
          <Surface object={object} />
        </mesh>
        {[[-0.5, -0.28], [-0.5, 0.28], [0.5, -0.28], [0.5, 0.28]].map(([x, z], i) => (
          <mesh key={i} castShadow position={[x, 0.34, z]}>
            <boxGeometry args={[0.07, 0.68, 0.07]} />
            <Surface object={object} />
          </mesh>
        ))}
      </group>
    );
  }
  if (kind === 'chair') {
    return (
      <group>
        <mesh castShadow position={[0, 0.42, 0]}>
          <boxGeometry args={[0.46, 0.06, 0.46]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 0.72, -0.2]}>
          <boxGeometry args={[0.46, 0.54, 0.06]} />
          <Surface object={object} />
        </mesh>
        {[[-0.18, -0.18], [-0.18, 0.18], [0.18, -0.18], [0.18, 0.18]].map(([x, z], i) => (
          <mesh key={i} castShadow position={[x, 0.2, z]}>
            <boxGeometry args={[0.05, 0.4, 0.05]} />
            <Surface object={object} />
          </mesh>
        ))}
      </group>
    );
  }
  if (kind === 'sofa') {
    return (
      <group>
        <mesh castShadow position={[0, 0.28, 0]}>
          <boxGeometry args={[1.4, 0.28, 0.6]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 0.55, -0.22]}>
          <boxGeometry args={[1.4, 0.4, 0.16]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[-0.62, 0.48, 0.05]}>
          <boxGeometry args={[0.14, 0.26, 0.5]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0.62, 0.48, 0.05]}>
          <boxGeometry args={[0.14, 0.26, 0.5]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'bed') {
    return (
      <group>
        <mesh castShadow position={[0, 0.22, 0]}>
          <boxGeometry args={[1.2, 0.16, 2]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 0.42, -0.85]}>
          <boxGeometry args={[1.2, 0.4, 0.12]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'lamp') {
    return (
      <group>
        <mesh castShadow position={[0, 0.7, 0]}>
          <cylinderGeometry args={[0.04, 0.04, 1.4, 10]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 1.45, 0]}>
          <sphereGeometry args={[0.18, 12, 12]} />
          <meshStandardMaterial color="#fff7cc" emissive="#ffec8b" emissiveIntensity={0.6} />
        </mesh>
      </group>
    );
  }
  if (kind === 'desk') {
    return (
      <group>
        <mesh castShadow position={[0, 0.76, 0]}>
          <boxGeometry args={[1.4, 0.06, 0.7]} />
          <Surface object={object} />
        </mesh>
        {[-0.6, 0.6].map((x) => (
          <mesh key={x} castShadow position={[x, 0.38, 0]}>
            <boxGeometry args={[0.08, 0.76, 0.66]} />
            <Surface object={object} />
          </mesh>
        ))}
      </group>
    );
  }
  if (kind === 'bookshelf') {
    return (
      <group>
        <mesh castShadow position={[0, 0.9, 0]}>
          <boxGeometry args={[1.1, 1.8, 0.28]} />
          <Surface object={object} />
        </mesh>
        {[0.35, 0.75, 1.15].map((y) => (
          <mesh key={y} position={[0, y, 0.02]}>
            <boxGeometry args={[1.02, 0.04, 0.24]} />
            <meshStandardMaterial color="#613400" />
          </mesh>
        ))}
      </group>
    );
  }
  if (kind === 'cabinet') {
    return (
      <mesh castShadow position={[0, 0.55, 0]}>
        <boxGeometry args={[0.8, 1.1, 0.45]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'stool') {
    return (
      <group>
        <mesh castShadow position={[0, 0.46, 0]}>
          <cylinderGeometry args={[0.18, 0.18, 0.06, 16]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 0.22, 0]}>
          <cylinderGeometry args={[0.04, 0.05, 0.44, 8]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'bench') {
    return (
      <group>
        <mesh castShadow position={[0, 0.38, 0]}>
          <boxGeometry args={[1.4, 0.08, 0.4]} />
          <Surface object={object} />
        </mesh>
        {[-0.55, 0.55].map((x) => (
          <mesh key={x} castShadow position={[x, 0.18, 0]}>
            <boxGeometry args={[0.08, 0.36, 0.36]} />
            <Surface object={object} />
          </mesh>
        ))}
      </group>
    );
  }
  if (kind === 'fridge') {
    return (
      <mesh castShadow position={[0, 0.95, 0]}>
        <boxGeometry args={[0.7, 1.9, 0.65]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'tvstand') {
    return (
      <group>
        <mesh castShadow position={[0, 0.22, 0]}>
          <boxGeometry args={[1.4, 0.44, 0.4]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 0.78, 0]}>
          <boxGeometry args={[1.2, 0.68, 0.08]} />
          <meshStandardMaterial color="#111" metalness={0.4} roughness={0.25} />
        </mesh>
      </group>
    );
  }
  if (kind === 'plantpot') {
    return (
      <group>
        <mesh castShadow position={[0, 0.16, 0]}>
          <cylinderGeometry args={[0.16, 0.12, 0.28, 12]} />
          <meshStandardMaterial color="#ad4e00" roughness={0.9} />
        </mesh>
        <mesh castShadow position={[0, 0.42, 0]}>
          <sphereGeometry args={[0.22, 12, 12]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'mirror') {
    return (
      <group>
        <mesh castShadow position={[0, 1.1, 0]}>
          <boxGeometry args={[0.7, 1.2, 0.06]} />
          <Surface object={object} />
        </mesh>
        <mesh position={[0, 1.1, 0.034]}>
          <planeGeometry args={[0.58, 1.05]} />
          <meshStandardMaterial color="#e6f4ff" metalness={0.8} roughness={0.08} />
        </mesh>
      </group>
    );
  }
  if (kind === 'wall') {
    return (
      <mesh castShadow position={[0, 1.2, 0]}>
        <boxGeometry args={[3, 2.4, 0.16]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'door') {
    return (
      <mesh castShadow position={[0, 1.05, 0]}>
        <boxGeometry args={[0.95, 2.1, 0.08]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'window') {
    return (
      <mesh castShadow position={[0, 1.3, 0]}>
        <boxGeometry args={[1.2, 1.1, 0.08]} />
        <meshStandardMaterial color={object.color} transparent opacity={0.45} metalness={0.4} roughness={0.1} />
      </mesh>
    );
  }
  if (kind === 'column') {
    return (
      <mesh castShadow position={[0, 1.4, 0]}>
        <cylinderGeometry args={[0.18, 0.2, 2.8, 12]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'stairs') {
    return (
      <group>
        {[0, 1, 2, 3].map((i) => (
          <mesh key={i} castShadow position={[0, 0.1 + i * 0.18, i * 0.28]}>
            <boxGeometry args={[1, 0.16, 0.3]} />
            <Surface object={object} />
          </mesh>
        ))}
      </group>
    );
  }
  if (kind === 'fence') {
    return (
      <group>
        {[-0.6, 0, 0.6].map((x) => (
          <mesh key={x} castShadow position={[x, 0.45, 0]}>
            <boxGeometry args={[0.08, 0.9, 0.08]} />
            <Surface object={object} />
          </mesh>
        ))}
        <mesh castShadow position={[0, 0.55, 0]}>
          <boxGeometry args={[1.4, 0.08, 0.06]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'floor') {
    return (
      <mesh receiveShadow position={[0, 0.02, 0]}>
        <boxGeometry args={[3.2, 0.04, 3.2]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'roof') {
    return (
      <mesh castShadow position={[0, 0.35, 0]} rotation={[0, Math.PI / 4, 0]}>
        <coneGeometry args={[1.4, 0.7, 4]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'house') {
    return (
      <group>
        <mesh castShadow position={[0, 0.7, 0]}>
          <boxGeometry args={[1.6, 1.4, 1.2]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 1.7, 0]} rotation={[0, Math.PI / 4, 0]}>
          <coneGeometry args={[1.25, 0.7, 4]} />
          <meshStandardMaterial color="#cf1322" roughness={0.8} />
        </mesh>
      </group>
    );
  }
  if (kind === 'arch') {
    return (
      <group>
        {[-0.55, 0.55].map((x) => (
          <mesh key={x} castShadow position={[x, 0.9, 0]}>
            <boxGeometry args={[0.22, 1.8, 0.22]} />
            <Surface object={object} />
          </mesh>
        ))}
        <mesh castShadow position={[0, 1.85, 0]}>
          <boxGeometry args={[1.32, 0.22, 0.22]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'road') {
    return (
      <group>
        <mesh receiveShadow position={[0, 0.01, 0]}>
          <boxGeometry args={[4, 0.02, 1.2]} />
          <Surface object={object} />
        </mesh>
        <mesh position={[0, 0.025, 0]}>
          <boxGeometry args={[3.2, 0.005, 0.08]} />
          <meshStandardMaterial color="#fadb14" />
        </mesh>
      </group>
    );
  }
  if (kind === 'streetlamp') {
    return (
      <group>
        <mesh castShadow position={[0, 1.2, 0]}>
          <cylinderGeometry args={[0.05, 0.07, 2.4, 8]} />
          <meshStandardMaterial color="#434343" />
        </mesh>
        <mesh castShadow position={[0.35, 2.3, 0]}>
          <boxGeometry args={[0.7, 0.08, 0.16]} />
          <meshStandardMaterial color="#434343" />
        </mesh>
        <mesh position={[0.55, 2.18, 0]}>
          <sphereGeometry args={[0.1, 10, 10]} />
          <meshStandardMaterial color={object.color} emissive={object.color} emissiveIntensity={0.8} />
        </mesh>
      </group>
    );
  }
  if (kind === 'stage') {
    return (
      <group>
        <mesh castShadow position={[0, 0.18, 0]}>
          <boxGeometry args={[3, 0.36, 1.8]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 0.42, -0.82]}>
          <boxGeometry args={[3, 0.16, 0.16]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'platform') {
    return (
      <mesh castShadow receiveShadow position={[0, 0.08, 0]}>
        <boxGeometry args={[2.2, 0.16, 2.2]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'tent') {
    return (
      <group>
        <mesh castShadow position={[0, 0.7, 0]}>
          <coneGeometry args={[0.9, 1.4, 3]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'tree') {
    return (
      <group>
        <mesh castShadow position={[0, 0.55, 0]}>
          <cylinderGeometry args={[0.1, 0.14, 1.1, 8]} />
          <meshStandardMaterial color="#613400" roughness={0.9} />
        </mesh>
        <mesh castShadow position={[0, 1.35, 0]}>
          <sphereGeometry args={[0.55, 12, 12]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0.25, 1.15, 0.1]}>
          <sphereGeometry args={[0.32, 10, 10]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'bush') {
    return (
      <group>
        <mesh castShadow position={[0, 0.28, 0]}>
          <sphereGeometry args={[0.32, 10, 10]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0.2, 0.22, 0.08]}>
          <sphereGeometry args={[0.22, 10, 10]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'rock') {
    return (
      <mesh castShadow position={[0, 0.22, 0]} scale={[1, 0.7, 0.85]}>
        <dodecahedronGeometry args={[0.35, 0]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'flower') {
    return (
      <group>
        <mesh castShadow position={[0, 0.2, 0]}>
          <cylinderGeometry args={[0.02, 0.02, 0.4, 6]} />
          <meshStandardMaterial color="#237804" />
        </mesh>
        <mesh castShadow position={[0, 0.42, 0]}>
          <sphereGeometry args={[0.1, 10, 10]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'pine') {
    return (
      <group>
        <mesh castShadow position={[0, 0.4, 0]}>
          <cylinderGeometry args={[0.08, 0.12, 0.8, 8]} />
          <meshStandardMaterial color="#613400" />
        </mesh>
        {[0.9, 1.25, 1.55].map((y, i) => (
          <mesh key={y} castShadow position={[0, y, 0]}>
            <coneGeometry args={[0.55 - i * 0.12, 0.55, 8]} />
            <Surface object={object} />
          </mesh>
        ))}
      </group>
    );
  }
  if (kind === 'palm') {
    return (
      <group>
        <mesh castShadow position={[0, 0.8, 0]} rotation={[0.08, 0, 0]}>
          <cylinderGeometry args={[0.07, 0.12, 1.6, 8]} />
          <meshStandardMaterial color="#ad6800" />
        </mesh>
        {[0, 1, 2, 3].map((i) => (
          <mesh key={i} castShadow position={[Math.cos((i * Math.PI) / 2) * 0.35, 1.65, Math.sin((i * Math.PI) / 2) * 0.35]} rotation={[0.8, (i * Math.PI) / 2, 0]}>
            <boxGeometry args={[0.55, 0.04, 0.16]} />
            <Surface object={object} />
          </mesh>
        ))}
      </group>
    );
  }
  if (kind === 'cactus') {
    return (
      <group>
        <mesh castShadow position={[0, 0.55, 0]}>
          <cylinderGeometry args={[0.12, 0.14, 1.1, 10]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0.22, 0.7, 0]} rotation={[0, 0, 1.1]}>
          <cylinderGeometry args={[0.07, 0.07, 0.4, 8]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'grass') {
    return (
      <group>
        {[-0.12, 0, 0.14, -0.06, 0.08].map((x, i) => (
          <mesh key={i} castShadow position={[x, 0.14, (i % 2) * 0.08]} rotation={[0.15, 0, x]}>
            <coneGeometry args={[0.03, 0.32, 5]} />
            <Surface object={object} />
          </mesh>
        ))}
      </group>
    );
  }
  if (kind === 'mountain') {
    return (
      <mesh castShadow position={[0, 0.7, 0]}>
        <coneGeometry args={[1.1, 1.4, 5]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'water') {
    return (
      <mesh receiveShadow position={[0, 0.02, 0]}>
        <boxGeometry args={[2.4, 0.04, 2.4]} />
        <meshStandardMaterial color={object.color} transparent opacity={0.55} metalness={0.3} roughness={0.15} />
      </mesh>
    );
  }
  if (kind === 'cloud') {
    return (
      <group>
        {[[0, 1.4, 0], [0.35, 1.35, 0.1], [-0.32, 1.32, -0.05]].map(([x, y, z], i) => (
          <mesh key={i} position={[x, y, z]}>
            <sphereGeometry args={[0.28 - i * 0.03, 12, 12]} />
            <meshStandardMaterial color={object.color} roughness={1} />
          </mesh>
        ))}
      </group>
    );
  }
  if (kind === 'mushroom') {
    return (
      <group>
        <mesh castShadow position={[0, 0.16, 0]}>
          <cylinderGeometry args={[0.05, 0.06, 0.28, 8]} />
          <meshStandardMaterial color="#fff2e8" />
        </mesh>
        <mesh castShadow position={[0, 0.32, 0]}>
          <sphereGeometry args={[0.16, 12, 10, 0, Math.PI * 2, 0, Math.PI / 2]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'car') {
    return (
      <group>
        <mesh castShadow position={[0, 0.28, 0]}>
          <boxGeometry args={[1.6, 0.28, 0.7]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[-0.1, 0.5, 0]}>
          <boxGeometry args={[0.8, 0.24, 0.64]} />
          <Surface object={object} />
        </mesh>
        {[[-0.48, -0.32], [-0.48, 0.32], [0.48, -0.32], [0.48, 0.32]].map(([x, z], i) => (
          <mesh key={i} castShadow position={[x, 0.14, z]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.14, 0.14, 0.1, 10]} />
            <meshStandardMaterial color="#222" />
          </mesh>
        ))}
      </group>
    );
  }
  if (kind === 'bike') {
    return (
      <group>
        <mesh castShadow position={[-0.32, 0.28, 0]} rotation={[0, 0, Math.PI / 2]}>
          <torusGeometry args={[0.22, 0.03, 8, 16]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0.32, 0.28, 0]} rotation={[0, 0, Math.PI / 2]}>
          <torusGeometry args={[0.22, 0.03, 8, 16]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 0.42, 0]} rotation={[0, 0, 0.35]}>
          <cylinderGeometry args={[0.02, 0.02, 0.7, 6]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'truck') {
    return (
      <group>
        <mesh castShadow position={[-0.55, 0.42, 0]}>
          <boxGeometry args={[0.7, 0.55, 0.7]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0.45, 0.38, 0]}>
          <boxGeometry args={[1.2, 0.48, 0.72]} />
          <Surface object={object} />
        </mesh>
        {[[-0.55, -0.32], [-0.55, 0.32], [0.55, -0.32], [0.55, 0.32]].map(([x, z], i) => (
          <mesh key={i} castShadow position={[x, 0.14, z]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.14, 0.14, 0.1, 10]} />
            <meshStandardMaterial color="#222" />
          </mesh>
        ))}
      </group>
    );
  }
  if (kind === 'bus') {
    return (
      <group>
        <mesh castShadow position={[0, 0.55, 0]}>
          <boxGeometry args={[2.2, 0.9, 0.75]} />
          <Surface object={object} />
        </mesh>
        {[-0.7, 0, 0.7].map((x) => (
          <mesh key={x} castShadow position={[x, 0.14, 0.32]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.14, 0.14, 0.1, 10]} />
            <meshStandardMaterial color="#222" />
          </mesh>
        ))}
      </group>
    );
  }
  if (kind === 'motorcycle') {
    return (
      <group>
        {[-0.28, 0.28].map((x) => (
          <mesh key={x} castShadow position={[x, 0.22, 0]} rotation={[0, 0, Math.PI / 2]}>
            <torusGeometry args={[0.16, 0.035, 8, 14]} />
            <meshStandardMaterial color="#222" />
          </mesh>
        ))}
        <mesh castShadow position={[0, 0.32, 0]}>
          <boxGeometry args={[0.45, 0.12, 0.16]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'boat') {
    return (
      <group>
        <mesh castShadow position={[0, 0.12, 0]}>
          <boxGeometry args={[1.6, 0.18, 0.55]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 0.32, 0]}>
          <boxGeometry args={[0.55, 0.22, 0.35]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'airplane') {
    return (
      <group>
        <mesh castShadow position={[0, 0.35, 0]} rotation={[0, 0, Math.PI / 2]}>
          <capsuleGeometry args={[0.12, 1.1, 6, 12]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 0.32, 0]}>
          <boxGeometry args={[0.35, 0.04, 1.4]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[-0.5, 0.45, 0]}>
          <boxGeometry args={[0.08, 0.28, 0.35]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'crate') {
    return (
      <mesh castShadow position={[0, 0.28, 0]}>
        <boxGeometry args={[0.55, 0.55, 0.55]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'barrel') {
    return (
      <mesh castShadow position={[0, 0.4, 0]}>
        <cylinderGeometry args={[0.28, 0.28, 0.8, 14]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'bottle') {
    return (
      <group>
        <mesh castShadow position={[0, 0.22, 0]}>
          <cylinderGeometry args={[0.08, 0.1, 0.36, 10]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 0.46, 0]}>
          <cylinderGeometry args={[0.035, 0.05, 0.16, 8]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'book') {
    return (
      <mesh castShadow position={[0, 0.04, 0]}>
        <boxGeometry args={[0.28, 0.06, 0.38]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'cup') {
    return (
      <mesh castShadow position={[0, 0.1, 0]}>
        <cylinderGeometry args={[0.08, 0.07, 0.16, 12]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'phone') {
    return (
      <mesh castShadow position={[0, 0.08, 0]} rotation={[-0.4, 0, 0]}>
        <boxGeometry args={[0.12, 0.22, 0.02]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'laptop') {
    return (
      <group>
        <mesh castShadow position={[0, 0.02, 0.08]}>
          <boxGeometry args={[0.42, 0.02, 0.28]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 0.14, -0.08]} rotation={[-0.4, 0, 0]}>
          <boxGeometry args={[0.42, 0.26, 0.02]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'bag') {
    return (
      <group>
        <mesh castShadow position={[0, 0.22, 0]}>
          <boxGeometry args={[0.28, 0.36, 0.16]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 0.44, 0]}>
          <torusGeometry args={[0.08, 0.015, 6, 12]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'suitcase') {
    return (
      <mesh castShadow position={[0, 0.22, 0]}>
        <boxGeometry args={[0.45, 0.32, 0.18]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'plate') {
    return (
      <mesh castShadow position={[0, 0.03, 0]}>
        <cylinderGeometry args={[0.18, 0.16, 0.03, 20]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'vase') {
    return (
      <mesh castShadow position={[0, 0.22, 0]}>
        <cylinderGeometry args={[0.08, 0.12, 0.44, 12]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'trash') {
    return (
      <mesh castShadow position={[0, 0.28, 0]}>
        <cylinderGeometry args={[0.18, 0.15, 0.55, 12]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'sign') {
    return (
      <group>
        <mesh castShadow position={[0, 0.45, 0]}>
          <cylinderGeometry args={[0.03, 0.03, 0.9, 8]} />
          <meshStandardMaterial color="#8c8c8c" />
        </mesh>
        <mesh castShadow position={[0, 1.0, 0]}>
          <boxGeometry args={[0.55, 0.32, 0.04]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'ball') {
    return (
      <mesh castShadow position={[0, 0.18, 0]}>
        <sphereGeometry args={[0.18, 16, 16]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'camera_prop') {
    return (
      <group>
        <mesh castShadow position={[0, 0.18, 0]}>
          <boxGeometry args={[0.28, 0.16, 0.18]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0.16, 0.18, 0]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.07, 0.08, 0.12, 12]} />
          <meshStandardMaterial color="#111" />
        </mesh>
      </group>
    );
  }
  if (kind === 'umbrella') {
    return (
      <group>
        <mesh castShadow position={[0, 0.7, 0]}>
          <cylinderGeometry args={[0.015, 0.015, 1.2, 6]} />
          <meshStandardMaterial color="#8c8c8c" />
        </mesh>
        <mesh castShadow position={[0, 1.22, 0]}>
          <sphereGeometry args={[0.42, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2.4]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'screen') {
    return (
      <group>
        <mesh castShadow position={[0, 0.7, 0]}>
          <boxGeometry args={[1.2, 0.72, 0.06]} />
          <meshStandardMaterial color="#111" metalness={0.4} roughness={0.3} />
        </mesh>
        <mesh position={[0, 0.7, 0.034]}>
          <planeGeometry args={[1.08, 0.6]} />
          <meshStandardMaterial color="#1677ff" emissive="#1677ff" emissiveIntensity={0.35} />
        </mesh>
      </group>
    );
  }
  if (kind === 'marker') {
    return (
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <ringGeometry args={[0.28, 0.38, 24]} />
        <meshStandardMaterial color={object.color} emissive={object.color} emissiveIntensity={0.4} />
      </mesh>
    );
  }
  if (kind === 'flag') {
    return (
      <group>
        <mesh castShadow position={[0, 0.85, 0]}>
          <cylinderGeometry args={[0.03, 0.03, 1.7, 8]} />
          <meshStandardMaterial color="#8c8c8c" />
        </mesh>
        <mesh castShadow position={[0.32, 1.4, 0]}>
          <boxGeometry args={[0.55, 0.32, 0.02]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'fire') {
    return (
      <group>
        <mesh position={[0, 0.22, 0]}>
          <coneGeometry args={[0.16, 0.4, 7]} />
          <meshStandardMaterial color={object.color} emissive="#fa541c" emissiveIntensity={1.2} />
        </mesh>
        <mesh position={[0, 0.38, 0]}>
          <coneGeometry args={[0.08, 0.28, 6]} />
          <meshStandardMaterial color="#ffec3d" emissive="#ffec3d" emissiveIntensity={1} />
        </mesh>
      </group>
    );
  }
  if (kind === 'smoke') {
    return (
      <group>
        {[0.25, 0.5, 0.78].map((y, i) => (
          <mesh key={y} position={[i * 0.05, y, 0]}>
            <sphereGeometry args={[0.16 + i * 0.04, 10, 10]} />
            <meshStandardMaterial color={object.color} transparent opacity={0.35} roughness={1} />
          </mesh>
        ))}
      </group>
    );
  }
  if (kind === 'hologram') {
    return (
      <mesh position={[0, 0.7, 0]}>
        <cylinderGeometry args={[0.35, 0.35, 1.3, 16, 1, true]} />
        <meshStandardMaterial color={object.color} emissive={object.color} emissiveIntensity={0.6} transparent opacity={0.35} />
      </mesh>
    );
  }
  if (kind === 'light_point') {
    return (
      <group>
        <mesh>
          <sphereGeometry args={[0.12, 12, 12]} />
          <meshStandardMaterial color={object.color} emissive={object.color} emissiveIntensity={1} />
        </mesh>
        <pointLight color={object.color} intensity={object.lightIntensity ?? 8} distance={18} />
      </group>
    );
  }
  if (kind === 'light_spot') {
    return (
      <group>
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <coneGeometry args={[0.14, 0.28, 10]} />
          <meshStandardMaterial color={object.color} />
        </mesh>
        <spotLight
          color={object.color}
          intensity={object.lightIntensity ?? 12}
          angle={0.5}
          penumbra={0.35}
          distance={20}
          position={[0, 0, 0]}
        />
      </group>
    );
  }
  if (kind === 'light_directional') {
    return (
      <group>
        <mesh>
          <boxGeometry args={[0.2, 0.2, 0.04]} />
          <meshStandardMaterial color={object.color} emissive={object.color} />
        </mesh>
        <directionalLight color={object.color} intensity={object.lightIntensity ?? 1.4} />
      </group>
    );
  }
  if (kind === 'light_area') {
    return (
      <group>
        <mesh>
          <planeGeometry args={[0.7, 0.4]} />
          <meshStandardMaterial color={object.color} emissive={object.color} emissiveIntensity={1} side={2} />
        </mesh>
        <pointLight color={object.color} intensity={object.lightIntensity ?? 6} distance={16} />
      </group>
    );
  }

  if (kind === 'hemisphere') {
    return (
      <mesh castShadow position={[0, 0.02, 0]}>
        <sphereGeometry args={[0.5, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'tube') {
    return (
      <mesh castShadow position={[0, 0.35, 0]} rotation={[0, 0, Math.PI / 2]}>
        <torusGeometry args={[0.35, 0.08, 10, 24]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'star') {
    return (
      <group>
        <mesh castShadow position={[0, 0.4, 0]}>
          <octahedronGeometry args={[0.28, 0]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0, 0.4, 0]} rotation={[0, 0, Math.PI / 4]}>
          <octahedronGeometry args={[0.28, 0]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'arrow') {
    return (
      <group>
        <mesh castShadow position={[0, 0.18, 0]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.06, 0.06, 0.7, 10]} />
          <Surface object={object} />
        </mesh>
        <mesh castShadow position={[0.42, 0.18, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[0.14, 0.28, 10]} />
          <Surface object={object} />
        </mesh>
      </group>
    );
  }
  if (kind === 'roundedBox') {
    return (
      <mesh castShadow position={[0, 0.35, 0]}>
        <boxGeometry args={[0.7, 0.7, 0.7]} />
        <Surface object={object} />
      </mesh>
    );
  }

  if (kind === 'sphere') {
    return (
      <mesh castShadow position={[0, 0.5, 0]}>
        <sphereGeometry args={[0.5, 24, 24]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'cylinder') {
    return (
      <mesh castShadow position={[0, 0.5, 0]}>
        <cylinderGeometry args={[0.4, 0.4, 1, 20]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'cone' || kind === 'pyramid') {
    return (
      <mesh castShadow position={[0, 0.5, 0]}>
        <coneGeometry args={[0.45, 1, kind === 'pyramid' ? 4 : 20]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'capsule') {
    return (
      <mesh castShadow position={[0, 0.9, 0]}>
        <capsuleGeometry args={[0.35, 1.1, 8, 16]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'plane') {
    return (
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[2, 2]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'torus') {
    return (
      <mesh castShadow position={[0, 0.35, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.35, 0.12, 12, 24]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'ring') {
    return (
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
        <ringGeometry args={[0.2, 0.5, 24]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'tetrahedron') {
    return (
      <mesh castShadow position={[0, 0.4, 0]}>
        <tetrahedronGeometry args={[0.55, 0]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'octahedron') {
    return (
      <mesh castShadow position={[0, 0.5, 0]}>
        <octahedronGeometry args={[0.5, 0]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'dodecahedron') {
    return (
      <mesh castShadow position={[0, 0.5, 0]}>
        <dodecahedronGeometry args={[0.45, 0]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'icosahedron') {
    return (
      <mesh castShadow position={[0, 0.5, 0]}>
        <icosahedronGeometry args={[0.48, 0]} />
        <Surface object={object} />
      </mesh>
    );
  }
  if (kind === 'torusKnot') {
    return (
      <mesh castShadow position={[0, 0.45, 0]}>
        <torusKnotGeometry args={[0.28, 0.08, 80, 12]} />
        <Surface object={object} />
      </mesh>
    );
  }

  return (
    <mesh castShadow position={[0, 0.4, 0]}>
      <boxGeometry args={[0.8, 0.8, 0.8]} />
      <Surface object={object} />
    </mesh>
  );
}
