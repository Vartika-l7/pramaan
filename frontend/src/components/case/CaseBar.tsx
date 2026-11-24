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
    <header className="h-16 border-b border-border bg-white/90 backdrop-blur-md px-6 flex items-center justify-between gap-3 select-none sticky top-0 z-30 whitespace-nowrap">
      {/* Left: Case Identifier & Synthetic Indicator */}
      <div className="flex items-center gap-2.5 shrink-0">
        <div className="inline-flex items-center gap-2 bg-[#F5F4F0] px-3 py-1.5 rounded-md border border-[#C9C6BC]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#316A78]" aria-hidden="true" />
          <span className="font-mono text-xs font-semibold text-[#20283A] tracking-tight">{caseId}</span>
        </div>
        <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[#455066] bg-[#ECEAE3] px-2.5 py-1 rounded-md border border-[#D4D1C7]">
          Synthetic case
        </span>
      </div>

      {/* Center: Integrity Seal */}
      <div className="flex items-center shrink-0">
        <div
          className={`flex items-center gap-2.5 pl-3 pr-1.5 py-1 rounded-md border text-xs font-sans transition-all duration-150 whitespace-nowrap ${
            isIntact
              ? 'bg-[#EAF2F4] border-[#B2CDD4] text-[#24525D]'
              : 'bg-[#FDF0EE] border-[#D95749] text-[#A63327] font-semibold ring-1 ring-[#D95749]/20'
          }`}
        >
          {isIntact ? (
            <ShieldCheck className="w-3.5 h-3.5 text-[#316A78] shrink-0" aria-hidden="true" />
          ) : (
            <AlertTriangle className="w-3.5 h-3.5 text-[#C74437] shrink-0" aria-hidden="true" />
          )}

          {isLoading ? (
            <span className="text-xs font-medium">Verifying chain…</span>
          ) : isIntact ? (
            <div className="flex items-center gap-2 text-xs">
              <span className="font-bold uppercase tracking-[0.06em] text-[11px]">Chain Intact</span>
              <span className="text-[#8EB4BE]">·</span>
              <span className="text-[#20283A] font-mono text-[11.5px] font-medium">
                {integrity?.total_exhibits ?? 0} exhibits
              </span>
              <span className="text-[#8EB4BE] hidden xl:inline">·</span>
              <span className="text-[#455066] font-mono text-[11px] hidden xl:inline">
                root <span className="text-[#20283A] font-semibold">{rootShort}</span>
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-xs">
              <span className="uppercase tracking-[0.06em] font-bold text-[11px]">Tampering Detected</span>
              <span className="opacity-50">·</span>
              <span className="font-mono text-[11.5px]">
                {integrity?.failed_exhibit ? `Exhibit ${integrity.failed_exhibit}` : 'Custody invalid'}
              </span>
            </div>
          )}

          <button
            type="button"
            disabled={verifyMutation.isPending}
            onClick={() => verifyMutation.mutate()}
            title="Recompute all SHA-256 digests and audit hash chain integrity"
            className={`ml-0.5 px-2.5 py-1 rounded text-[10.5px] font-sans font-semibold uppercase tracking-wider cursor-pointer inline-flex items-center gap-1 transition-colors duration-150 disabled:opacity-60 ${
              isIntact
                ? 'bg-white text-[#24525D] border border-[#B2CDD4] hover:bg-[#316A78] hover:text-white hover:border-[#316A78]'
                : 'bg-[#C74437] text-white border border-[#C74437] hover:bg-[#A63327]'
            }`}
          >
            <RefreshCw
              className={`w-3 h-3 ${verifyMutation.isPending ? 'animate-spin' : ''}`}
              aria-hidden="true"
            />
            <span>Verify now</span>
          </button>
        </div>
      </div>

      {/* Right: Deep Teal Primary CTA, Status Popover, and Quick Search */}
      <div className="flex items-center gap-2 relative shrink-0">
        <button
          type="button"
          disabled={isAnalyzing}
          onClick={() => analyzeMutation.mutate()}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-[#316A78] hover:bg-[#24525D] text-white text-xs font-sans font-semibold rounded-md shadow-sm transition-colors duration-150 disabled:opacity-55 cursor-pointer whitespace-nowrap"
        >
          <Layers className={`w-3.5 h-3.5 text-white ${isAnalyzing ? 'animate-spin' : ''}`} aria-hidden="true" />
          <span>{isAnalyzing ? 'Running…' : 'Run Pipeline'}</span>
        </button>

        {/* Compact Status Popover */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setCapsOpen(!capsOpen)}
            aria-expanded={capsOpen}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-sans font-semibold text-[#20283A] hover:bg-[#ECEAE3] border border-[#C9C6BC] rounded-md bg-[#F5F4F0] transition-colors duration-150 cursor-pointer whitespace-nowrap"
          >
            <Cpu className="w-3.5 h-3.5 text-[#316A78]" aria-hidden="true" />
            <span>Status</span>
            <ChevronDown className={`w-3 h-3 text-[#556077] transition-transform ${capsOpen ? 'rotate-180' : ''}`} aria-hidden="true" />
          </button>

          {capsOpen && (
            <div className="absolute right-0 mt-2 w-72 bg-white border border-[#C9C6BC] rounded-lg p-4 text-xs z-50 space-y-3 shadow-popover">
              <div className="flex items-center justify-between border-b border-border pb-2.5">
                <span className="font-sans text-[11px] uppercase font-bold tracking-[0.09em] text-[#20283A]">
                  Offline Engines
                </span>
                <span className="text-[10px] font-mono font-semibold text-[#24525D] bg-[#EAF2F4] px-2 py-0.5 rounded border border-[#B2CDD4]">
                  OFFLINE
                </span>
              </div>
              <div className="space-y-2.5 text-xs whitespace-normal">
                <div className="flex items-center justify-between">
                  <span className="text-[#556077]">Local Model</span>
                  <span className={`font-semibold flex items-center gap-1 ${caps?.ollama.available ? 'text-[#246B4F]' : 'text-[#9A6819]'}`}>
                    {caps?.ollama.available ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                    {caps?.ollama.available ? 'Ollama' : 'Deterministic'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#556077]">OCR Engine</span>
                  <span className={`font-semibold flex items-center gap-1 ${caps?.tesseract.available ? 'text-[#246B4F]' : 'text-[#556077]'}`}>
                    {caps?.tesseract.available ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                    {caps?.tesseract.available ? 'Tesseract' : 'Unavailable'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#556077]">PDF Engine</span>
                  <span className="font-mono text-[#20283A] text-[11px]">{caps?.pdf_engine.engine || 'pdfplumber'}</span>
                </div>
                <div className="flex items-center justify-between pt-2 border-t border-border">
                  <span className="text-[#556077]">Network use</span>
                  <span className="font-mono font-semibold text-[#24525D] text-[11px]">
                    {caps?.network_use?.outbound_connections ?? 0} outbound
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Quick Navigation Search Box */}
        <div className="relative">
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs border border-[#C9C6BC] rounded-md bg-[#F5F4F0] focus-within:border-[#316A78] focus-within:bg-white transition-all duration-150">
            <Search className="w-3.5 h-3.5 text-[#556077] shrink-0" aria-hidden="true" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setTimeout(() => setSearchFocused(false), 180)}
              placeholder="Jump to…"
              aria-label="Quick navigation"
              className="bg-transparent border-none outline-none text-xs text-[#20283A] placeholder:text-[#556077] w-20 focus:w-32 transition-all duration-150 font-sans"
            />
          </div>

          {searchFocused && filteredRoutes.length > 0 && (
            <div className="absolute right-0 mt-2 w-48 bg-white border border-[#C9C6BC] rounded-lg py-1.5 z-50 text-xs shadow-popover">
              {filteredRoutes.map((r) => (
                <button
                  key={r.path}
                  type="button"
                  onMouseDown={() => {
                    navigate(r.path);
                    setSearchQuery('');
                  }}
                  className="w-full text-left px-3.5 py-2 hover:bg-[#ECEAE3] cursor-pointer text-[#20283A] font-medium font-sans transition-colors"
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
