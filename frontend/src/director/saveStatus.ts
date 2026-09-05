import { create } from 'zustand';

export type SavePhase = 'saved' | 'saving' | 'error';

export const useSaveStatus = create<{
  phase: SavePhase;
  error: string | null;
  markSaving: () => void;
  markSaved: () => void;
  markError: (message: string) => void;
}>((set) => ({
  phase: 'saved',
  error: null,
  markSaving: () => set({ phase: 'saving', error: null }),
  markSaved: () => set({ phase: 'saved', error: null }),
  markError: (message) => set({ phase: 'error', error: message }),
}));
