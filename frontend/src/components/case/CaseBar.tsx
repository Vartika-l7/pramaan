import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Search,
  Cpu,
  Layers,
  ChevronDown,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { fetchIntegrityStatus, verifyIntegrity, fetchSystemCapabilities, triggerFullAnalysis } from '../../lib/api';
import { useAppStore } from '../../lib/store';

export const CaseBar: React.FC = () => {
  const queryClient = useQueryClient();
  const caseId = useAppStore((state) => state.caseId);
  const setCommandPaletteOpen = useAppStore((state) => state.setCommandPaletteOpen);
  const isAnalyzing = useAppStore((state) => state.isAnalyzing);
  const setIsAnalyzing = useAppStore((state) => state.setIsAnalyzing);

  const [capsOpen, setCapsOpen] = useState(false);

  const { data: integrity, isLoading } = useQuery({
    queryKey: ['integrityStatus'],
    queryFn: fetchIntegrityStatus,
    refetchInterval: 10000,
  });

  const { data: caps } = useQuery({
    queryKey: ['systemCapabilities'],
    queryFn: fetchSystemCapabilities,
  });

  const verifyMutation = useMutation({
    mutationFn: verifyIntegrity,
    onSuccess: (data) => {
      queryClient.setQueryData(['integrityStatus'], data);
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: triggerFullAnalysis,
    onMutate: () => setIsAnalyzing(true),
    onSettled: () => {
      setIsAnalyzing(false);
      queryClient.invalidateQueries();
    },
  });

  const isIntact = integrity?.intact ?? true;
  const rootShort = integrity?.merkle_root
    ? `${integrity.merkle_root.slice(0, 8)}...${integrity.merkle_root.slice(-6)}`
    : 'genesis';

  return (
    <header className="h-16 border-b border-border bg-surface-raised px-6 flex items-center justify-between gap-4 select-none sticky top-0 z-30">
      {/* Left: Case Pill & Synthetic Label */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="font-sans text-xs font-bold text-ink-tertiary uppercase tracking-wider">
            Case
          </span>
          <span className="font-mono text-sm font-bold text-ink bg-surface px-2.5 py-1 rounded-md border border-border">
            {caseId}
          </span>
        </div>

        <span className="font-sans text-xs font-bold uppercase tracking-wider text-ochre-dark bg-ochre-light px-2.5 py-1 rounded-full border border-ochre/30">
          Synthetic Dossier
        </span>
      </div>

      {/* Center: The Integrity Seal */}
      <div className="flex items-center">
        <div
          className={`flex items-center gap-2.5 px-3.5 py-1.5 rounded-full border text-xs font-sans transition-all ${
            isIntact
              ? 'bg-lime-light border-lime-dark/30 text-lime-dark'
              : 'bg-tomato-light border-tomato text-tomato font-bold shadow-xs'
          }`}
        >
          {isIntact ? (
            <ShieldCheck className="w-4 h-4 text-lime-dark shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-tomato shrink-0 animate-bounce" />
          )}

          {isLoading ? (
            <span className="text-xs font-medium">Verifying chain...</span>
          ) : isIntact ? (
            <div className="flex items-center gap-2 text-xs">
              <span className="font-bold tracking-wide uppercase">Chain Intact</span>
              <span className="text-border-strong">·</span>
              <span className="text-ink font-medium">{integrity?.total_exhibits ?? 0} exhibits</span>
              <span className="text-border-strong">·</span>
              <span className="text-ink-secondary font-mono text-2xs">
                root <span className="text-ink font-semibold">{rootShort}</span>
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-xs">
              <span className="uppercase tracking-wide font-bold">Tampering Detected</span>
              <span className="text-border-strong">·</span>
              <span>{integrity?.failed_exhibit ? `Exhibit: ${integrity.failed_exhibit}` : 'Custody log invalid'}</span>
            </div>
          )}

          <button
            type="button"
            disabled={verifyMutation.isPending}
            onClick={() => verifyMutation.mutate()}
            title="Recompute all SHA-256 digests and audit hash chain integrity"
            className="ml-1 hover:bg-black/5 active:bg-black/10 px-2 py-0.5 rounded-full text-2xs font-sans font-bold uppercase tracking-wider border border-current/20 cursor-pointer flex items-center gap-1 transition-colors"
          >
            <RefreshCw
              className={`w-3 h-3 ${verifyMutation.isPending ? 'animate-spin' : ''}`}
            />
            <span>Verify</span>
          </button>
        </div>
      </div>

      {/* Right: Actions, Capabilities, and Search */}
      <div className="flex items-center gap-3 relative">
        <button
          type="button"
          disabled={isAnalyzing}
          onClick={() => analyzeMutation.mutate()}
          className="flex items-center gap-2 px-3.5 py-1.5 bg-cobalt hover:bg-cobalt-dark text-white text-xs font-sans font-semibold rounded-lg transition-colors shadow-xs disabled:opacity-50 cursor-pointer"
        >
          <Layers className={`w-3.5 h-3.5 ${isAnalyzing ? 'animate-spin' : ''}`} />
          <span>{isAnalyzing ? 'Analyzing Pipeline...' : 'Run Pipeline'}</span>
        </button>

        {/* Forensic Capabilities Dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setCapsOpen(!capsOpen)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-sans font-medium text-ink-secondary hover:text-ink border border-border rounded-lg bg-surface hover:bg-ivory-dark transition-colors cursor-pointer"
          >
            <Cpu className="w-3.5 h-3.5 text-cobalt" />
            <span>Engines</span>
            <ChevronDown className="w-3 h-3 text-ink-tertiary" />
          </button>

          {capsOpen && (
            <div className="absolute right-0 mt-2 w-80 bg-surface-raised border border-border rounded-xl shadow-xl p-4 text-xs z-50 animate-in fade-in zoom-in-95">
              <div className="flex items-center justify-between border-b border-border pb-2.5 mb-3">
                <span className="font-sans text-xs uppercase font-bold tracking-wider text-ink">
                  Active Forensic Engines
                </span>
                <span className="text-2xs font-sans font-bold text-lime-dark bg-lime-light px-2 py-0.5 rounded-full border border-lime-dark/30">
                  OFFLINE
                </span>
              </div>
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-ink-secondary">Local AI (Ollama):</span>
                  <span
                    className={`font-sans font-semibold flex items-center gap-1 ${
                      caps?.ollama.available ? 'text-lime-dark' : 'text-ochre-dark'
                    }`}
                  >
                    {caps?.ollama.available ? (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5" />
                    )}
                    {caps?.ollama.available ? 'Connected' : 'Deterministic Mode'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-ink-secondary">OCR Engine (Tesseract):</span>
                  <span
                    className={`font-sans font-semibold flex items-center gap-1 ${
                      caps?.tesseract.available ? 'text-lime-dark' : 'text-ink-tertiary'
                    }`}
                  >
                    {caps?.tesseract.available ? (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5" />
                    )}
                    {caps?.tesseract.available ? 'Ready (hin+eng)' : 'Unavailable'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-ink-secondary">Bank PDF Engine:</span>
                  <span className="font-sans font-semibold text-ink">
                    {caps?.pdf_engine.engine || 'pdfplumber + reportlab'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-ink-secondary">IndicNER Pipeline:</span>
                  <span className="font-sans font-medium text-ink-secondary">
                    {caps?.indic_ner.enabled ? 'Active (AI4Bharat)' : 'Rule-Based Gazetteer'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Command Palette Trigger */}
        <button
          type="button"
          onClick={() => setCommandPaletteOpen(true)}
          className="flex items-center gap-2 px-2.5 py-1.5 text-xs text-ink-secondary border border-border rounded-lg bg-surface hover:text-ink hover:border-ink-tertiary transition-colors cursor-pointer"
        >
          <Search className="w-3.5 h-3.5 text-ink-tertiary" />
          <kbd className="font-mono text-2xs bg-surface-raised border border-border px-1.5 py-0.5 rounded text-ink-secondary">
            ⌘K
          </kbd>
        </button>
      </div>
    </header>
  );
};
