import { useSyncExternalStore } from 'react';
import { isCapturing, subscribeCapturing } from '../captureRegistry';

export function useCapturing(): boolean {
  return useSyncExternalStore(subscribeCapturing, isCapturing, isCapturing);
}
