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
  Fingerprint,
  Image as ImageIcon,
  FileSpreadsheet,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Eye,
} from 'lucide-react';
import {
  fetchEvidenceList,
  uploadEvidenceFile,
  fetchEvidenceDetail,
  fetchImageAuthenticity,
  fetchStatementCheck,
} from '../lib/api';
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
  const [drawerTab, setDrawerTab] = useState<'custody' | 'authenticity'>('custody');
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

  // Folded Authenticity Queries for the selected exhibit
  const isImageExhibit = detailData?.source_type === 'image';
  const isStatementExhibit = detailData?.source_type === 'bank_pdf' || detailData?.source_type === 'bank_csv';

  const { data: imageData, isLoading: imageLoading } = useQuery({
    queryKey: ['imageAuth', detailData?.id],
    queryFn: () => (detailData?.id ? fetchImageAuthenticity(detailData.id) : null),
    enabled: !!detailData?.id && isImageExhibit && drawerTab === 'authenticity',
  });

  const { data: statementData, isLoading: statementLoading } = useQuery({
    queryKey: ['statementAuth', detailData?.id],
    queryFn: () => (detailData?.id ? fetchStatementCheck(detailData.id) : null),
    enabled: !!detailData?.id && isStatementExhibit && drawerTab === 'authenticity',
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadEvidenceFile(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evidenceList'] });
      queryClient.invalidateQueries({ queryKey: ['integrityStatus'] });
    },
  });

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    files.forEach((file) => uploadMutation.mutate(file));
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      Array.from(e.target.files).forEach((file) => uploadMutation.mutate(file));
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12 font-sans">
      {/* Editorial Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="font-sans text-xs font-bold uppercase tracking-wider text-cobalt bg-cobalt-light px-2.5 py-1 rounded-full">
              Digital Evidence Vault
            </span>
            <span className="text-ink-tertiary">·</span>
            <span className="font-sans text-xs text-ink-secondary">
              Immutable Content-Addressed Storage
            </span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl font-bold text-ink tracking-tight">
            Evidence Ingest & Custody Chain
          </h1>
          <p className="text-sm text-ink-secondary mt-1 max-w-2xl leading-relaxed">
            All exhibits are hashed with SHA-256 during streaming upload, preserved read-only under hash digest, and linked to the cryptographic custody ledger.
          </p>
        </div>

        <label className="flex items-center gap-2 px-4 py-2 bg-cobalt hover:bg-cobalt-dark text-white text-sm font-sans font-medium rounded-lg transition-colors cursor-pointer shadow-xs self-start md:self-auto">
          <Upload className="w-4 h-4" />
          <span>Upload Exhibit</span>
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
        className={`bg-surface-raised border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
          isDragging ? 'border-cobalt bg-cobalt-light' : 'border-border hover:border-cobalt'
        }`}
      >
        <FolderArchive className="w-9 h-9 text-cobalt mx-auto mb-2 opacity-80" />
        <div className="font-sans text-ink font-semibold text-sm">
          Drop forensic exhibits here to ingest
        </div>
        <p className="text-xs text-ink-secondary mt-1 max-w-lg mx-auto">
          Supports WhatsApp logs, Bank Statements (PDF/CSV), CDR Call Logs, and Images.
        </p>
      </div>

      {/* Registered Exhibits Ledger Table */}
      <div className="bg-surface-raised rounded-xl border border-border overflow-hidden">
        <div className="px-5 py-3 border-b border-border bg-ivory-dark flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Tag className="w-3.5 h-3.5 text-cobalt" />
            <span className="font-sans text-xs font-bold uppercase tracking-wider text-ink">
              Registered Evidence Ledger ({exhibits?.length || 0})
            </span>
          </div>
          <span className="text-xs font-mono text-ink-secondary bg-surface px-2 py-0.5 rounded border border-border">
            SHA-256 Content-Addressed
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-ivory-dark text-ink-secondary text-2xs font-sans font-semibold uppercase tracking-wider select-none">
              <tr>
                <th className="py-2.5 px-4">Exhibit Tag</th>
                <th className="py-2.5 px-4">Filename</th>
                <th className="py-2.5 px-4">Source Type</th>
                <th className="py-2.5 px-4">File Size</th>
                <th className="py-2.5 px-4">SHA-256 Digest</th>
                <th className="py-2.5 px-4">Parse Status</th>
                <th className="py-2.5 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-ink-secondary">
                    Loading evidence exhibits...
                  </td>
                </tr>
              ) : exhibits?.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-ink-secondary">
                    No exhibits ingested yet.
                  </td>
                </tr>
              ) : (
                exhibits?.map((ex) => (
                  <tr
                    key={ex.id}
                    onClick={() => {
                      setSelectedExhibit(ex.id);
                      setDrawerTab('custody');
                    }}
                    className="hover:bg-ivory cursor-pointer transition-colors group"
                  >
                    <td className="py-3 px-4 font-mono font-bold text-ink">
                      {ex.exhibit_id}
                    </td>
                    <td className="py-3 px-4 font-medium text-ink">
                      {ex.filename}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded-full font-mono text-2xs uppercase ${getSourceTypeStyle(ex.source_type)}`}>
                        {ex.source_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-ink-secondary">
                      {(ex.size_bytes / 1024).toFixed(1)} KB
                    </td>
                    <td className="py-3 px-4 font-mono text-2xs text-ink-secondary">
                      <span className="bg-surface px-1.5 py-0.5 rounded border border-border">
                        {ex.sha256.slice(0, 16)}...{ex.sha256.slice(-8)}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-mono text-2xs font-semibold text-lime-dark bg-lime-light px-2 py-0.5 rounded-full border border-lime-dark/30">
                        {ex.parse_status || 'PARSED'}
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

      {/* Exhibit Custody & Folded Authenticity Drawer Slide-over */}
      {selectedExhibit && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-xs">
          <div className="w-full max-w-xl bg-surface-raised h-full shadow-2xl border-l border-border flex flex-col animate-in slide-in-from-right duration-200">
            {/* Header */}
            <div className="h-14 border-b border-border px-6 flex items-center justify-between bg-ivory-dark">
              <div className="flex items-center gap-2.5">
                <FileText className="w-4 h-4 text-cobalt" />
                <h3 className="font-serif font-bold text-base text-ink">
                  Exhibit Dossier · {detailData?.exhibit_id}
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

            {/* Folded Tab Bar */}
            <div className="px-6 border-b border-border bg-surface flex gap-6 text-xs font-sans">
              <button
                type="button"
                onClick={() => setDrawerTab('custody')}
                className={`py-2.5 font-semibold border-b-2 cursor-pointer transition-colors ${
                  drawerTab === 'custody'
                    ? 'border-cobalt text-cobalt'
                    : 'border-transparent text-ink-secondary hover:text-ink'
                }`}
              >
                Chain of Custody
              </button>
              {(isImageExhibit || isStatementExhibit) && (
                <button
                  type="button"
                  onClick={() => setDrawerTab('authenticity')}
                  className={`py-2.5 font-semibold border-b-2 cursor-pointer transition-colors ${
                    drawerTab === 'authenticity'
                      ? 'border-cobalt text-cobalt'
                      : 'border-transparent text-ink-secondary hover:text-ink'
                  }`}
                >
                  Authenticity &amp; Forensics
                </button>
              )}
            </div>

            {/* Body */}
            <div className="p-6 flex-1 overflow-y-auto space-y-5">
              {detailLoading ? (
                <div className="text-xs font-mono text-ink-secondary text-center py-12">
                  Querying SQLite custody logs...
                </div>
              ) : drawerTab === 'custody' ? (
                <>
                  <div className="bg-ivory rounded-xl p-4 border border-border space-y-2 text-xs">
                    <div className="flex items-center justify-between border-b border-border pb-2">
                      <span className="font-sans text-ink-secondary">Filename:</span>
                      <span className="font-semibold text-ink font-sans">{detailData?.filename}</span>
                    </div>
                    <div className="border-b border-border pb-2">
                      <div className="font-sans text-ink-secondary mb-1">SHA-256 Digest:</div>
                      <div className="font-mono text-2xs text-ink-secondary break-all select-all bg-surface p-2 rounded-lg border border-border">
                        {detailData?.sha256}
                      </div>
                    </div>
                    <div>
                      <div className="font-sans text-ink-secondary mb-1">Read-Only Disk Location:</div>
                      <div className="font-mono text-2xs text-ink-tertiary break-all">
                        {detailData?.stored_path}
                      </div>
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-sans text-xs font-bold uppercase tracking-wider text-ink flex items-center gap-1.5">
                        <Lock className="w-3.5 h-3.5 text-lime-dark" />
                        Append-Only Custody Log (Hash-Chained)
                      </h4>
                      <span className="text-2xs font-mono text-lime-dark bg-lime-light px-2 py-0.5 rounded border border-lime-dark/30 font-bold">
                        VERIFIED
                      </span>
                    </div>

                    <div className="space-y-2.5">
                      {detailData?.custody_events?.map((ev) => (
                        <div
                          key={ev.seq}
                          className="bg-surface border border-border rounded-lg p-3 text-xs font-mono space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-ink">
                              Seq #{ev.seq} · {ev.action}
                            </span>
                            <span className="text-2xs text-ink-secondary bg-ivory px-2 py-0.5 rounded border border-border">
                              {ev.actor}
                            </span>
                          </div>
                          <div className="text-2xs text-ink-tertiary">
                            Prev Hash: <span className="text-ink-secondary">{ev.prev_hash ? `${ev.prev_hash.slice(0, 16)}...` : '00000000 (GENESIS)'}</span>
                          </div>
                          <div className="text-2xs text-ink-tertiary">
                            Entry Hash: <span className="text-ink font-semibold">{ev.entry_hash?.slice(0, 16)}...</span>
                          </div>
                          <div className="text-2xs text-ink-tertiary pt-1 border-t border-border">
                            UTC: {ev.ts_utc}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                /* Folded Authenticity Panel */
                <div className="space-y-4">
                  {isImageExhibit && imageData && (
                    <div className="space-y-4">
                      <div className="p-3.5 rounded-lg border border-border bg-surface text-xs space-y-2">
                        <span className="font-bold uppercase tracking-wider text-ink block">EXIF Metadata Analysis</span>
                        <div className="grid grid-cols-2 gap-2 text-2xs">
                          <div>Software: <span className="font-semibold text-ink">{imageData.exif_software || 'None'}</span></div>
                          <div>Perceptual Hash: <span className="font-mono text-ink">{imageData.phash || 'N/A'}</span></div>
                        </div>
                        {imageData.reused_elsewhere && (
                          <div className="p-2 rounded bg-tomato-light border border-tomato text-tomato text-2xs font-bold">
                            Perceptual Hash Reused Across Multiple Exhibits!
                          </div>
                        )}
                      </div>
                      {imageData.ela_available && (
                        <div className="p-3.5 rounded-lg border border-border bg-surface text-xs space-y-2">
                          <span className="font-bold uppercase tracking-wider text-ink block">Error Level Analysis (ELA)</span>
                          <p className="text-2xs text-ink-secondary">Hotspot Ratio: {(imageData.hotspot_ratio * 100).toFixed(2)}%</p>
                          {imageData.ela_preview_url && (
                            <img src={imageData.ela_preview_url} alt="ELA Preview" className="w-full rounded border border-border max-h-48 object-contain bg-black" />
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {isStatementExhibit && statementData && (
                    <div className="p-3.5 rounded-lg border border-border bg-surface text-xs space-y-3">
                      <span className="font-bold uppercase tracking-wider text-ink block">Bank Statement Arithmetic Audit</span>
                      <div className="flex items-center justify-between text-2xs">
                        <span>Balance Arithmetic:</span>
                        <span className={`font-bold ${statementData.math_consistent ? 'text-lime-dark' : 'text-tomato'}`}>
                          {statementData.math_consistent ? 'CONSISTENT' : 'DISCREPANCY DETECTED'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-2xs">
                        <span>Total Rows Audited:</span>
                        <span className="font-mono text-ink">{statementData.total_rows || 0}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
