import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Upload,
  X,
  Lock,
  ShieldCheck,
  AlertTriangle,
  FileSearch,
  RefreshCw,
} from 'lucide-react';
import {
  fetchEvidenceList,
  uploadEvidenceFile,
  fetchEvidenceDetail,
  fetchImageAuthenticity,
  fetchStatementCheck,
  computeBrowserSha256,
} from '../lib/api';
import { WorkspaceHeader } from '../components/ui/WorkspaceHeader';
import { TierBadge } from '../components/ui/TierBadge';
import { HashChip } from '../components/ui/HashChip';
import { ExhibitChip } from '../components/evidence/ExhibitChip';
import { SkeletonBlock, EmptyState, ErrorState } from '../components/ui/Skeleton';

const SOURCE_FAMILIES: Array<{ id: string; label: string; types: string[] }> = [
  { id: 'ALL', label: 'All Families', types: [] },
  { id: 'mobile', label: 'Mobile', types: ['calllog'] },
  { id: 'social', label: 'Social Media', types: ['whatsapp', 'social_media'] },
  { id: 'cctv', label: 'CCTV / Media', types: ['image', 'cctv'] },
  { id: 'cloud', label: 'Cloud', types: ['cloud'] },
  { id: 'financial', label: 'Financial', types: ['bank_pdf', 'bank_csv'] },
  { id: 'email', label: 'Email', types: ['email'] },
  { id: 'network', label: 'Network', types: ['network_log'] },
];

function familyForType(sourceType: string): string {
  const found = SOURCE_FAMILIES.find((f) => f.types.includes(sourceType));
  return found ? found.label : sourceType;
}

export const EvidenceVaultPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedExhibit, setSelectedExhibit] = useState<string | null>(null);
  const [drawerTab, setDrawerTab] = useState<'custody' | 'parse' | 'authenticity' | 'mentions'>('custody');
  const [familyFilter, setFamilyFilter] = useState<string>('ALL');
  const [isDragging, setIsDragging] = useState(false);
  const [rehashMsg, setRehashMsg] = useState<string | null>(null);

  const { data: exhibits, isLoading, isError, refetch } = useQuery({
    queryKey: ['evidenceList'],
    queryFn: fetchEvidenceList,
  });

  const { data: detailData, isLoading: detailLoading } = useQuery({
    queryKey: ['evidenceDetail', selectedExhibit],
    queryFn: () => (selectedExhibit ? fetchEvidenceDetail(selectedExhibit) : null),
    enabled: !!selectedExhibit,
  });

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
    Array.from(e.dataTransfer.files).forEach((file) => uploadMutation.mutate(file));
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      Array.from(e.target.files).forEach((file) => uploadMutation.mutate(file));
    }
  };

  const handleBrowserRehash = async (e: React.ChangeEvent<HTMLInputElement>, expectedHash: string) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const computed = await computeBrowserSha256(file);
    if (computed.toLowerCase() === expectedHash.toLowerCase()) {
      setRehashMsg(`MATCH: Browser SHA-256 (${computed.slice(0, 8)}…${computed.slice(-4)}) matches stored digest.`);
    } else {
      setRehashMsg(`MISMATCH: Browser computed ${computed.slice(0, 8)}…${computed.slice(-4)}, expected ${expectedHash.slice(0, 8)}…${expectedHash.slice(-4)}.`);
    }
  };

  const filteredExhibits = (exhibits || []).filter((ex) => {
    if (familyFilter === 'ALL') return true;
    const fam = SOURCE_FAMILIES.find((f) => f.id === familyFilter);
    return fam ? fam.types.includes(ex.source_type) : true;
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <WorkspaceHeader
        workspace="evidence"
        title="Evidence Vault"
        subtitle="Content-addressed read-only exhibit storage. Files are SHA-256 hashed in streaming chunks at ingest and sealed in the custody chain."
        actions={
          <label className="inline-flex items-center gap-2 px-3.5 py-2 bg-teal text-white text-xs font-semibold rounded cursor-pointer hover:opacity-90 transition-opacity duration-150">
            <Upload className="w-3.5 h-3.5" aria-hidden="true" />
            <span>{uploadMutation.isPending ? 'Hashing…' : 'Upload Exhibit'}</span>
            <input type="file" multiple onChange={handleFileInput} className="hidden" />
          </label>
        }
      />

      {/* Compact Drag-and-Drop Bar */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`border border-dashed rounded px-5 py-4 flex flex-col sm:flex-row items-center justify-between gap-3 transition-colors duration-150 ${
          isDragging ? 'border-teal bg-teal-light' : 'border-border-strong bg-panel hover:border-teal'
        }`}
      >
        <div className="text-xs text-muted">
          <span className="font-semibold text-ink">Drag and drop exhibits here</span> to compute SHA-256 on ingest (mobile, social media, CCTV, cloud, financial, email, network).
        </div>
        {uploadMutation.data && (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-approved font-semibold">Ingested:</span>
            <HashChip hash={uploadMutation.data.sha256} />
          </div>
        )}
      </div>

      {/* Source Family Filters */}
      <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Filter by source family">
        {SOURCE_FAMILIES.map((fam) => (
          <button
            key={fam.id}
            type="button"
            onClick={() => setFamilyFilter(fam.id)}
            className={`px-3 py-1 rounded text-xs font-medium border transition-colors duration-150 cursor-pointer ${
              familyFilter === fam.id
                ? 'bg-teal text-white border-teal'
                : 'bg-panel text-muted border-border hover:text-ink hover:border-border-strong'
            }`}
          >
            {fam.label}
          </button>
        ))}
      </div>

      {/* Dense Exhibits Table */}
      {isError ? (
        <ErrorState message="Failed to load exhibits." onRetry={() => refetch()} />
      ) : isLoading ? (
        <SkeletonBlock className="h-64" />
      ) : filteredExhibits.length === 0 ? (
        <EmptyState
          title="No exhibits match this filter"
          description="Upload forensic files above or switch the source family filter to view registered exhibits."
        />
      ) : (
        <div className="bg-panel border border-border rounded overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-paper-subtle border-b border-border text-[11px] font-semibold uppercase tracking-wider text-muted">
              <tr>
                <th className="py-2.5 px-3">Exhibit ID</th>
                <th className="py-2.5 px-3">Filename</th>
                <th className="py-2.5 px-3">Family / Type</th>
                <th className="py-2.5 px-3">Size</th>
                <th className="py-2.5 px-3">SHA-256</th>
                <th className="py-2.5 px-3">Received (UTC)</th>
                <th className="py-2.5 px-3">Parse Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredExhibits.map((ex) => (
                <tr
                  key={ex.id}
                  onClick={() => {
                    setSelectedExhibit(ex.id);
                    setRehashMsg(null);
                  }}
                  className={`ledger-row cursor-pointer ${selectedExhibit === ex.id ? 'bg-teal-light/60' : ''}`}
                >
                  <td className="py-2.5 px-3">
                    <ExhibitChip exhibitId={ex.exhibit_id} />
                  </td>
                  <td className="py-2.5 px-3 font-medium text-ink">{ex.filename}</td>
                  <td className="py-2.5 px-3 text-muted">
                    {familyForType(ex.source_type)} <span className="font-mono text-[11px]">({ex.source_type})</span>
                  </td>
                  <td className="py-2.5 px-3 font-mono text-muted">
                    {(ex.size_bytes / 1024).toFixed(1)} KB
                  </td>
                  <td className="py-2.5 px-3" onClick={(e) => e.stopPropagation()}>
                    <HashChip hash={ex.sha256} />
                  </td>
                  <td className="py-2.5 px-3 font-mono text-muted">
                    {ex.received_at_utc?.slice(0, 19).replace('T', ' ')}
                  </td>
                  <td className="py-2.5 px-3">
                    <span className="font-mono text-[11px] px-2 py-0.5 rounded border border-teal-border bg-teal-light text-teal font-semibold">
                      {ex.parse_status || 'PENDING'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail Drawer */}
      {selectedExhibit && (
        <div className="fixed inset-0 z-50 flex justify-end bg-ink/35" role="dialog" aria-label="Exhibit Details">
          <div className="w-full max-w-2xl bg-panel h-full border-l border-border-strong flex flex-col">
            <div className="h-14 border-b border-border px-5 flex items-center justify-between bg-paper">
              <div className="flex items-center gap-2.5">
                <span className="exhibit-id">{detailData?.exhibit_id || 'EXH'}</span>
                <h2 className="font-serif text-base font-bold text-ink truncate">
                  {detailData?.filename || 'Loading exhibit…'}
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setSelectedExhibit(null)}
                aria-label="Close Exhibit Drawer"
                className="p-1.5 rounded hover:bg-paper-subtle text-muted hover:text-ink cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Re-hash in browser bar */}
            {detailData && (
              <div className="px-5 py-3 bg-paper-subtle border-b border-border flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className="section-label">Stored Digest:</span>
                  <HashChip hash={detailData.sha256} />
                </div>
                <label className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-teal text-teal bg-panel hover:bg-teal-light font-medium cursor-pointer transition-colors duration-150">
                  <RefreshCw className="w-3 h-3" aria-hidden="true" />
                  <span>Re-hash in browser</span>
                  <input
                    type="file"
                    onChange={(e) => handleBrowserRehash(e, detailData.sha256)}
                    className="hidden"
                  />
                </label>
                {rehashMsg && (
                  <p className={`w-full font-mono text-xs ${rehashMsg.startsWith('MATCH') ? 'text-approved' : 'text-vermilion'}`}>
                    {rehashMsg}
                  </p>
                )}
              </div>
            )}

            {/* Tabs */}
            <div className="flex border-b border-border px-5 gap-4 bg-paper text-xs font-medium">
              {[
                { id: 'custody', label: 'Chain of custody' },
                { id: 'parse', label: 'Parse report' },
                { id: 'authenticity', label: 'Authenticity' },
                { id: 'mentions', label: 'Mentions' },
              ].map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setDrawerTab(t.id as any)}
                  className={`py-2.5 border-b-2 transition-colors duration-150 cursor-pointer ${
                    drawerTab === t.id
                      ? 'border-teal text-teal font-semibold'
                      : 'border-transparent text-muted hover:text-ink'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4 text-xs">
              {detailLoading ? (
                <SkeletonBlock className="h-40" />
              ) : drawerTab === 'custody' ? (
                <div className="space-y-2">
                  {(detailData?.custody_events || []).map((c: any) => (
                    <div key={c.seq} className="p-3 bg-paper border border-border rounded font-mono flex items-start justify-between">
                      <div>
                        <div className="font-bold text-ink">
                          <Lock className="w-3 h-3 inline mr-1.5 text-teal" />
                          #{c.seq} {c.action}
                        </div>
                        <div className="text-[11px] text-muted mt-1">Actor: {c.actor} · Hash: {c.entry_hash?.slice(0, 12)}…</div>
                      </div>
                      <span className="text-[11px] text-muted">{c.ts_utc?.slice(0, 19).replace('T', ' ')}</span>
                    </div>
                  ))}
                </div>
              ) : drawerTab === 'parse' ? (
                detailData?.parse_report ? (
                  <div className="space-y-3">
                    <div className="grid grid-cols-3 gap-3">
                      <div className="p-3 bg-paper border border-border rounded">
                        <div className="section-label">Total Units</div>
                        <div className="font-mono text-lg font-bold text-ink mt-1">{detailData.parse_report.total_units}</div>
                      </div>
                      <div className="p-3 bg-paper border border-border rounded">
                        <div className="section-label">Parsed Events</div>
                        <div className="font-mono text-lg font-bold text-teal mt-1">{detailData.parse_report.parsed_events}</div>
                      </div>
                      <div className="p-3 bg-paper border border-border rounded">
                        <div className="section-label">Skipped / Errors</div>
                        <div className="font-mono text-lg font-bold text-amber mt-1">
                          {(detailData.parse_report.skipped_units?.length || 0) + (detailData.parse_report.errors?.length || 0)}
                        </div>
                      </div>
                    </div>
                    <pre className="p-3 bg-paper border border-border rounded font-mono text-[11px] overflow-x-auto">
                      {JSON.stringify(detailData.parse_report, null, 2)}
                    </pre>
                  </div>
                ) : (
                  <EmptyState title="No parse report recorded" description="Run the pipeline or re-ingest this exhibit to record unit reconciliation." />
                )
              ) : drawerTab === 'authenticity' ? (
                isImageExhibit ? (
                  imageLoading ? <SkeletonBlock className="h-32" /> : (
                    <div className="space-y-3">
                      <div className="p-3 bg-paper border border-border rounded flex items-center justify-between">
                        <span className="font-semibold text-ink">Image Forensics Verdict</span>
                        <TierBadge tier={imageData?.tampered ? 'TAMPERED' : 'VERIFIED BY CODE'} size="sm" />
                      </div>
                      <pre className="p-3 bg-paper border border-border rounded font-mono text-[11px] overflow-x-auto">
                        {JSON.stringify(imageData, null, 2)}
                      </pre>
                    </div>
                  )
                ) : isStatementExhibit ? (
                  statementLoading ? <SkeletonBlock className="h-32" /> : (
                    <div className="space-y-3">
                      <div className="p-3 bg-paper border border-border rounded flex items-center justify-between">
                        <span className="font-semibold text-ink">Bank Ledger Arithmetic Check</span>
                        <TierBadge tier={statementData?.mismatches?.length ? 'TAMPERED' : 'VERIFIED BY CODE'} size="sm" />
                      </div>
                      <pre className="p-3 bg-paper border border-border rounded font-mono text-[11px] overflow-x-auto">
                        {JSON.stringify(statementData, null, 2)}
                      </pre>
                    </div>
                  )
                ) : (
                  <EmptyState title="No binary authenticity check" description="Authenticity checks apply to images (EXIF/ELA/pHash) and bank statements (running-balance math)." />
                )
              ) : (
                /* Mentions tab */
                (detailData as any)?.mentions?.length ? (
                  <div className="space-y-2">
                    {(detailData as any).mentions.map((m: any) => (
                      <div key={m.id} className="p-2.5 bg-paper border border-border rounded flex items-center justify-between gap-2">
                        <div>
                          <span className="font-mono text-[11px] font-semibold text-teal">{m.entity_type}</span>
                          <span className="mx-1.5 text-muted">·</span>
                          <span className="font-semibold text-ink">{m.entity_display}</span>
                          <div className="text-[11px] text-muted truncate max-w-md mt-0.5">{m.event_text}</div>
                        </div>
                        <TierBadge tier={m.tier} size="sm" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState title="No entity mentions extracted" description="Run the pipeline to extract entities and spans from this exhibit." />
                )
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
