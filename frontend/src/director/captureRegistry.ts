import * as THREE from 'three';

export interface CaptureContext {
  gl: THREE.WebGLRenderer;
  scene: THREE.Scene;
}

let ctx: CaptureContext | null = null;
let capturing = false;
const listeners = new Set<(value: boolean) => void>();

export function registerCaptureContext(next: CaptureContext | null): void {
  ctx = next;
}

export function getCaptureContext(): CaptureContext | null {
  return ctx;
}

export function isCapturing(): boolean {
  return capturing;
}

export function setCapturing(value: boolean): void {
  capturing = value;
  listeners.forEach((fn) => fn(value));
}

export function subscribeCapturing(fn: (value: boolean) => void): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}
