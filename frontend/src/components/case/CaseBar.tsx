import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
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

const QUICK_ROUTES = [
  { label: 'Overview', path: '/' },
  { label: 'Evidence', path: '/evidence' },
  { label: 'Review and Report', path: '/review' },
  { label: 'Knowledge Graph', path: '/graph' },
  { label: 'Reconstruction', path: '/reconstruction' },
  { label: 'Assistant', path: '/assistant' },
];

export const CaseBar: React.FC = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const caseId = useAppStore((state) => state.caseId);
  const isAnalyzing = useAppStore((state) => state.isAnalyzing);
  const setIsAnalyzing = useAppStore((state) => state.setIsAnalyzing);

  const [capsOpen, setCapsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchFocused, setSearchFocused] = useState(false);

  const { data: integrity, isLoading } = useQuery({
    queryKey: ['integrityStatus'],
    queryFn: fetchIntegrityStatus,
    refetchInterval: 15000,
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
    ? `${integrity.merkle_root.slice(0, 8)}…${integrity.merkle_root.slice(-4)}`
    : 'genesis';

  const filteredRoutes = searchQuery
    ? QUICK_ROUTES.filter((r) => r.label.toLowerCase().includes(searchQuery.toLowerCase()))
    : [];

  return (
    <header className="h-14 border-b border-border bg-panel px-5 flex items-center justify-between gap-3 select-none sticky top-0 z-30 whitespace-nowrap">
      {/* Left: Case ID & Synthetic case tag */}
      <div className="flex items-center gap-2.5 shrink-0">
        <span className="font-mono text-xs font-semibold text-ink bg-paper px-2.5 py-1 rounded border border-border-strong whitespace-nowrap">
          {caseId}
        </span>
        <span className="font-sans text-[11px] font-semibold uppercase tracking-wider text-amber bg-amber-light px-2.5 py-0.5 rounded border border-amber-border whitespace-nowrap">
          Synthetic case
        </span>
      </div>

      {/* Center: The Integrity Seal */}
      <div className="flex items-center shrink-0">
        <div
          className={`flex items-center gap-2 px-3 py-1 rounded border text-xs font-sans transition-colors duration-150 whitespace-nowrap ${
            isIntact
              ? 'bg-teal-light border-teal-border text-teal'
              : 'bg-vermilion-light border-vermilion text-vermilion font-semibold'
          }`}
        >
          {isIntact ? (
            <ShieldCheck className="w-3.5 h-3.5 text-teal shrink-0" aria-hidden="true" />
          ) : (
            <AlertTriangle className="w-3.5 h-3.5 text-vermilion shrink-0" aria-hidden="true" />
          )}

          {isLoading ? (
            <span className="text-xs font-medium">Verifying chain…</span>
          ) : isIntact ? (
            <div className="flex items-center gap-2 text-xs">
              <span className="font-bold uppercase tracking-wide">Chain Intact</span>
              <span className="text-border-strong">·</span>
              <span className="text-ink font-mono">{integrity?.total_exhibits ?? 0} exhibits</span>
              <span className="text-border-strong hidden xl:inline">·</span>
              <span className="text-muted font-mono hidden xl:inline">
                root <span className="text-ink font-semibold">{rootShort}</span>
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-xs">
              <span className="uppercase tracking-wide font-bold">Tampering Detected</span>
              <span className="text-border-strong">·</span>
              <span>{integrity?.failed_exhibit ? `Exhibit: ${integrity.failed_exhibit}` : 'Custody invalid'}</span>
            </div>
          )}

          <button
            type="button"
            disabled={verifyMutation.isPending}
            onClick={() => verifyMutation.mutate()}
            title="Recompute all SHA-256 digests and audit hash chain integrity"
            className="ml-1 hover:bg-black/5 px-2 py-0.5 rounded text-[11px] font-sans font-semibold uppercase tracking-wider border border-current/25 cursor-pointer inline-flex items-center gap-1 transition-colors duration-150"
          >
            <RefreshCw
              className={`w-3 h-3 ${verifyMutation.isPending ? 'animate-spin' : ''}`}
              aria-hidden="true"
            />
            <span>Verify</span>
          </button>
        </div>
      </div>

      {/* Right: Pipeline, Status Popover, and Quick Search */}
      <div className="flex items-center gap-2 relative shrink-0">
        <button
          type="button"
          disabled={isAnalyzing}
          onClick={() => analyzeMutation.mutate()}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-vermilion hover:bg-vermilion-dark text-white text-xs font-sans font-semibold rounded transition-colors duration-150 disabled:opacity-50 cursor-pointer whitespace-nowrap"
        >
          <Layers className={`w-3.5 h-3.5 ${isAnalyzing ? 'animate-spin' : ''}`} aria-hidden="true" />
          <span>{isAnalyzing ? 'Running…' : 'Run Pipeline'}</span>
        </button>

        {/* Compact Status Popover */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setCapsOpen(!capsOpen)}
            aria-expanded={capsOpen}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-sans font-medium text-muted hover:text-ink border border-border rounded bg-paper hover:bg-paper-subtle transition-colors duration-150 cursor-pointer whitespace-nowrap"
          >
            <Cpu className="w-3.5 h-3.5 text-teal" aria-hidden="true" />
            <span>Status</span>
            <ChevronDown className="w-3 h-3 text-muted" aria-hidden="true" />
          </button>

          {capsOpen && (
            <div className="absolute right-0 mt-2 w-64 bg-panel border border-border-strong rounded p-3.5 text-xs z-50 space-y-2.5">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <span className="font-sans text-[11px] uppercase font-bold tracking-wider text-ink">
                  Offline Engines
                </span>
                <span className="text-[10px] font-mono font-semibold text-teal bg-teal-light px-2 py-0.5 rounded border border-teal-border">
                  OFFLINE
                </span>
              </div>
              <div className="space-y-2 text-xs whitespace-normal">
                <div className="flex items-center justify-between">
                  <span className="text-muted">Local Model:</span>
                  <span className={`font-medium flex items-center gap-1 ${caps?.ollama.available ? 'text-approved' : 'text-amber'}`}>
                    {caps?.ollama.available ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                    {caps?.ollama.available ? 'Ollama' : 'Deterministic'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted">OCR:</span>
                  <span className={`font-medium flex items-center gap-1 ${caps?.tesseract.available ? 'text-approved' : 'text-muted'}`}>
                    {caps?.tesseract.available ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                    {caps?.tesseract.available ? 'Tesseract' : 'Unavailable'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted">PDF Engine:</span>
                  <span className="font-mono text-ink">{caps?.pdf_engine.engine || 'pdfplumber'}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Quick Navigation Search Box */}
        <div className="relative">
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-muted border border-border rounded bg-paper focus-within:border-teal transition-colors duration-150">
            <Search className="w-3.5 h-3.5 text-muted shrink-0" aria-hidden="true" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setTimeout(() => setSearchFocused(false), 180)}
              placeholder="Jump to…"
              aria-label="Quick navigation"
              className="bg-transparent border-none outline-none text-xs text-ink placeholder:text-muted w-24 focus:w-32 transition-all duration-150 font-sans"
            />
          </div>

          {searchFocused && filteredRoutes.length > 0 && (
            <div className="absolute right-0 mt-1.5 w-44 bg-panel border border-border-strong rounded py-1 z-50 text-xs">
              {filteredRoutes.map((r) => (
                <button
                  key={r.path}
                  type="button"
                  onMouseDown={() => {
                    navigate(r.path);
                    setSearchQuery('');
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-paper-subtle cursor-pointer text-ink font-sans"
                >
                  {r.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
