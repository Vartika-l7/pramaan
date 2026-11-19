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
  { label: 'Evidence Vault', path: '/evidence' },
  { label: 'Knowledge Graph', path: '/graph' },
  { label: 'Event Sequence', path: '/events' },
  { label: 'Review Queue', path: '/review' },
  { label: 'Case Package', path: '/package' },
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

  const filteredRoutes = searchQuery
    ? QUICK_ROUTES.filter((r) => r.label.toLowerCase().includes(searchQuery.toLowerCase()))
    : [];

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

      {/* Right: Actions, Capabilities, and Search Box */}
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

        {/* Forensic Capabilities Status Popover */}
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
            <div className="absolute right-0 mt-2 w-72 bg-surface-raised border border-border rounded-xl shadow-xl p-3.5 text-xs z-50 animate-in fade-in zoom-in-95">
              <div className="flex items-center justify-between border-b border-border pb-2 mb-2.5">
                <span className="font-sans text-xs uppercase font-bold tracking-wider text-ink">
                  Forensic Engines
                </span>
                <span className="text-2xs font-sans font-bold text-lime-dark bg-lime-light px-2 py-0.5 rounded-full border border-lime-dark/30">
                  OFFLINE
                </span>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-ink-secondary">Local AI:</span>
                  <span className={`font-semibold flex items-center gap-1 ${caps?.ollama.available ? 'text-lime-dark' : 'text-ochre-dark'}`}>
                    {caps?.ollama.available ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                    {caps?.ollama.available ? 'Ollama' : 'Deterministic'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-ink-secondary">OCR:</span>
                  <span className={`font-semibold flex items-center gap-1 ${caps?.tesseract.available ? 'text-lime-dark' : 'text-ink-tertiary'}`}>
                    {caps?.tesseract.available ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                    {caps?.tesseract.available ? 'Tesseract' : 'Unavailable'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-ink-secondary">PDF Engine:</span>
                  <span className="font-semibold text-ink">{caps?.pdf_engine.engine || 'pdfplumber'}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Clean Unified Search Box (replacing heavy Command Palette) */}
        <div className="relative">
          <div className="flex items-center gap-2 px-2.5 py-1 text-xs text-ink-secondary border border-border rounded-lg bg-surface focus-within:border-cobalt transition-colors">
            <Search className="w-3.5 h-3.5 text-ink-tertiary shrink-0" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setTimeout(() => setSearchFocused(false), 200)}
              placeholder="Quick search..."
              className="bg-transparent border-none outline-hidden text-xs text-ink placeholder:text-ink-tertiary w-28 focus:w-40 transition-all font-sans"
            />
          </div>

          {searchFocused && filteredRoutes.length > 0 && (
            <div className="absolute right-0 mt-1.5 w-44 bg-surface-raised border border-border rounded-lg shadow-lg py-1 z-50 text-xs">
              {filteredRoutes.map((r) => (
                <button
                  key={r.path}
                  type="button"
                  onMouseDown={() => {
                    navigate(r.path);
                    setSearchQuery('');
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-ivory cursor-pointer text-ink font-sans flex items-center justify-between"
                >
                  <span>{r.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
