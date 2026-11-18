import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  X,
  Copy,
  Check,
  FileCode,
  Shield,
  Upload,
  Lock,
  Hash,
} from 'lucide-react';
import { useAppStore } from '../../lib/store';
import { fetchEventSource, computeBrowserSha256 } from '../../lib/api';

export const SourceViewer: React.FC = () => {
  const isOpen = useAppStore((state) => state.sourceViewerOpen);
  const closeSourceViewer = useAppStore((state) => state.closeSourceViewer);
  const eventId = useAppStore((state) => state.sourceViewerEventId);

  const [copied, setCopied] = useState(false);
  const [browserRehashStatus, setBrowserRehashStatus] = useState<string | null>(null);

  const { data: sourceData, isLoading } = useQuery({
    queryKey: ['eventSource', eventId],
    queryFn: () => (eventId ? fetchEventSource(eventId) : null),
    enabled: !!eventId && isOpen,
  });

  if (!isOpen) return null;

  const copyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleBrowserRehash = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !sourceData) return;

    try {
      const computedHash = await computeBrowserSha256(file);
      if (computedHash.toLowerCase() === sourceData.sha256.toLowerCase()) {
        setBrowserRehashStatus('MATCH: Browser WebCrypto SHA-256 matches evidence record exactly.');
      } else {
        setBrowserRehashStatus(
          `MISMATCH: Browser computed ${computedHash.slice(0, 10)}... does not match ${sourceData.sha256.slice(0, 10)}...`
        );
      }
    } catch (err: any) {
      setBrowserRehashStatus(`Error computing hash: ${err.message}`);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end bg-black/40 backdrop-blur-[2px]">
      <div className="w-full max-w-2xl bg-surface-raised h-full shadow-2xl border-l border-border flex flex-col animate-in slide-in-from-right duration-200">
        {/* Header - Evidence File Dossier Top */}
        <div className="h-14 border-b border-border px-6 flex items-center justify-between bg-surface">
          <div className="flex items-center gap-2.5">
            <FileCode className="w-4 h-4 text-cobalt" />
            <h3 className="font-serif font-bold text-base text-ink">
              Evidence Source Record
            </h3>
            {sourceData?.exhibit_id && (
              <span className="font-mono text-xs bg-ivory border border-border px-2 py-0.5 rounded-[3px] font-bold text-cobalt">
                {sourceData.exhibit_id}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={closeSourceViewer}
            className="p-1 hover:bg-ivory-dark rounded text-ink-secondary hover:text-ink transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isLoading ? (
            <div className="flex items-center justify-center h-48 text-ink-secondary text-xs font-mono">
              Fetching raw evidence source span...
            </div>
          ) : !sourceData ? (
            <div className="text-ink-secondary text-xs font-mono">No source record found for event {eventId}.</div>
          ) : (
            <>
              {/* Evidence Dossier Metadata Tag */}
              <div className="bg-surface p-4 rounded-[4px] border border-border space-y-2.5">
                <div className="flex items-center justify-between text-xs border-b border-border/60 pb-2">
                  <span className="text-ink-secondary font-mono uppercase text-[10px] tracking-wider">
                    Raw Exhibit File
                  </span>
                  <span className="font-mono font-bold text-ink">{sourceData.filename}</span>
                </div>

                <div className="flex items-center justify-between text-xs border-b border-border/60 pb-2">
                  <span className="text-ink-secondary font-mono uppercase text-[10px] tracking-wider">
                    SHA-256 Digest
                  </span>
                  <div className="flex items-center gap-1.5 font-mono text-xs text-ink">
                    <span className="font-medium text-ink-secondary">
                      {sourceData.sha256.slice(0, 16)}...{sourceData.sha256.slice(-10)}
                    </span>
                    <button
                      type="button"
                      onClick={() => copyHash(sourceData.sha256)}
                      title="Copy full 64-char SHA-256 digest"
                      className="p-1 hover:bg-ivory-dark rounded text-ink-secondary hover:text-ink cursor-pointer transition-colors"
                    >
                      {copied ? (
                        <Check className="w-3.5 h-3.5 text-lime-dark" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs">
                  <span className="text-ink-secondary font-mono uppercase text-[10px] tracking-wider">
                    Location Index
                  </span>
                  <span className="font-mono font-medium text-ink">
                    {sourceData.ref?.line_start
                      ? `Lines ${sourceData.ref.line_start} - ${sourceData.ref.line_end}`
                      : sourceData.ref?.row_index
                      ? `Row ${sourceData.ref.row_index} (Page ${sourceData.ref.page || 1})`
                      : 'N/A'}
                  </span>
                </div>
              </div>

              {/* Source Text with Context Before / After */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono uppercase tracking-wider font-bold text-ink-secondary flex items-center gap-1.5">
                    <Hash className="w-3 h-3 text-cobalt" />
                    Raw Artifact Extract (±5 Context Lines)
                  </span>
                  <span className="text-[10px] font-mono text-lime-dark bg-lime-light px-2 py-0.5 rounded-[3px] border border-lime-dark/30 font-semibold">
                    VERIFIED BY CODE
                  </span>
                </div>

                <div className="bg-[#242D3A] text-[#F4F0E7] font-mono text-[11px] p-4 rounded-[4px] overflow-x-auto leading-relaxed border border-border shadow-inner">
                  {/* Context Before */}
                  {sourceData.context_before?.map((line: string, idx: number) => (
                    <div key={`b-${idx}`} className="opacity-40 select-none hover:opacity-80 transition-opacity">
                      {line || ' '}
                    </div>
                  ))}

                  {/* Target Highlighted Span */}
                  <div className="bg-ochre-light/20 text-ochre font-medium my-1.5 px-2 py-1 rounded-[2px] border-l-2 border-ochre">
                    {sourceData.target_lines?.map((line: string, idx: number) => (
                      <div key={`t-${idx}`}>{line || ' '}</div>
                    ))}
                  </div>

                  {/* Context After */}
                  {sourceData.context_after?.map((line: string, idx: number) => (
                    <div key={`a-${idx}`} className="opacity-40 select-none hover:opacity-80 transition-opacity">
                      {line || ' '}
                    </div>
                  ))}
                </div>
              </div>

              {/* Independent Re-hash Verification in Browser */}
              <div className="border border-border rounded-[4px] p-4 bg-surface space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-ink flex items-center gap-1.5">
                    <Shield className="w-4 h-4 text-cobalt" />
                    Client-Side Re-Hash Audit (Web Crypto API)
                  </span>
                  <span className="text-[10px] font-mono text-ink-secondary">OFFLINE VERIFICATION</span>
                </div>
                <p className="text-[11px] text-ink-secondary leading-relaxed">
                  Verify cryptographic integrity client-side. Select the raw exhibit file from disk to compute its SHA-256 digest in browser memory without sending bytes anywhere.
                </p>

                <div className="flex items-center gap-3 pt-1">
                  <label className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-raised border border-border hover:border-ink text-xs font-mono rounded-[3px] cursor-pointer transition-colors shadow-xs">
                    <Upload className="w-3.5 h-3.5 text-ink-secondary" />
                    <span>Select File to Verify</span>
                    <input type="file" onChange={handleBrowserRehash} className="hidden" />
                  </label>

                  {browserRehashStatus && (
                    <span
                      className={`text-xs font-mono ${
                        browserRehashStatus.startsWith('MATCH')
                          ? 'text-lime-dark font-semibold'
                          : 'text-tomato font-semibold'
                      }`}
                    >
                      {browserRehashStatus}
                    </span>
                  )}
                </div>
              </div>

              {/* Chain of Custody History */}
              <div>
                <div className="flex items-center justify-between mb-2.5">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-ink-secondary font-bold flex items-center gap-1.5">
                    <Lock className="w-3 h-3 text-lime-dark" />
                    Tamper-Evident Custody Chain
                  </span>
                  <span className="text-[10px] font-mono text-ink-tertiary">IMMUTABLE LOG</span>
                </div>

                <div className="space-y-2">
                  {sourceData.custody_events?.map((ev: any) => (
                    <div
                      key={ev.seq}
                      className="text-xs bg-surface border border-border rounded-[3px] p-3 flex items-start justify-between font-mono"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-ink">#{ev.seq} {ev.action}</span>
                          <span className="text-[10px] text-ink-secondary bg-ivory px-1.5 py-0.2 rounded border border-border">
                            {ev.actor}
                          </span>
                        </div>
                        <div className="text-[10px] text-ink-secondary mt-1">
                          Hash: <span className="text-ink font-semibold">{ev.entry_hash?.slice(0, 16)}...</span>
                        </div>
                      </div>
                      <span className="text-[10px] text-ink-tertiary">
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
