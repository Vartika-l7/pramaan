import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ShieldCheck,
  AlertTriangle,
  Compass,
  ArrowRight,
  CheckCircle2,
  ListChecks,
} from 'lucide-react';
import {
  fetchIntegrityStatus,
  fetchEvidenceList,
  fetchAnomalies,
  fetchGraph,
  fetchReviewQueue,
} from '../lib/api';
import { WorkspaceHeader } from '../components/ui/WorkspaceHeader';
import { TierBadge } from '../components/ui/TierBadge';
import { HashChip } from '../components/ui/HashChip';
import { SkeletonBlock, ErrorState } from '../components/ui/Skeleton';

const SOURCE_FAMILY_MAP: Record<string, string> = {
  calllog: 'Mobile',
  whatsapp: 'Social Media',
  social_media: 'Social Media',
  social_telegram: 'Social Media',
  social_generic: 'Social Media',
  image: 'Media / CCTV',
  cctv: 'CCTV',
  cctv_index: 'CCTV',
  cctv_video: 'CCTV',
  cloud: 'Cloud',
  cloud_location: 'Cloud',
  cloud_activity: 'Cloud',
  bank_pdf: 'Financial',
  bank_csv: 'Financial',
  email: 'Email',
  network_log: 'Network',
};

export const OverviewPage: React.FC = () => {
  const navigate = useNavigate();

  const { data: integrity, isLoading: intLoading, isError: intError, refetch: refetchInt } = useQuery({
    queryKey: ['integrityStatus'],
    queryFn: fetchIntegrityStatus,
  });
  const { data: evidence, isLoading: evLoading } = useQuery({
    queryKey: ['evidenceList'],
    queryFn: fetchEvidenceList,
  });
  const { data: reviewQueue } = useQuery({
    queryKey: ['reviewQueue'],
    queryFn: fetchReviewQueue,
  });
  const { data: anomalies } = useQuery({
    queryKey: ['anomaliesList'],
    queryFn: () => fetchAnomalies(),
  });
  const { data: graph } = useQuery({
    queryKey: ['graphData'],
    queryFn: () => fetchGraph(),
  });
  const { data: startersData } = useQuery({
    queryKey: ['assistantStarters'],
    queryFn: async () => {
      const r = await fetch('/api/assistant/starters');
      return r.json();
    },
  });

  if (intError) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        <WorkspaceHeader workspace="overview" title="Case Overview" />
        <ErrorState message="Could not reach the local PRAMAAN backend." onRetry={() => refetchInt()} />
      </div>
    );
  }

  const isLoading = intLoading || evLoading;
  const exhibitsCount = evidence?.length ?? 0;
  const familiesCovered = Array.from(
    new Set((evidence || []).map((e) => SOURCE_FAMILY_MAP[e.source_type] || e.source_type))
  );

  const approvedCount = reviewQueue?.approved_count ?? 0;
  const totalReviewable = reviewQueue?.total_reviewable ?? 0;
  const pendingReview = reviewQueue?.total_pending ?? 0;

  // Strongest lead edge from live graph
  const leadEdges = (graph?.edges || [])
    .map((e: any) => e.data || e)
    .filter((e: any) => e.tier === 'LEAD' || e.status === 'LEAD')
    .sort((a: any, b: any) => (b.strength || 0) - (a.strength || 0));
  const strongestLead = leadEdges[0] || null;

  const highCount = (anomalies || []).filter((a) => a.severity === 'HIGH').length;
  const medCount = (anomalies || []).filter((a) => a.severity === 'MEDIUM').length;
  const lowCount = (anomalies || []).filter((a) => a.severity === 'LOW').length;

  const suggestedQuestion = startersData?.starters?.[0] || null;
  const unverifiedExhibits = (integrity?.exhibits || []).filter((x) => x.status !== 'PASS');

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <WorkspaceHeader
        workspace="overview"
        title="Case Overview"
        subtitle="Two separated workspaces: court-ready provable evidence on the left, AI-assisted investigation leads on the right."
      />

      {isLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonBlock className="h-72" />
          <SkeletonBlock className="h-72" />
        </div>
      ) : (
        /* Two side-by-side workspace panels */
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* WORKSPACE 1 PANEL: Evidence and Court Package */}
          <section className="bg-panel border border-border border-t-4 border-t-teal rounded p-6 flex flex-col justify-between space-y-5">
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-2 border-b border-border pb-3">
                <div className="flex items-center gap-2 text-teal">
                  <ShieldCheck className="w-4 h-4 shrink-0" aria-hidden="true" />
                  <span className="font-sans text-xs font-bold uppercase tracking-[0.08em]">
                    Evidence and Court Package
                  </span>
                </div>
                <TierBadge tier={integrity?.intact ? 'VERIFIED BY CODE' : 'TAMPERED'} size="sm" />
              </div>

              <div className="space-y-1">
                <h2 className="font-serif text-xl font-bold text-ink">
                  {integrity?.intact ? 'Integrity Seal Intact' : 'Integrity Breach Detected'}
                </h2>
                <div className="flex items-center gap-2 text-xs text-muted">
                  <span>{integrity?.chain_intact ? 'Custody hash chain intact' : 'Custody chain invalid'}</span>
                  <span>·</span>
                  <HashChip hash={integrity?.merkle_root} />
                </div>
              </div>

              <dl className="divide-y divide-border text-sm border-y border-border">
                <div className="py-2.5 flex items-center justify-between gap-4">
                  <dt className="text-muted">Exhibits hashed</dt>
                  <dd className="font-mono font-semibold text-ink">{exhibitsCount}</dd>
                </div>
                <div className="py-2.5 flex items-start justify-between gap-4">
                  <dt className="text-muted shrink-0">Source families</dt>
                  <dd className="text-right font-medium text-ink">
                    {familiesCovered.length > 0 ? familiesCovered.join(', ') : 'None ingested yet'}
                  </dd>
                </div>
                <div className="py-2.5 flex items-center justify-between gap-4">
                  <dt className="text-muted">Court-package readiness</dt>
                  <dd className="font-mono font-semibold text-ink">
                    {approvedCount} of {totalReviewable} items approved for the report
                  </dd>
                </div>
              </dl>
            </div>

            <div>
              <button
                type="button"
                onClick={() => navigate('/evidence')}
                className="inline-flex items-center gap-2 px-4 py-2 rounded bg-teal text-white text-sm font-medium hover:opacity-90 transition-opacity duration-150 cursor-pointer"
              >
                <span>Open evidence vault</span>
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>
          </section>

          {/* WORKSPACE 2 PANEL: Investigation */}
          <section className="bg-panel border border-border border-t-4 border-t-amber rounded p-6 flex flex-col justify-between space-y-5">
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-2 border-b border-border pb-3">
                <div className="flex items-center gap-2 text-amber">
                  <Compass className="w-4 h-4 shrink-0" aria-hidden="true" />
                  <span className="font-sans text-xs font-bold uppercase tracking-[0.08em]">
                    Investigation
                  </span>
                </div>
                <TierBadge tier="LEAD" size="sm" />
              </div>

              <div className="space-y-1">
                <h2 className="font-serif text-xl font-bold text-ink">
                  {strongestLead ? 'Strongest Correlation Lead' : 'Awaiting Correlation Pipeline'}
                </h2>
                <p className="text-sm text-muted">
                  {strongestLead
                    ? strongestLead.reason_text || `${strongestLead.edge_type} (strength ${Math.round((strongestLead.strength || 0) * 100)}%)`
                    : 'Ingest exhibits and run the pipeline to generate cross-source leads.'}
                </p>
              </div>

              <dl className="divide-y divide-border text-sm border-y border-border">
                <div className="py-2.5 flex items-center justify-between gap-4">
                  <dt className="text-muted">Anomalies by severity</dt>
                  <dd className="font-mono text-xs flex items-center gap-2">
                    <span className="text-vermilion font-semibold">{highCount} HIGH</span>
                    <span className="text-muted">·</span>
                    <span className="text-amber font-semibold">{medCount} MED</span>
                    <span className="text-muted">·</span>
                    <span className="text-ink">{lowCount} LOW</span>
                  </dd>
                </div>
                <div className="py-2.5 flex items-start justify-between gap-4">
                  <dt className="text-muted shrink-0">Suggested question</dt>
                  <dd className="text-right text-ink italic">
                    {suggestedQuestion ? `"${suggestedQuestion}"` : 'No case starters available yet'}
                  </dd>
                </div>
              </dl>
            </div>

            <div>
              <button
                type="button"
                onClick={() => navigate('/graph')}
                className="inline-flex items-center gap-2 px-4 py-2 rounded bg-amber text-white text-sm font-medium hover:opacity-90 transition-opacity duration-150 cursor-pointer"
              >
                <span>Open investigation</span>
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>
          </section>
        </div>
      )}

      {/* Next steps list */}
      <section className="bg-panel border border-border rounded p-5 space-y-3">
        <div className="flex items-center gap-2 border-b border-border pb-2.5">
          <ListChecks className="w-4 h-4 text-ink" aria-hidden="true" />
          <h3 className="font-serif text-base font-bold text-ink">Next Steps</h3>
        </div>
        <ul className="space-y-2 text-sm">
          {exhibitsCount === 0 && (
            <li className="flex items-center justify-between gap-4 py-1">
              <span className="text-ink">1. Upload raw exhibits in the Evidence Vault and run the correlation pipeline.</span>
              <button
                type="button"
                onClick={() => navigate('/evidence')}
                className="text-xs font-medium text-teal hover:underline cursor-pointer shrink-0"
              >
                Go to Evidence →
              </button>
            </li>
          )}
          {pendingReview > 0 && (
            <li className="flex items-center justify-between gap-4 py-1">
              <span className="text-ink">
                {pendingReview} proposed finding{pendingReview === 1 ? '' : 's'} awaiting human admissibility review before court export.
              </span>
              <button
                type="button"
                onClick={() => navigate('/review')}
                className="text-xs font-medium text-teal hover:underline cursor-pointer shrink-0"
              >
                Review Queue →
              </button>
            </li>
          )}
          {unverifiedExhibits.length > 0 && (
            <li className="flex items-center gap-2 py-1 text-vermilion font-medium">
              <AlertTriangle className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>
                {unverifiedExhibits.length} exhibit{unverifiedExhibits.length === 1 ? '' : 's'} failed integrity check:{' '}
                {unverifiedExhibits.map((x) => x.exhibit_id).join(', ')}.
              </span>
            </li>
          )}
          {exhibitsCount > 0 && pendingReview === 0 && unverifiedExhibits.length === 0 && (
            <li className="flex items-center justify-between gap-4 py-1 text-approved">
              <span className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" aria-hidden="true" />
                All exhibits verified and review queue is clear. Ready to build and verify the court package.
              </span>
              <button
                type="button"
                onClick={() => navigate('/review')}
                className="text-xs font-medium text-teal hover:underline cursor-pointer shrink-0"
              >
                Open Review and Report →
              </button>
            </li>
          )}
        </ul>
      </section>
    </div>
  );
};
