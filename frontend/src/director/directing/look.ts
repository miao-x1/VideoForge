import type { Atmosphere, SceneEnvironment, ShotSize, CameraAngle, Vec3, Weather } from '../types';
import { lookAtRotation } from '../types';

export const SHOT_SIZE_LABEL: Record<ShotSize, string> = {
  extreme_long: '远景',
  long: '全景',
  full: '全身',
  medium: '中景',
  close: '近景',
  extreme_close: '特写',
};

export const ANGLE_LABEL: Record<CameraAngle, string> = {
  eye: '平视',
  high: '俯拍',
  low: '仰拍',
  side: '侧拍',
};

export const WEATHER_LABEL: Record<Weather, string> = {
  clear: '晴',
  cloudy: '阴',
  rain: '雨天',
  snow: '雪',
  fog: '雾',
};

export const ATMOSPHERE_LABEL: Record<Atmosphere, string> = {
  neutral: '日常',
  tense: '紧张',
  romantic: '浪漫',
  oppressive: '压抑',
  joyful: '明快',
  melancholy: '伤感',
};

const SIZE_FRAME: Record<ShotSize, { distance: number; height: number; fov: number; focal: number }> = {
  extreme_long: { distance: 14, height: 3.8, fov: 50, focal: 24 },
  long: { distance: 9, height: 2.4, fov: 45, focal: 28 },
  full: { distance: 6.4, height: 1.8, fov: 40, focal: 35 },
  medium: { distance: 4.2, height: 1.55, fov: 38, focal: 40 },
  close: { distance: 2.4, height: 1.5, fov: 32, focal: 50 },
  extreme_close: { distance: 1.35, height: 1.52, fov: 28, focal: 85 },
};

export function environmentLook(
  weather: Weather,
  timeOfDay: string,
  atmosphere: Atmosphere,
): Partial<SceneEnvironment> {
  let sky = '#1a1a2c';
  let ambient = 0.55;
  if (timeOfDay === 'dawn') {
    sky = '#2a2438';
    ambient = 0.48;
  } else if (timeOfDay === 'dusk') {
    sky = '#3a2030';
    ambient = 0.42;
  } else if (timeOfDay === 'night') {
    sky = '#0a1020';
    ambient = 0.28;
  } else if (timeOfDay === 'day') {
    sky = '#87a0c4';
    ambient = 0.7;
  }
  if (weather === 'rain') {
    sky = timeOfDay === 'night' ? '#070b14' : '#4a5568';
    ambient *= 0.82;
  } else if (weather === 'fog') {
    sky = '#6b7280';
    ambient *= 0.9;
  } else if (weather === 'snow') {
    sky = timeOfDay === 'night' ? '#1a2030' : '#c5d0dc';
    ambient *= 1.05;
  } else if (weather === 'cloudy') {
    ambient *= 0.88;
  }
  if (atmosphere === 'oppressive' || atmosphere === 'tense') ambient *= 0.78;
  if (atmosphere === 'romantic') {
    sky = timeOfDay === 'night' ? '#1a1228' : '#c4a090';
    ambient *= 1.05;
  }
  if (atmosphere === 'joyful') ambient *= 1.12;
  if (atmosphere === 'melancholy') ambient *= 0.85;
  return { sky, ambientIntensity: Number(ambient.toFixed(2)), weather, timeOfDay, atmosphere };
}

export function frameCamera(
  size: ShotSize,
  angle: CameraAngle,
  target: Vec3 = [0, 1.45, 0],
): { position: Vec3; rotation: Vec3; fov: number; focalLength: number; shotSize: ShotSize; angle: CameraAngle } {
  const frame = SIZE_FRAME[size];
  let x = 0;
  let y = frame.height;
  let z = frame.distance;
  if (angle === 'high') y += 1.35;
  if (angle === 'low') y = Math.max(0.35, frame.height - 1.05);
  if (angle === 'side') {
    x = frame.distance * 0.55;
    z = frame.distance * 0.75;
  }
  const position: Vec3 = [target[0] + x, y, target[2] + z];
  return {
    position,
    rotation: lookAtRotation(position, target),
    fov: frame.fov,
    focalLength: frame.focal,
    shotSize: size,
    angle,
  };
}

export function centroidOf(points: Vec3[]): Vec3 {
  if (!points.length) return [0, 1.45, 0];
  const sum = points.reduce((acc, p) => [acc[0] + p[0], acc[1] + p[1], acc[2] + p[2]] as Vec3, [0, 0, 0]);
  return [sum[0] / points.length, sum[1] / points.length + 1.2, sum[2] / points.length];
}

export function distance2d(a: Vec3, b: Vec3): number {
  return Math.hypot(a[0] - b[0], a[2] - b[2]);
}

export function shotSizeFromFov(fov: number): ShotSize {
  if (fov <= 30) return 'extreme_close';
  if (fov <= 34) return 'close';
  if (fov <= 40) return 'medium';
  if (fov <= 44) return 'full';
  if (fov <= 48) return 'long';
  return 'extreme_long';
}
