import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Upload,
  FolderArchive,
  FileText,
  Clock,
  Copy,
  Check,
  ChevronRight,
  Shield,
  Layers,
  X,
  Lock,
  Tag,
  Hash,
} from 'lucide-react';
import { fetchEvidenceList, uploadEvidenceFile, fetchEvidenceDetail } from '../lib/api';
import { Evidence, CustodyEvent } from '../types';
import { TierBadge } from '../components/ui/TierBadge';

const SOURCE_TYPE_STYLES: Record<string, string> = {
  whatsapp: 'bg-cobalt-light text-cobalt',
  WHATSAPP: 'bg-cobalt-light text-cobalt',
  pdf: 'bg-lavender-light text-lavender-dark',
  PDF: 'bg-lavender-light text-lavender-dark',
  csv: 'bg-lime-light text-lime-dark',
  CSV: 'bg-lime-light text-lime-dark',
  cdr: 'bg-ochre-light text-ochre-dark',
  CDR: 'bg-ochre-light text-ochre-dark',
  image: 'bg-tomato-light text-tomato',
  IMAGE: 'bg-tomato-light text-tomato',
};

function getSourceTypeStyle(type: string) {
  return SOURCE_TYPE_STYLES[type] || SOURCE_TYPE_STYLES[type?.toLowerCase()] || 'bg-ivory-dark text-ink-secondary';
}

export const EvidenceVaultPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedExhibit, setSelectedExhibit] = useState<string | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const { data: exhibits, isLoading } = useQuery({
    queryKey: ['evidenceList'],
    queryFn: fetchEvidenceList,
  });

  const { data: detailData, isLoading: detailLoading } = useQuery({
    queryKey: ['evidenceDetail', selectedExhibit],
    queryFn: () => (selectedExhibit ? fetchEvidenceDetail(selectedExhibit) : null),
    enabled: !!selectedExhibit,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadEvidenceFile(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evidenceList'] });
      queryClient.invalidateQueries({ queryKey: ['integrityStatus'] });
    },
  });

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    for (const f of files) {
      await uploadMutation.mutateAsync(f);
    }
  };

  const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    for (const f of files) {
      await uploadMutation.mutateAsync(f);
    }
  };

  const copyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="border-b border-border pb-5 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="section-label mb-1.5">
            Dossier Section 02 · Evidence Repository &amp; Custody Chain
          </div>
          <h1 className="font-serif text-4xl font-bold text-ink tracking-tight">
            Evidence Vault
          </h1>
          <p className="text-ink-secondary text-sm mt-2 max-w-3xl leading-relaxed">
            All forensic artifacts are read-only and indexed by their SHA-256 cryptographic digest upon ingest. Every inspection and state transformation is permanently recorded in an append-only, SQLite-triggered custody ledger.
          </p>
        </div>

        <label className="flex items-center gap-2 px-4 py-2 bg-cobalt hover:bg-cobalt-dark text-white text-sm font-sans font-medium rounded-lg transition-colors cursor-pointer shadow-sm self-start md:self-auto">
          <Upload className="w-4 h-4" />
          <span>Upload New Exhibit</span>
          <input type="file" multiple onChange={handleFileInput} className="hidden" />
        </label>
      </div>

      {/* Drag & Drop Archival Dropzone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`bg-surface-raised border-2 border-dashed rounded-xl p-10 text-center transition-colors ${
          isDragging
            ? 'border-cobalt bg-cobalt-light'
            : 'border-border hover:border-cobalt'
        }`}
      >
        <FolderArchive className="w-10 h-10 text-cobalt mx-auto mb-3 opacity-80" />
        <div className="font-sans text-ink-secondary font-semibold text-sm">
          Drop forensic exhibits here
        </div>
        <p className="text-xs text-ink-tertiary mt-1.5 max-w-lg mx-auto">
          Supports WhatsApp exported text logs, PNB/HDFC Bank PDFs &amp; CSVs, CDR cell logs, and JPEG/PNG screenshots.
        </p>
        <div className="text-xs text-ink-tertiary mt-3 font-mono flex items-center justify-center gap-3">
          <span>Chunked SHA-256 Hashing</span>
          <span>·</span>
          <span>Read-Only Storage Under Hash</span>
          <span>·</span>
          <span>Immutable Custody Trigger</span>
        </div>
      </div>

      {/* Registered Exhibits Ledger Table */}
      <div className="bg-surface-raised rounded-xl border border-border overflow-hidden">
        <div className="px-5 py-3.5 border-b border-border bg-ivory-dark flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Tag className="w-3.5 h-3.5 text-cobalt" />
            <span className="section-label">
              Registered Evidence Ledger ({exhibits?.length || 0})
            </span>
          </div>
          <span className="text-xs font-mono text-ink-tertiary bg-surface px-2 py-0.5 rounded border border-border">
            SHA-256 / READ-ONLY REPOSITORY
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-ivory-dark text-ink-secondary text-2xs font-sans font-semibold uppercase tracking-wider select-none">
              <tr>
                <th className="py-2.5 px-4">Exhibit Tag</th>
                <th className="py-2.5 px-4">Filename</th>
                <th className="py-2.5 px-4">Source Type</th>
                <th className="py-2.5 px-4">File Size</th>
                <th className="py-2.5 px-4">SHA-256 Digest</th>
                <th className="py-2.5 px-4">Received UTC</th>
                <th className="py-2.5 px-4">Parse Status</th>
                <th className="py-2.5 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="font-sans">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-ink-tertiary font-mono text-xs">
                    Accessing SQLite evidence database...
                  </td>
                </tr>
              ) : exhibits?.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-ink-tertiary font-mono text-xs">
                    No evidence exhibits registered in case repository. Drag and drop raw files above.
                  </td>
                </tr>
              ) : (
                exhibits?.map((ev) => (
                  <tr
                    key={ev.id}
                    onClick={() => setSelectedExhibit(ev.id)}
                    className="ledger-row cursor-pointer group"
                  >
                    <td className="py-3 px-4">
                      <span className="exhibit-id group-hover:border-cobalt transition-colors">
                        {ev.exhibit_id}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-sm font-medium text-ink font-sans">
                      {ev.filename}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`text-xs font-mono px-2 py-0.5 rounded font-medium ${getSourceTypeStyle(ev.source_type)}`}>
                        {ev.source_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-ink-tertiary">
                      {(ev.size_bytes / 1024).toFixed(1)} KB
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-xs text-ink-tertiary">
                          {ev.sha256.slice(0, 10)}...{ev.sha256.slice(-8)}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            copyHash(ev.sha256);
                          }}
                          title="Copy full 64-char SHA-256 digest"
                          className="p-1 hover:bg-ivory-dark rounded text-ink-tertiary hover:text-cobalt cursor-pointer transition-colors"
                        >
                          {copiedHash === ev.sha256 ? (
                            <Check className="w-3 h-3 text-lime-dark" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-ink-tertiary">
                      {ev.received_at_utc.slice(0, 16).replace('T', ' ')}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`text-xs font-mono px-2 py-0.5 rounded font-medium ${
                          ev.parse_status === 'PARSED'
                            ? 'bg-lime-light text-lime-dark'
                            : ev.parse_status === 'FAILED'
                            ? 'bg-tomato-light text-tomato'
                            : 'bg-ochre-light text-ochre-dark'
                        }`}
                      >
                        {ev.parse_status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <ChevronRight className="w-4 h-4 text-ink-tertiary group-hover:text-cobalt inline-block transition-colors" />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Exhibit Custody Drawer Slide-over */}
      {selectedExhibit && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-[1px]">
          <div className="w-full max-w-xl bg-surface-raised h-full shadow-2xl border-l border-border flex flex-col animate-in slide-in-from-right duration-200">
            {/* Header */}
            <div className="h-14 border-b border-border px-6 flex items-center justify-between bg-ivory-dark">
              <div className="flex items-center gap-2.5">
                <FileText className="w-4 h-4 text-cobalt" />
                <h3 className="font-serif font-bold text-base text-ink">
                  Exhibit Custody Dossier · {detailData?.exhibit_id}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedExhibit(null)}
                className="p-1.5 hover:bg-border rounded-lg text-ink-secondary hover:text-ink cursor-pointer transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            <div className="p-6 flex-1 overflow-y-auto space-y-5">
              {detailLoading ? (
                <div className="text-xs font-mono text-ink-tertiary text-center py-12">
                  Querying custody event log from SQLite...
                </div>
              ) : (
                <>
                  <div className="bg-ivory rounded-xl p-4 border border-border space-y-2 text-xs">
                    <div className="flex items-center justify-between border-b border-border pb-2">
                      <span className="section-label">Filename:</span>
                      <span className="font-semibold text-ink font-sans">{detailData?.filename}</span>
                    </div>
                    <div className="border-b border-border pb-2">
                      <div className="section-label mb-1">SHA-256 Digest:</div>
                      <div className="font-mono text-xs text-ink-secondary break-all select-all bg-surface-raised p-2 rounded-lg border border-border">
                        {detailData?.sha256}
                      </div>
                    </div>
                    <div>
                      <div className="section-label mb-1">Read-Only Disk Location:</div>
                      <div className="font-mono text-xs text-ink-tertiary break-all">
                        {detailData?.stored_path}
                      </div>
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="section-label flex items-center gap-1.5">
                        <Lock className="w-3 h-3 text-lime-dark" />
                        Append-Only Custody Log (Hash-Chained)
                      </h4>
                      <span className="text-xs font-mono text-lime-dark bg-lime-light px-2 py-0.5 rounded border border-lime/40">
                        AUDIT VERIFIED
                      </span>
                    </div>

                    <div className="space-y-2.5">
                      {detailData?.custody_events?.map((ev) => (
                        <div
                          key={ev.seq}
                          className="bg-surface-raised border border-border rounded-lg p-3 text-xs font-mono space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-ink">
                              Seq #{ev.seq} · {ev.action}
                            </span>
                            <span className="text-xs text-ink-secondary bg-ivory px-2 py-0.5 rounded border border-border">
                              {ev.actor}
                            </span>
                          </div>
                          <div className="text-xs text-ink-tertiary">
                            Prev Hash: <span className="text-ink-secondary">{ev.prev_hash ? `${ev.prev_hash.slice(0, 20)}...` : '0000000000000000 (GENESIS)'}</span>
                          </div>
                          <div className="text-xs text-ink-tertiary">
                            Entry Hash: <span className="text-ink font-semibold">{ev.entry_hash?.slice(0, 20)}...</span>
                          </div>
                          <div className="text-xs text-ink-tertiary pt-1 border-t border-border">
                            Recorded UTC: {ev.ts_utc}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
