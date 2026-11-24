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
  Sparkles,
  FileCheck2,
  Link2,
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
      <div className="max-w-7xl mx-auto space-y-6">
        <WorkspaceHeader workspace="overview" title="Case Overview" />
        <ErrorState message="Could not reach the local PRAMAAN backend." onRetry={() => refetchInt()} />
      </div>
    );
  }

  const isLoading = intLoading || evLoading;
  const exhibitsCount = evidence?.length ?? 0;

  // Real counts per source family
  const familyCounts = (evidence || []).reduce<Record<string, number>>((acc, e) => {
    const fam = SOURCE_FAMILY_MAP[e.source_type] || e.source_type;
    acc[fam] = (acc[fam] || 0) + 1;
    return acc;
  }, {});
  const familiesCovered = Object.keys(familyCounts);

  const approvedCount = reviewQueue?.approved_count ?? 0;
  const totalReviewable = reviewQueue?.total_reviewable ?? 0;
  const pendingReview = reviewQueue?.total_pending ?? 0;
  const readinessPct = totalReviewable > 0 ? Math.round((approvedCount / totalReviewable) * 100) : 0;

  // Strongest lead edge from live graph
  const leadEdges = (graph?.edges || [])
    .map((e: any) => e.data || e)
    .filter((e: any) => e.tier === 'LEAD' || e.status === 'LEAD')
    .sort((a: any, b: any) => (b.strength || 0) - (a.strength || 0));
  const strongestLead = leadEdges[0] || null;
  const strongestStrengthPct = strongestLead ? Math.round((strongestLead.strength || 0) * 100) : 0;

  const highCount = (anomalies || []).filter((a) => a.severity === 'HIGH').length;
  const medCount = (anomalies || []).filter((a) => a.severity === 'MEDIUM').length;
  const lowCount = (anomalies || []).filter((a) => a.severity === 'LOW').length;
  const totalAnomalies = highCount + medCount + lowCount;

  const suggestedQuestion = startersData?.starters?.[0] || null;
  const unverifiedExhibits = (integrity?.exhibits || []).filter((x) => x.status !== 'PASS');
  const isIntact = integrity?.intact ?? true;

  return (
    <div className="max-w-7xl mx-auto space-y-7 pb-12">
      <WorkspaceHeader
        workspace="overview"
        title="Case Overview"
        subtitle="Two separated workspaces: court-ready provable evidence and cryptographic custody on the left, correlated investigation leads on the right."
        actions={
          <button
            type="button"
            onClick={() => navigate('/review')}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-[#C9C6BC] bg-white hover:border-[#316A78] hover:text-[#24525D] text-xs font-semibold text-[#20283A] transition-colors duration-150 shadow-sm cursor-pointer"
          >
            <FileCheck2 className="w-3.5 h-3.5 text-[#316A78]" aria-hidden="true" />
            <span>Review &amp; Report</span>
          </button>
        }
      />

      {isLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <SkeletonBlock className="lg:col-span-7 h-96" />
          <SkeletonBlock className="lg:col-span-5 h-96" />
        </div>
      ) : (
        /* Balanced Asymmetric 12-Column Composition */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          {/* WORKSPACE 1 HERO (7 cols): Evidence & Court Package — Midnight Ink Surface (#20283A) */}
          <section className="lg:col-span-7 obsidian-card text-white rounded-xl p-7 flex flex-col justify-between space-y-6 shadow-obsidian border border-[#32405A]">
            <div className="space-y-5">
              {/* Top Eyebrow + Tier */}
              <div className="flex items-center justify-between gap-3">
                <div className="inline-flex items-center gap-2 text-[#9AD0DB]">
                  <span className="w-2 h-2 rounded-full bg-[#68B2C0]" aria-hidden="true" />
                  <span className="font-sans text-[11px] font-bold uppercase tracking-[0.11em]">
                    Evidence and Court Package
                  </span>
                </div>
                <TierBadge tier={isIntact ? 'VERIFIED BY CODE' : 'TAMPERED'} size="sm" />
              </div>

              {/* Editorial Integrity Headline + Custody Metadata */}
              <div className="space-y-2">
                <h2 className="font-serif text-[34px] sm:text-[38px] text-white leading-[1.06] tracking-[-0.02em]">
                  {isIntact ? 'Integrity Seal Intact' : 'Integrity Breach Detected'}
                </h2>
                <div className="flex flex-wrap items-center gap-2.5 text-xs text-[#D5DFEC]">
                  <span className="inline-flex items-center gap-1.5 font-medium">
                    {isIntact ? (
                      <ShieldCheck className="w-3.5 h-3.5 text-[#7FD1C2]" aria-hidden="true" />
                    ) : (
                      <AlertTriangle className="w-3.5 h-3.5 text-[#F08C81]" aria-hidden="true" />
                    )}
                    <span>{integrity?.chain_intact ? 'Custody hash chain intact' : 'Custody chain invalid'}</span>
                  </span>
                  <span className="text-white/35">·</span>
                  <HashChip
                    hash={integrity?.merkle_root}
                    className="!bg-white/10 !border-white/25 !text-white hover:!bg-white/20 hover:!border-white/45"
                  />
                </div>
              </div>

              {/* Key Forensic Statistic Blocks (High Contrast) */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-4 rounded-lg bg-white/[0.08] border border-white/15">
                  <div className="font-sans text-[10px] font-bold uppercase tracking-[0.09em] text-[#C8D4E3]">
                    Exhibits Hashed
                  </div>
                  <div className="font-mono text-[26px] font-semibold text-white mt-1 leading-none">
                    {exhibitsCount}
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-white/[0.08] border border-white/15">
                  <div className="font-sans text-[10px] font-bold uppercase tracking-[0.09em] text-[#C8D4E3]">
                    Source Families
                  </div>
                  <div className="font-mono text-[26px] font-semibold text-white mt-1 leading-none">
                    {familiesCovered.length}
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-white/[0.08] border border-white/15">
                  <div className="font-sans text-[10px] font-bold uppercase tracking-[0.09em] text-[#C8D4E3]">
                    Approved Items
                  </div>
                  <div className="font-mono text-[26px] font-semibold text-[#8CE0BA] mt-1 leading-none">
                    {approvedCount}
                    <span className="text-sm text-[#B8C7DA] font-normal">/{totalReviewable}</span>
                  </div>
                </div>
              </div>

              {/* Court-Package Readiness Progress Bar */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[#D5DFEC] font-medium">Court-package readiness</span>
                  <span className="font-mono text-[11.5px] text-white font-semibold">
                    {approvedCount} of {totalReviewable} approved ({readinessPct}%)
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-white/15 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-[#4CA1AE] transition-all duration-300"
                    style={{ width: `${Math.max(readinessPct, approvedCount > 0 ? 4 : 0)}%` }}
                  />
                </div>
              </div>

              {/* Source Families Breakdown Tags */}
              <div className="space-y-2">
                <div className="font-sans text-[10px] font-bold uppercase tracking-[0.09em] text-[#C8D4E3]">
                  Ingested Source Coverage
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {familiesCovered.length > 0 ? (
                    familiesCovered.map((fam) => (
                      <span
                        key={fam}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-white/[0.10] border border-white/20 text-[11.5px] text-white font-medium"
                      >
                        <span>{fam}</span>
                        <span className="font-mono text-[10.5px] font-semibold text-[#9AD0DB]">
                          {familyCounts[fam]}
                        </span>
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-[#C8D4E3]">None ingested yet</span>
                  )}
                </div>
              </div>
            </div>

            {/* Bottom Actions — Explicit High-Contrast Styling */}
            <div className="pt-3 border-t border-white/15 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => navigate('/evidence')}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md bg-white hover:bg-[#EAF2F4] text-[#20283A] text-xs font-bold transition-colors duration-150 cursor-pointer shadow-sm"
              >
                <span>Open evidence vault</span>
                <ArrowRight className="w-3.5 h-3.5 text-[#316A78]" aria-hidden="true" />
              </button>
              <button
                type="button"
                onClick={() => navigate('/review')}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-md bg-white/10 hover:bg-white/20 border border-white/30 text-white text-xs font-semibold transition-colors duration-150 cursor-pointer"
              >
                <span>Admissibility Queue</span>
              </button>
            </div>
          </section>

          {/* WORKSPACE 2 PANEL (5 cols): Investigation — Pearl Surface with Teal & Slate Blue */}
          <section className="lg:col-span-5 editorial-card p-7 flex flex-col justify-between space-y-6">
            <div className="space-y-5">
              {/* Top Eyebrow + Tier */}
              <div className="flex items-center justify-between gap-2 pb-4 border-b border-border">
                <div className="inline-flex items-center gap-2 text-[#415E87]">
                  <Compass className="w-4 h-4 text-[#5576A5] shrink-0" aria-hidden="true" />
                  <span className="font-sans text-[11px] font-bold uppercase tracking-[0.1em]">
                    Investigation
                  </span>
                </div>
                <TierBadge tier="LEAD" size="sm" />
              </div>

              {/* Strongest Correlation Lead */}
              <div className="space-y-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="section-label inline-flex items-center gap-1.5">
                    <Link2 className="w-3 h-3 text-[#5576A5]" aria-hidden="true" />
                    {strongestLead ? 'Strongest Correlation Lead' : 'Awaiting Correlation Pipeline'}
                  </span>
                  {strongestLead && (
                    <span className="font-mono text-xs font-bold text-[#24525D] bg-[#EAF2F4] px-2 py-0.5 rounded border border-[#B2CDD4]">
                      {strongestStrengthPct}%
                    </span>
                  )}
                </div>
                <p className="font-serif text-[25px] text-[#20283A] leading-[1.2]">
                  {strongestLead
                    ? strongestLead.reason_text || `${strongestLead.edge_type} (strength ${strongestStrengthPct}%)`
                    : 'Ingest exhibits and run the pipeline to generate cross-source leads.'}
                </p>
                {strongestLead && (
                  <div className="h-1.5 w-full rounded-full bg-[#ECEAE3] overflow-hidden">
                    <div
                      className="h-full rounded-full bg-[#316A78] transition-all duration-300"
                      style={{ width: `${strongestStrengthPct}%` }}
                    />
                  </div>
                )}
              </div>

              {/* Anomaly Severity Distribution */}
              <div className="p-4 rounded-lg bg-[#F5F4F0] border border-border space-y-3">
                <div className="flex items-center justify-between">
                  <span className="section-label">Anomalies by Severity</span>
                  <span className="font-mono text-xs font-semibold text-[#20283A]">{totalAnomalies} total</span>
                </div>
                {totalAnomalies > 0 ? (
                  <div className="h-2.5 w-full rounded-full bg-[#E1DFD7] overflow-hidden flex gap-0.5">
                    {highCount > 0 && (
                      <div
                        className="h-full bg-[#D95749]"
                        style={{ width: `${(highCount / totalAnomalies) * 100}%` }}
                        title={`${highCount} HIGH`}
                      />
                    )}
                    {medCount > 0 && (
                      <div
                        className="h-full bg-[#D59A45]"
                        style={{ width: `${(medCount / totalAnomalies) * 100}%` }}
                        title={`${medCount} MEDIUM`}
                      />
                    )}
                    {lowCount > 0 && (
                      <div
                        className="h-full bg-[#316A78]"
                        style={{ width: `${(lowCount / totalAnomalies) * 100}%` }}
                        title={`${lowCount} LOW`}
                      />
                    )}
                  </div>
                ) : (
                  <div className="h-2 w-full rounded-full bg-[#E1DFD7]" />
                )}
                <div className="flex items-center justify-between font-mono text-[11px]">
                  <span className="inline-flex items-center gap-1.5 text-[#A63327] font-semibold">
                    <span className="w-2 h-2 rounded-full bg-[#D95749]" />
                    {highCount} HIGH
                  </span>
                  <span className="inline-flex items-center gap-1.5 text-[#8F6018] font-semibold">
                    <span className="w-2 h-2 rounded-full bg-[#D59A45]" />
                    {medCount} MED
                  </span>
                  <span className="inline-flex items-center gap-1.5 text-[#24525D] font-semibold">
                    <span className="w-2 h-2 rounded-full bg-[#316A78]" />
                    {lowCount} LOW
                  </span>
                </div>
              </div>

              {/* Actionable Suggested Investigative Prompt */}
              <button
                type="button"
                onClick={() => navigate('/assistant')}
                className="w-full text-left p-4 rounded-lg bg-[#EEF2F8] hover:bg-[#E4ECF6] border border-[#C1CFE4] hover:border-[#5576A5] transition-all duration-150 space-y-1.5 cursor-pointer group"
              >
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-1.5 font-sans text-[10px] font-bold uppercase tracking-[0.09em] text-[#415E87]">
                    <Sparkles className="w-3 h-3 text-[#5576A5]" aria-hidden="true" />
                    Suggested Investigative Prompt
                  </span>
                  <ArrowRight className="w-3.5 h-3.5 text-[#415E87] group-hover:translate-x-0.5 transition-transform" />
                </div>
                <p className="text-[13px] text-[#20283A] font-semibold leading-snug">
                  {suggestedQuestion ? `"${suggestedQuestion}"` : 'No case starters available yet'}
                </p>
              </button>
            </div>

            {/* Bottom Actions — Primary Deep Teal + Secondary Neutral */}
            <div className="pt-3 border-t border-border flex items-center gap-2.5">
              <button
                type="button"
                onClick={() => navigate('/graph')}
                className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-[#316A78] hover:bg-[#24525D] text-white text-xs font-bold transition-colors duration-150 cursor-pointer shadow-sm"
              >
                <span>Open investigation</span>
                <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
              </button>
              <button
                type="button"
                onClick={() => navigate('/reconstruction')}
                className="inline-flex items-center justify-center px-4 py-2.5 rounded-md border border-[#C9C6BC] bg-[#F5F4F0] hover:bg-[#ECEAE3] text-[#20283A] text-xs font-semibold transition-colors duration-150 cursor-pointer"
              >
                Timeline
              </button>
            </div>
          </section>
        </div>
      )}

      {/* Next Steps Action Strip */}
      <section className="editorial-card p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div className="flex items-center gap-2.5">
            <ListChecks className="w-4 h-4 text-[#316A78]" aria-hidden="true" />
            <h3 className="font-serif text-[26px] text-[#20283A] leading-none">Next Steps</h3>
          </div>
          <span className="font-mono text-[11px] font-semibold text-[#556077]">
            {unverifiedExhibits.length > 0
              ? `${unverifiedExhibits.length} critical alert`
              : pendingReview > 0
              ? `${pendingReview} pending review`
              : 'Ready for export'}
          </span>
        </div>

        <ul className="space-y-2.5 text-sm">
          {unverifiedExhibits.length > 0 && (
            <li className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-lg bg-[#FDF0EE] border border-[#D95749] text-[#A63327]">
              <span className="flex items-center gap-2.5 font-semibold text-xs sm:text-sm">
                <AlertTriangle className="w-4 h-4 text-[#C74437] shrink-0" aria-hidden="true" />
                <span>
                  {unverifiedExhibits.length} exhibit{unverifiedExhibits.length === 1 ? '' : 's'} failed integrity check:{' '}
                  <span className="font-mono">{unverifiedExhibits.map((x) => x.exhibit_id).join(', ')}</span>.
                </span>
              </span>
              <button
                type="button"
                onClick={() => navigate('/evidence')}
                className="px-3.5 py-1.5 rounded-md bg-[#C74437] text-white text-xs font-semibold hover:bg-[#A63327] transition-colors cursor-pointer shrink-0"
              >
                Inspect Exhibits →
              </button>
            </li>
          )}

          {exhibitsCount === 0 && (
            <li className="flex items-center justify-between gap-4 p-3.5 rounded-lg bg-[#F5F4F0] border border-border">
              <span className="text-[#20283A] text-[13.5px]">
                1. Upload raw exhibits in the Evidence Vault and run the correlation pipeline.
              </span>
              <button
                type="button"
                onClick={() => navigate('/evidence')}
                className="px-3.5 py-1.5 rounded-md bg-[#316A78] text-white text-xs font-semibold hover:bg-[#24525D] transition-colors cursor-pointer shrink-0"
              >
                Go to Evidence →
              </button>
            </li>
          )}

          {pendingReview > 0 && (
            <li className="flex items-center justify-between gap-4 p-3.5 rounded-lg bg-[#F5F4F0] border border-border hover:border-[#B2CDD4] transition-colors">
              <span className="text-[#20283A] text-[13.5px]">
                <strong className="font-mono text-[#24525D]">{pendingReview}</strong> proposed finding
                {pendingReview === 1 ? '' : 's'} awaiting human admissibility review before court export.
              </span>
              <button
                type="button"
                onClick={() => navigate('/review')}
                className="px-3.5 py-1.5 rounded-md border border-[#B2CDD4] bg-[#EAF2F4] text-[#24525D] hover:bg-[#316A78] hover:text-white text-xs font-semibold transition-colors cursor-pointer shrink-0"
              >
                Review Queue →
              </button>
            </li>
          )}

          {exhibitsCount > 0 && pendingReview === 0 && unverifiedExhibits.length === 0 && (
            <li className="flex items-center justify-between gap-4 p-3.5 rounded-lg bg-[#ECF6F1] border border-[#B2D9C7] text-[#246B4F]">
              <span className="flex items-center gap-2.5 text-[13.5px] font-medium">
                <CheckCircle2 className="w-4 h-4 shrink-0" aria-hidden="true" />
                All exhibits verified and review queue is clear. Ready to build and verify the court package.
              </span>
              <button
                type="button"
                onClick={() => navigate('/review')}
                className="px-3.5 py-1.5 rounded-md bg-[#246B4F] text-white text-xs font-semibold hover:opacity-90 transition-opacity cursor-pointer shrink-0"
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
