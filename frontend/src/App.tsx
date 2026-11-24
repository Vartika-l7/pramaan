import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { CaseBar } from './components/case/CaseBar';
import { LeftRail } from './components/navigation/LeftRail';
import { SourceViewer } from './components/evidence/SourceViewer';

import { OverviewPage } from './pages/OverviewPage';
import { EvidenceVaultPage } from './pages/EvidenceVaultPage';
import { ReviewAndReportPage } from './pages/ReviewAndReportPage';
import { KnowledgeGraphPage } from './pages/KnowledgeGraphPage';
import { ReconstructionPage } from './pages/ReconstructionPage';
import { AssistantPage } from './pages/AssistantPage';

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
        <div className="flex h-screen w-screen overflow-hidden pramaan-canvas text-ink">
          <LeftRail />

          <div className="flex-1 flex flex-col h-full overflow-hidden">
            <CaseBar />

            <main className="flex-1 overflow-y-auto px-6 py-7 lg:px-10 lg:py-8">
              <Routes>
                <Route path="/" element={<OverviewPage />} />
                <Route path="/evidence" element={<EvidenceVaultPage />} />
                <Route path="/review" element={<ReviewAndReportPage />} />
                <Route path="/package" element={<Navigate to="/review?step=package" replace />} />
                <Route path="/graph" element={<KnowledgeGraphPage />} />
                <Route path="/reconstruction" element={<ReconstructionPage />} />
                <Route path="/events" element={<Navigate to="/reconstruction" replace />} />
                <Route path="/assistant" element={<AssistantPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </main>
          </div>

          <SourceViewer />
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
};
