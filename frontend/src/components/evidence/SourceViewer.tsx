import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  X,
  FileCode,
  Shield,
  Upload,
  Lock,
  Hash,
  RefreshCw,
} from 'lucide-react';
import { useAppStore } from '../../lib/store';
import { fetchEventSource, computeBrowserSha256, verifyIntegrity } from '../../lib/api';
import { HashChip } from '../ui/HashChip';
import { TierBadge } from '../ui/TierBadge';

export const SourceViewer: React.FC = () => {
  const isOpen = useAppStore((state) => state.sourceViewerOpen);
  const closeSourceViewer = useAppStore((state) => state.closeSourceViewer);
  const eventId = useAppStore((state) => state.sourceViewerEventId);
  const queryClient = useQueryClient();

  const [browserRehashStatus, setBrowserRehashStatus] = useState<string | null>(null);
  const [serverVerifyStatus, setServerVerifyStatus] = useState<string | null>(null);

  const { data: sourceData, isLoading } = useQuery({
    queryKey: ['eventSource', eventId],
    queryFn: () => (eventId ? fetchEventSource(eventId) : null),
    enabled: !!eventId && isOpen,
  });

  const rehashNowMutation = useMutation({
    mutationFn: verifyIntegrity,
    onSuccess: (res) => {
      queryClient.setQueryData(['integrityStatus'], res);
      const match = res?.exhibits?.find((ex: any) => ex.exhibit_id === sourceData?.exhibit_id);
      if (match) {
        setServerVerifyStatus(`${match.status}: ${match.reason}`);
      } else {
        setServerVerifyStatus(res?.intact ? 'PASS: Case integrity verified' : 'FAIL: Integrity breach');
      }
    },
  });

  if (!isOpen) return null;

  const handleBrowserRehash = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !sourceData) return;
    try {
      const computedHash = await computeBrowserSha256(file);
      if (computedHash.toLowerCase() === sourceData.sha256.toLowerCase()) {
        setBrowserRehashStatus('MATCH: Browser WebCrypto SHA-256 matches exhibit digest.');
      } else {
        setBrowserRehashStatus(
          `MISMATCH: Computed ${computedHash.slice(0, 8)}…${computedHash.slice(-4)} differs from stored digest.`
        );
      }
    } catch (err: any) {
      setBrowserRehashStatus(`Error: ${err.message}`);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end bg-ink/35" role="dialog" aria-label="Source Viewer">
      <div className="w-full max-w-2xl bg-panel h-full border-l border-border-strong flex flex-col">
        {/* Header */}
        <div className="h-14 border-b border-border px-5 flex items-center justify-between bg-paper">
          <div className="flex items-center gap-2.5">
            <FileCode className="w-4 h-4 text-teal" aria-hidden="true" />
            <h3 className="font-serif font-bold text-base text-ink">
              Evidence Source Record
            </h3>
            {sourceData?.exhibit_id && (
              <span className="exhibit-id">{sourceData.exhibit_id}</span>
            )}
          </div>
          <button
            type="button"
            onClick={closeSourceViewer}
            aria-label="Close Source Viewer"
            className="p-1.5 hover:bg-paper-subtle rounded text-muted hover:text-ink transition-colors duration-150 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {isLoading ? (
            <div className="space-y-3">
              <div className="h-24 bg-paper-subtle rounded animate-pulse border border-border" />
              <div className="h-48 bg-paper-subtle rounded animate-pulse border border-border" />
            </div>
          ) : !sourceData ? (
            <div className="text-muted text-xs font-mono p-4 bg-paper rounded border border-border">
              No source record found for event {eventId}.
            </div>
          ) : (
            <>
              {/* Metadata */}
              <div className="bg-paper p-4 rounded border border-border space-y-2.5 text-xs">
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <span className="section-label">Exhibit File</span>
                  <span className="font-mono font-semibold text-ink">{sourceData.filename}</span>
                </div>

                <div className="flex items-center justify-between border-b border-border pb-2">
                  <span className="section-label">SHA-256 Digest</span>
                  <HashChip hash={sourceData.sha256} />
                </div>

                <div className="flex items-center justify-between">
                  <span className="section-label">Line / Row Reference</span>
                  <span className="font-mono font-medium text-ink">
                    {sourceData.ref?.line_start
                      ? `Lines ${sourceData.ref.line_start}–${sourceData.ref.line_end}`
                      : sourceData.ref?.row_index !== undefined
                      ? `Row ${sourceData.ref.row_index} (Page ${sourceData.ref.page || 1})`
                      : 'N/A'}
                  </span>
                </div>
              </div>

              {/* Raw Extract (±5 lines) */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="section-label flex items-center gap-1.5">
                    <Hash className="w-3.5 h-3.5 text-teal" aria-hidden="true" />
                    Record &amp; ±5 Context Lines
                  </span>
                  <TierBadge tier="VERIFIED BY CODE" size="sm" />
                </div>

                <div className="bg-ink text-paper font-mono text-xs p-4 rounded overflow-x-auto leading-relaxed border border-border-strong">
                  {sourceData.context_before?.map((line: string, idx: number) => (
                    <div key={`b-${idx}`} className="opacity-50 select-none">
                      {line || ' '}
                    </div>
                  ))}

                  <div className="bg-amber/20 text-[#FDE6C4] font-medium my-1.5 px-2 py-1 rounded border-l-2 border-amber">
                    {sourceData.target_lines?.map((line: string, idx: number) => (
                      <div key={`t-${idx}`}>{line || ' '}</div>
                    ))}
                  </div>

                  {sourceData.context_after?.map((line: string, idx: number) => (
                    <div key={`a-${idx}`} className="opacity-50 select-none">
                      {line || ' '}
                    </div>
                  ))}
                </div>
              </div>

              {/* Re-hash Now (Server + Browser) */}
              <div className="border border-border rounded p-4 bg-paper space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-ink flex items-center gap-1.5">
                    <Shield className="w-4 h-4 text-teal" aria-hidden="true" />
                    Cryptographic Verification
                  </span>
                  <button
                    type="button"
                    onClick={() => rehashNowMutation.mutate()}
                    disabled={rehashNowMutation.isPending}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-teal text-white text-xs font-medium hover:opacity-90 transition-opacity duration-150 cursor-pointer"
                  >
                    <RefreshCw className={`w-3 h-3 ${rehashNowMutation.isPending ? 'animate-spin' : ''}`} />
                    <span>Re-hash now</span>
                  </button>
                </div>

                {serverVerifyStatus && (
                  <p className={`text-xs font-mono ${serverVerifyStatus.startsWith('PASS') ? 'text-approved' : 'text-vermilion'}`}>
                    {serverVerifyStatus}
                  </p>
                )}

                <div className="flex flex-wrap items-center gap-3 pt-1 border-t border-border">
                  <label className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-panel border border-border-strong hover:border-teal text-xs font-mono rounded cursor-pointer transition-colors duration-150">
                    <Upload className="w-3.5 h-3.5 text-muted" aria-hidden="true" />
                    <span>Compare Local File (WebCrypto)</span>
                    <input type="file" onChange={handleBrowserRehash} className="hidden" />
                  </label>

                  {browserRehashStatus && (
                    <span
                      className={`text-xs font-mono ${
                        browserRehashStatus.startsWith('MATCH') ? 'text-approved font-semibold' : 'text-vermilion font-semibold'
                      }`}
                    >
                      {browserRehashStatus}
                    </span>
                  )}
                </div>
              </div>

              {/* Custody Events */}
              <div className="space-y-2">
                <span className="section-label flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-teal" aria-hidden="true" />
                  Custody Events
                </span>

                <div className="space-y-2">
                  {sourceData.custody_events?.map((ev: any) => (
                    <div
                      key={ev.seq}
                      className="text-xs bg-paper border border-border rounded p-2.5 flex items-start justify-between font-mono"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-ink">#{ev.seq} {ev.action}</span>
                          <span className="text-[11px] text-muted bg-panel px-1.5 py-0.5 rounded border border-border">
                            {ev.actor}
                          </span>
                        </div>
                        <div className="text-[11px] text-muted mt-1">
                          Entry hash: <span className="text-ink">{ev.entry_hash?.slice(0, 12)}…</span>
                        </div>
                      </div>
                      <span className="text-[11px] text-muted">
                        {ev.ts_utc?.slice(0, 19).replace('T', ' ')}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
