import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { CaseBar } from './components/case/CaseBar';
import { LeftRail } from './components/navigation/LeftRail';
import { SourceViewer } from './components/evidence/SourceViewer';
import { CommandPalette } from './components/command/CommandPalette';

import { OverviewPage } from './pages/OverviewPage';
import { EvidenceVaultPage } from './pages/EvidenceVaultPage';
import { EntitiesPage } from './pages/EntitiesPage';
import { KnowledgeGraphPage } from './pages/KnowledgeGraphPage';
import { EventSequencePage } from './pages/EventSequencePage';
import { AuthenticityPage } from './pages/AuthenticityPage';
import { ReviewQueuePage } from './pages/ReviewQueuePage';
import { VerifierChallengePage } from './pages/VerifierChallengePage';
import { CasePackagePage } from './pages/CasePackagePage';
import { MetricsPage } from './pages/MetricsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="flex h-screen w-screen overflow-hidden bg-ivory text-ink">
          {/* Persistent Left Rail */}
          <LeftRail />

          {/* Main Content Area */}
          <div className="flex-1 flex flex-col h-full overflow-hidden">
            {/* Top Case Bar */}
            <CaseBar />

            {/* Scrollable Page Body */}
            <main className="flex-1 overflow-y-auto p-6">
              <Routes>
                <Route path="/" element={<OverviewPage />} />
                <Route path="/evidence" element={<EvidenceVaultPage />} />
                <Route path="/entities" element={<EntitiesPage />} />
                <Route path="/graph" element={<KnowledgeGraphPage />} />
                <Route path="/events" element={<EventSequencePage />} />
                <Route path="/authenticity" element={<AuthenticityPage />} />
                <Route path="/review" element={<ReviewQueuePage />} />
                <Route path="/verifier" element={<VerifierChallengePage />} />
                <Route path="/package" element={<CasePackagePage />} />
                <Route path="/metrics" element={<MetricsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </main>
          </div>

          {/* Global Source Viewer Slide-over */}
          <SourceViewer />

          {/* Command Palette */}
          <CommandPalette />
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
};
