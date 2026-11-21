import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Check,
  X,
  Edit2,
  Package,
  HardDriveDownload,
  ExternalLink,
  Terminal,
  ShieldCheck,
  AlertTriangle,
  QrCode,
  CheckCheck,
} from 'lucide-react';
import {
  fetchReviewQueue,
  submitReviewDecision,
  submitBulkReview,
  fetchEventSource,
  fetchReportPreview,
  buildCourtPackage,
  runStandaloneVerifier,
  fetchBenchmarkResults,
} from '../lib/api';
import { WorkspaceHeader } from '../components/ui/WorkspaceHeader';
import { TierBadge } from '../components/ui/TierBadge';
import { HashChip } from '../components/ui/HashChip';
import { ExhibitChip } from '../components/evidence/ExhibitChip';
import { SkeletonBlock, EmptyState } from '../components/ui/Skeleton';

type Step = 'queue' | 'package' | 'verify';

export const ReviewAndReportPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialStep = (searchParams.get('step') as Step) || 'queue';
  const [step, setStep] = useState<Step>(initialStep);
  const queryClient = useQueryClient();

  const [selectedIndex, setSelectedIndex] = useState(0);
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState('');

  const { data: queueData, isLoading: queueLoading } = useQuery({
    queryKey: ['reviewQueue'],
    queryFn: fetchReviewQueue,
  });

  const { data: previewData, isLoading: previewLoading, refetch: refetchPreview } = useQuery({
    queryKey: ['reportPreview'],
    queryFn: fetchReportPreview,
    enabled: step === 'package',
  });

  const { data: benchmarkData } = useQuery({
    queryKey: ['benchmarkResults'],
    queryFn: fetchBenchmarkResults,
    enabled: step === 'verify',
  });

  const claims = queueData?.claims || [];
  const edges = queueData?.edges || [];
  const items = [...claims, ...edges];
  const currentItem = items[selectedIndex] || null;
  const primaryRefId = currentItem?.refs?.[0] || currentItem?.event_ids?.[0];

  const { data: sourceContext } = useQuery({
    queryKey: ['eventSource', primaryRefId],
    queryFn: () => (primaryRefId ? fetchEventSource(primaryRefId) : null),
    enabled: !!primaryRefId && step === 'queue',
  });

  const reviewMutation = useMutation({
    mutationFn: ({
      itemId,
      itemType,
      decision,
      text,
    }: {
      itemId: string;
      itemType: 'claim' | 'edge';
      decision: 'APPROVED' | 'REJECTED' | 'EDIT';
      text?: string;
    }) =>
      submitReviewDecision(itemId, {
        decision,
        item_type: itemType,
        edited_text: text,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviewQueue'] });
      queryClient.invalidateQueries({ queryKey: ['reportPreview'] });
      queryClient.invalidateQueries({ queryKey: ['graphData'] });
      setIsEditing(false);
      setEditedText('');
      if (selectedIndex >= items.length - 1) {
        setSelectedIndex(Math.max(0, items.length - 2));
      }
    },
  });

  const bulkMutation = useMutation({
    mutationFn: ({ group, decision }: { group: 'claims' | 'edges'; decision: 'APPROVED' | 'REJECTED' }) => {
      const target = group === 'claims' ? claims : edges;
      return submitBulkReview(
        target.map((it: any) => ({ item_id: it.id, item_type: it.item_type })),
        decision
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviewQueue'] });
      queryClient.invalidateQueries({ queryKey: ['reportPreview'] });
      setSelectedIndex(0);
    },
  });

  const buildMutation = useMutation({
    mutationFn: buildCourtPackage,
    onSuccess: () => refetchPreview(),
  });

  const verifyMutation = useMutation({
    mutationFn: runStandaloneVerifier,
  });

  // Keyboard shortcuts: A (Approve), R (Reject), E (Edit), J (Next), K (Prev)
  useEffect(() => {
    if (step !== 'queue') return;
    const onKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if (!currentItem) return;

      const key = e.key.toLowerCase();
      if (key === 'j') {
        setSelectedIndex((i) => Math.min(items.length - 1, i + 1));
      } else if (key === 'k') {
        setSelectedIndex((i) => Math.max(0, i - 1));
      } else if (key === 'a') {
        reviewMutation.mutate({
          itemId: currentItem.id,
          itemType: currentItem.item_type,
          decision: 'APPROVED',
        });
      } else if (key === 'r') {
        reviewMutation.mutate({
          itemId: currentItem.id,
          itemType: currentItem.item_type,
          decision: 'REJECTED',
        });
      } else if (key === 'e' && currentItem.item_type === 'claim') {
        setIsEditing(true);
        setEditedText(currentItem.text || '');
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [step, currentItem, items.length]);

  const switchStep = (s: Step) => {
    setStep(s);
    setSearchParams({ step: s });
  };

  const approvedCount = queueData?.approved_count ?? 0;
  const totalReviewable = queueData?.total_reviewable ?? 0;
  const pct = totalReviewable > 0 ? Math.round((approvedCount / totalReviewable) * 100) : 0;

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <WorkspaceHeader
        workspace="evidence"
        title="Review and Report"
        subtitle="The single admissibility gate: nothing from Investigation enters the court report until a human approves it here."
      />

      {/* 3-Step Flow Stepper */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-3">
        <div className="flex items-center gap-2" role="tablist" aria-label="Review and Report Steps">
          {[
            { id: 'queue', num: '1', label: `Review Queue (${items.length})` },
            { id: 'package', num: '2', label: 'Court Package' },
            { id: 'verify', num: '3', label: 'Verify & Trust Report' },
          ].map((s) => (
            <button
              key={s.id}
              type="button"
              role="tab"
              aria-selected={step === s.id}
              onClick={() => switchStep(s.id as Step)}
              className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded text-xs font-semibold border transition-colors duration-150 cursor-pointer ${
                step === s.id
                  ? 'bg-teal text-white border-teal'
                  : 'bg-panel text-muted border-border hover:text-ink'
              }`}
            >
              <span className="font-mono">{s.num}.</span>
              <span>{s.label}</span>
            </button>
          ))}
        </div>

        {/* Progress */}
        <div className="flex items-center gap-3 text-xs">
          <span className="font-mono text-muted">
            Approved: <strong className="text-ink">{approvedCount}</strong> / {totalReviewable} ({pct}%)
          </span>
          <div className="w-28 h-2 bg-paper-subtle border border-border rounded overflow-hidden">
            <div className="h-full bg-approved transition-all duration-150" style={{ width: `${pct}%` }} />
          </div>
        </div>
      </div>

      {/* STEP 1: REVIEW QUEUE */}
      {step === 'queue' && (
        <div className="space-y-4">
          {/* Bulk Approve Bar + Keyboard Legend */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-paper-subtle border border-border rounded px-4 py-2.5 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <span className="section-label">Bulk Actions:</span>
              <button
                type="button"
                disabled={claims.length === 0 || bulkMutation.isPending}
                onClick={() => bulkMutation.mutate({ group: 'claims', decision: 'APPROVED' })}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-teal-border bg-panel text-teal hover:bg-teal-light font-medium disabled:opacity-40 cursor-pointer"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                <span>Approve all verified claims ({claims.length})</span>
              </button>
              <button
                type="button"
                disabled={edges.length === 0 || bulkMutation.isPending}
                onClick={() => bulkMutation.mutate({ group: 'edges', decision: 'APPROVED' })}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-amber-border bg-panel text-amber hover:bg-amber-light font-medium disabled:opacity-40 cursor-pointer"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                <span>Approve all lead edges ({edges.length})</span>
              </button>
            </div>
            <div className="font-mono text-[11px] text-muted">
              Keys: <kbd className="px-1 border border-border rounded bg-panel">A</kbd> Approve ·{' '}
              <kbd className="px-1 border border-border rounded bg-panel">R</kbd> Reject ·{' '}
              <kbd className="px-1 border border-border rounded bg-panel">E</kbd> Edit ·{' '}
              <kbd className="px-1 border border-border rounded bg-panel">J</kbd>/<kbd className="px-1 border border-border rounded bg-panel">K</kbd> Next/Prev
            </div>
          </div>

          {queueLoading ? (
            <SkeletonBlock className="h-72" />
          ) : items.length === 0 ? (
            <EmptyState
              title="Review queue is clear"
              description="All proposed claims and lead edges have been adjudicated. Proceed to Court Package to preview and build the signed ZIP."
              action={
                <button
                  type="button"
                  onClick={() => switchStep('package')}
                  className="px-4 py-2 rounded bg-teal text-white text-xs font-semibold cursor-pointer"
                >
                  Continue to Court Package →
                </button>
              }
            />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
              {/* Left: Claim/Lead list + active item */}
              <div className="lg:col-span-6 space-y-4">
                <div className="bg-panel border border-border rounded p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-border pb-2">
                    <span className="section-label">
                      Item {selectedIndex + 1} of {items.length} ({currentItem.item_type})
                    </span>
                    <TierBadge tier={currentItem.tier || 'LEAD'} size="sm" />
                  </div>

                  {isEditing ? (
                    <textarea
                      value={editedText}
                      onChange={(e) => setEditedText(e.target.value)}
                      rows={4}
                      className="w-full p-2.5 border border-teal rounded text-sm font-sans bg-paper"
                    />
                  ) : (
                    <p className="text-sm text-ink leading-relaxed font-medium">
                      {currentItem.item_type === 'claim'
                        ? currentItem.text
                        : `${currentItem.src} → ${currentItem.dst} (${currentItem.edge_type}): ${currentItem.reason_text}`}
                    </p>
                  )}

                  <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border">
                    <button
                      type="button"
                      onClick={() =>
                        reviewMutation.mutate({
                          itemId: currentItem.id,
                          itemType: currentItem.item_type,
                          decision: isEditing ? 'EDIT' : 'APPROVED',
                          text: isEditing ? editedText : undefined,
                        })
                      }
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-approved text-white text-xs font-semibold cursor-pointer"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>{isEditing ? 'Save & Approve' : 'Approve (A)'}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        reviewMutation.mutate({
                          itemId: currentItem.id,
                          itemType: currentItem.item_type,
                          decision: 'REJECTED',
                        })
                      }
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-vermilion text-vermilion bg-panel hover:bg-vermilion-light text-xs font-semibold cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                      <span>Reject (R)</span>
                    </button>
                    {currentItem.item_type === 'claim' && !isEditing && (
                      <button
                        type="button"
                        onClick={() => {
                          setIsEditing(true);
                          setEditedText(currentItem.text || '');
                        }}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-border text-ink bg-paper hover:bg-paper-subtle text-xs font-medium cursor-pointer"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                        <span>Edit (E)</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Compact Queue List */}
                <div className="bg-panel border border-border rounded max-h-64 overflow-y-auto divide-y divide-border">
                  {items.map((it: any, idx: number) => (
                    <button
                      key={it.id}
                      type="button"
                      onClick={() => {
                        setSelectedIndex(idx);
                        setIsEditing(false);
                      }}
                      className={`w-full text-left px-3.5 py-2.5 text-xs flex items-center justify-between gap-2 cursor-pointer transition-colors duration-150 ${
                        idx === selectedIndex ? 'bg-teal-light font-semibold text-ink' : 'hover:bg-paper-subtle text-muted'
                      }`}
                    >
                      <span className="truncate">
                        {it.item_type === 'claim' ? it.text : `${it.src} → ${it.dst}: ${it.reason_text}`}
                      </span>
                      <TierBadge tier={it.tier || 'LEAD'} size="sm" />
                    </button>
                  ))}
                </div>
              </div>

              {/* Right: Underlying Source */}
              <div className="lg:col-span-6 bg-panel border border-border rounded p-4 space-y-3">
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <span className="section-label">Cited Source Record</span>
                  {sourceContext?.exhibit_id && (
                    <ExhibitChip exhibitId={sourceContext.exhibit_id} eventId={primaryRefId} />
                  )}
                </div>
                {sourceContext ? (
                  <div className="space-y-3 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-ink font-semibold">{sourceContext.filename}</span>
                      <HashChip hash={sourceContext.sha256} />
                    </div>
                    <div className="bg-ink text-paper font-mono text-xs p-3.5 rounded overflow-x-auto leading-relaxed">
                      {(sourceContext.context_before || []).map((l: string, i: number) => (
                        <div key={`b-${i}`} className="opacity-50">{l || ' '}</div>
                      ))}
                      <div className="bg-amber/20 text-[#FDE6C4] px-2 py-1 my-1 rounded border-l-2 border-amber">
                        {(sourceContext.target_lines || []).map((l: string, i: number) => (
                          <div key={`t-${i}`}>{l || ' '}</div>
                        ))}
                      </div>
                      {(sourceContext.context_after || []).map((l: string, i: number) => (
                        <div key={`a-${i}`} className="opacity-50">{l || ' '}</div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <EmptyState
                    title="No primary event source attached"
                    description="This item does not reference a specific line-level event ID."
                  />
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* STEP 2: COURT PACKAGE PREVIEW & BUILD */}
      {step === 'package' && (
        <div className="space-y-5">
          <div className="bg-panel border border-border rounded p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <h2 className="font-serif text-lg font-bold text-ink">Signed Court Package (.ZIP)</h2>
              <p className="text-xs text-muted">
                Includes approved findings only, exhibit manifest, Ed25519 signature, Section 63 draft certificate, and offline <code className="font-mono">verifier.py</code>.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={buildMutation.isPending}
                onClick={() => buildMutation.mutate()}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded bg-teal text-white text-xs font-semibold cursor-pointer"
              >
                <Package className={`w-3.5 h-3.5 ${buildMutation.isPending ? 'animate-spin' : ''}`} />
                <span>{buildMutation.isPending ? 'Building…' : 'Build Package'}</span>
              </button>
              <a
                href="/api/report/download"
                download
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded bg-vermilion text-white text-xs font-semibold"
              >
                <HardDriveDownload className="w-3.5 h-3.5" />
                <span>Download ZIP</span>
              </a>
              <a
                href="/api/report/pdf"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded border border-border bg-paper text-ink text-xs font-medium"
              >
                <span>View PDF</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>

          {previewLoading ? (
            <SkeletonBlock className="h-64" />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
              {/* Approved Findings Table */}
              <div className="lg:col-span-8 bg-panel border border-border rounded p-5 space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-2.5">
                  <h3 className="font-serif text-base font-bold text-ink">
                    Approved Findings ({(previewData?.approved_claims?.length || 0) + (previewData?.approved_edges?.length || 0)})
                  </h3>
                  <TierBadge tier="APPROVED" size="sm" />
                </div>

                {previewData?.approved_claims?.length === 0 && previewData?.approved_edges?.length === 0 ? (
                  <EmptyState
                    title="No human-approved findings yet"
                    description="Approve claims or lead edges in Step 1 (Review Queue) for them to appear in the court report."
                  />
                ) : (
                  <table className="w-full text-left border-collapse text-xs">
                    <thead className="bg-paper-subtle border-b border-border text-[11px] uppercase text-muted">
                      <tr>
                        <th className="py-2 px-2.5">Type</th>
                        <th className="py-2 px-2.5">Approved Statement</th>
                        <th className="py-2 px-2.5">Exhibit / Ref</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {(previewData?.approved_claims || []).map((c: any) => (
                        <tr key={c.id}>
                          <td className="py-2 px-2.5 font-mono text-teal">CLAIM</td>
                          <td className="py-2 px-2.5 text-ink">{c.text}</td>
                          <td className="py-2 px-2.5">
                            {c.refs?.[0] ? <ExhibitChip exhibitId="REF" eventId={c.refs[0]} /> : '—'}
                          </td>
                        </tr>
                      ))}
                      {(previewData?.approved_edges || []).map((e: any) => (
                        <tr key={e.id}>
                          <td className="py-2 px-2.5 font-mono text-approved">LINK</td>
                          <td className="py-2 px-2.5 text-ink">{e.src} → {e.dst}: {e.reason_text}</td>
                          <td className="py-2 px-2.5">
                            {e.event_ids?.[0] ? <ExhibitChip exhibitId="REF" eventId={e.event_ids[0]} /> : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}

                {/* Event Sequence Summary */}
                <div className="pt-3 border-t border-border space-y-2">
                  <h4 className="section-label">Reconstructed Event Sequence ({previewData?.episodes?.length || 0} episodes)</h4>
                  {(previewData?.episodes || []).map((ep: any) => (
                    <div key={ep.id} className="text-xs p-2.5 bg-paper border border-border rounded flex items-center justify-between gap-3">
                      <span className="font-medium text-ink">{ep.title}</span>
                      <span className="font-mono text-[11px] text-muted">{ep.start_ts_utc?.slice(0, 16)}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Section 63 Draft Certificate & QR Code */}
              <div className="lg:col-span-4 bg-panel border border-border rounded p-5 space-y-4">
                <div className="border-b border-border pb-2.5 space-y-1">
                  <span className="inline-block font-mono text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-amber-light text-amber border border-amber-border">
                    {previewData?.section63_draft?.status || 'DRAFT — HUMANS MUST SIGN'}
                  </span>
                  <h3 className="font-serif text-base font-bold text-ink">
                    Section 63 Certificate Annexure
                  </h3>
                </div>
                <p className="text-xs text-muted leading-relaxed">
                  {previewData?.section63_draft?.statement}
                </p>
                <div className="p-3 bg-paper border border-border rounded space-y-2">
                  <div className="section-label">Merkle Root</div>
                  <HashChip hash={previewData?.merkle_root} />
                </div>
                <div className="p-3 bg-paper border border-border rounded flex items-center gap-3">
                  <QrCode className="w-12 h-12 text-ink shrink-0" aria-hidden="true" />
                  <div className="text-[11px] font-mono text-muted break-all">
                    {previewData?.qr_payload}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* STEP 3: VERIFY & TRUST REPORT */}
      {step === 'verify' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Standalone Verifier */}
          <div className="lg:col-span-7 bg-panel border border-border rounded p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-teal" />
                <h2 className="font-serif text-base font-bold text-ink">Standalone Offline Verifier</h2>
              </div>
              <button
                type="button"
                disabled={verifyMutation.isPending}
                onClick={() => verifyMutation.mutate()}
                className="px-3.5 py-1.5 rounded bg-teal text-white text-xs font-semibold cursor-pointer"
              >
                {verifyMutation.isPending ? 'Running verifier.py…' : 'Run verifier.py'}
              </button>
            </div>

            {verifyMutation.data ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  {verifyMutation.data.verdict === 'PASS' ? (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-approved-light text-approved border border-approved-border font-mono text-xs font-bold">
                      <ShieldCheck className="w-4 h-4" />
                      PASS (exit {verifyMutation.data.returncode})
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-vermilion-light text-vermilion border border-vermilion font-mono text-xs font-bold">
                      <AlertTriangle className="w-4 h-4" />
                      FAIL (exit {verifyMutation.data.returncode})
                    </span>
                  )}
                  <span className="font-mono text-[11px] text-muted">{verifyMutation.data.verified_at_utc}</span>
                </div>
                <pre className="bg-ink text-paper font-mono text-xs p-4 rounded overflow-x-auto leading-relaxed max-h-96">
                  {verifyMutation.data.output}
                </pre>
              </div>
            ) : (
              <EmptyState
                title="Verifier not run yet"
                description="Click 'Run verifier.py' to execute the standalone zero-dependency cryptographic audit on the assembled package."
              />
            )}
          </div>

          {/* Trust Report (Saved Benchmark Results) */}
          <div className="lg:col-span-5 bg-panel border border-border rounded p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h2 className="font-serif text-base font-bold text-ink">Trust Report</h2>
              <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-amber-light text-amber border border-amber-border">
                synthetic dataset
              </span>
            </div>
            <div className="space-y-3 text-xs">
              <div className="p-3 bg-teal-light border border-teal-border rounded space-y-1">
                <div className="font-semibold text-teal">Proven by Deterministic Code &amp; Tests</div>
                <p className="text-ink">
                  SHA-256 streaming ingest, append-only SQLite custody triggers, Merkle root, Ed25519 manifest signature, bank running-balance math, and claim verifier rules V1–V5.
                </p>
              </div>
              <div className="p-3 bg-amber-light border border-amber-border rounded space-y-1">
                <div className="font-semibold text-amber">Probabilistic / Heuristic (Requires Human Review)</div>
                <p className="text-ink">
                  Cross-source correlation scores, IndicNER entity extraction, and Assistant natural-language planning.
                </p>
              </div>
              {benchmarkData && (
                <pre className="p-3 bg-paper border border-border rounded font-mono text-[11px] overflow-x-auto max-h-64">
                  {JSON.stringify(benchmarkData, null, 2)}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
