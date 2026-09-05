import * as THREE from 'three';
import type { CharacterAsset } from './types';

const SKIN_MESH = /head|body|skin|wolf3d_head|wolf3d_body/i;
const HAIR_MESH = /hair|wolf3d_hair/i;
const OUTFIT_MESH = /outfit|cloth|top|bottom|footwear|shirt|pant|boot|jacket/i;
const GLASS_MESH = /glass|wolf3d_glasses/i;

function tintMaterial(mat: THREE.Material, hex: string): void {
  if (!hex) return;
  const color = new THREE.Color(hex);
  const apply = (m: THREE.Material) => {
    const anyMat = m as THREE.MeshStandardMaterial;
    if (anyMat.color) anyMat.color.lerp(color, 0.55);
    anyMat.needsUpdate = true;
  };
  apply(mat);
}

export function applyCharacterAppearance(root: THREE.Object3D, asset: CharacterAsset): void {
  const { appearance } = asset;
  const heightCm = asset.body?.heightCm ?? asset.heightCm;
  const bodyType = asset.body?.bodyType ?? asset.bodyType;
  const heightScale = Math.max(0.55, heightCm / 170);
  const bodyXz = bodyType === 'slim' ? 0.88 : bodyType === 'heavy' ? 1.16 : 1;
  root.scale.set(heightScale * bodyXz, heightScale, heightScale * bodyXz);

  root.traverse((child) => {
    if (!(child instanceof THREE.Mesh) && !(child instanceof THREE.SkinnedMesh)) return;
    const name = child.name || '';
    if (GLASS_MESH.test(name)) {
      child.visible = appearance.glassesVisible;
    }
    const mats = Array.isArray(child.material) ? child.material : [child.material];
    mats.forEach((mat) => {
      if (!mat) return;
      const cloned = mat.clone();
      if (SKIN_MESH.test(name) && appearance.skinColor) tintMaterial(cloned, appearance.skinColor);
      if (HAIR_MESH.test(name) && appearance.hairColor) tintMaterial(cloned, appearance.hairColor);
      if (OUTFIT_MESH.test(name) && appearance.outfitColor) tintMaterial(cloned, appearance.outfitColor);
      child.material = cloned;
    });
  });
}

export function findAccessoryFlags(root: THREE.Object3D): { glasses: boolean } {
  let glasses = false;
  root.traverse((child) => {
    if (GLASS_MESH.test(child.name || '')) glasses = true;
  });
  return { glasses };
}
