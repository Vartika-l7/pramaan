import { create } from 'zustand';

interface AppState {
  caseId: string;
  sourceViewerEventId: string | null;
  sourceViewerOpen: boolean;
  isAnalyzing: boolean;

  /* Linked-view selection across Graph, Reconstruction, and Assistant */
  selectedEntityId: string | null;
  selectedEventId: string | null;
  selectedLocationId: string | null;

  setCaseId: (id: string) => void;
  openSourceViewer: (eventId: string) => void;
  closeSourceViewer: () => void;
  setIsAnalyzing: (analyzing: boolean) => void;
  setSelectedEntityId: (id: string | null) => void;
  setSelectedEventId: (id: string | null) => void;
  setSelectedLocationId: (id: string | null) => void;
  clearLinkedSelection: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  caseId: 'PRM-2026-0042',
  sourceViewerEventId: null,
  sourceViewerOpen: false,
  isAnalyzing: false,
  selectedEntityId: null,
  selectedEventId: null,
  selectedLocationId: null,

  setCaseId: (id) => set({ caseId: id }),
  openSourceViewer: (eventId) =>
    set({ sourceViewerEventId: eventId, sourceViewerOpen: true, selectedEventId: eventId }),
  closeSourceViewer: () => set({ sourceViewerOpen: false, sourceViewerEventId: null }),
  setIsAnalyzing: (analyzing) => set({ isAnalyzing: analyzing }),
  setSelectedEntityId: (id) => set({ selectedEntityId: id }),
  setSelectedEventId: (id) => set({ selectedEventId: id }),
  setSelectedLocationId: (id) => set({ selectedLocationId: id }),
  clearLinkedSelection: () =>
    set({ selectedEntityId: null, selectedEventId: null, selectedLocationId: null }),
}));
