import { create } from 'zustand';

interface AppState {
  caseId: string;
  sourceViewerEventId: string | null;
  sourceViewerOpen: boolean;
  commandPaletteOpen: boolean;
  isAnalyzing: boolean;
  setCaseId: (id: string) => void;
  openSourceViewer: (eventId: string) => void;
  closeSourceViewer: () => void;
  setCommandPaletteOpen: (open: boolean) => void;
  setIsAnalyzing: (analyzing: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  caseId: 'PRM-2026-0042',
  sourceViewerEventId: null,
  sourceViewerOpen: false,
  commandPaletteOpen: false,
  isAnalyzing: false,
  setCaseId: (id) => set({ caseId: id }),
  openSourceViewer: (eventId) => set({ sourceViewerEventId: eventId, sourceViewerOpen: true }),
  closeSourceViewer: () => set({ sourceViewerOpen: false, sourceViewerEventId: null }),
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  setIsAnalyzing: (analyzing) => set({ isAnalyzing: analyzing }),
}));

