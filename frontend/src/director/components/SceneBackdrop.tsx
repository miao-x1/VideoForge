import { useLayoutEffect, useMemo } from 'react';
import { useTexture } from '@react-three/drei';
import { SRGBColorSpace } from 'three';
import { mediaUrl } from '../../api/client';

function freshMediaUrl(raw: string): string {
  if (!raw || raw.startsWith('data:') || raw.startsWith('blob:')) return raw;
  try {
    const url = new URL(raw, window.location.origin);
    url.searchParams.delete('access_token');
    return mediaUrl(`${url.pathname}${url.search}`);
  } catch {
    return mediaUrl(raw);
  }
}

export default function SceneBackdrop({ url }: { url: string }) {
  const texture = useTexture(freshMediaUrl(url));
  const { width, height } = useMemo(() => {
    const img = texture.image as { width?: number; height?: number } | undefined;
    const ratio = img?.width && img?.height ? img.width / img.height : 16 / 9;
    const h = 8;
    return { width: h * ratio, height: h };
  }, [texture.image]);

  useLayoutEffect(() => {
    texture.colorSpace = SRGBColorSpace;
    texture.needsUpdate = true;
  }, [texture]);

  return (
    <mesh position={[0, height / 2, -5.4]} receiveShadow>
      <planeGeometry args={[width, height]} />
      <meshBasicMaterial map={texture} toneMapped={false} />
    </mesh>
  );
}
