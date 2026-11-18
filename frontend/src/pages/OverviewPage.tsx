import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  FolderArchive,
  Users,
  Clock,
  ArrowRight,
  AlertTriangle,
  Compass,
  CheckCircle2,
  FileCheck2,
  Layers,
  ShieldCheck,
  Activity,
  Lock,
  ArrowUpRight,
  Radio,
  Fingerprint,
  FileSpreadsheet,
  FileText,
  Key,
  Hash,
  ChevronRight,
  Eye,
  SlidersHorizontal,
  Zap,
  Target,
  Sparkles,
} from 'lucide-react';
import {
  fetchIntegrityStatus,
  fetchEvidenceList,
  fetchAnomalies,
  fetchEntities,
  fetchGraph,
} from '../lib/api';
import { TierBadge } from '../components/ui/TierBadge';
import { ExhibitChip } from '../components/evidence/ExhibitChip';
import { useAppStore } from '../lib/store';

export const OverviewPage: React.FC = () => {
  const navigate = useNavigate();
  const openSourceViewer = useAppStore((state) => state.openSourceViewer);

  const { data: integrity } = useQuery({ queryKey: ['integrityStatus'], queryFn: fetchIntegrityStatus });
  const { data: evidence } = useQuery({ queryKey: ['evidenceList'], queryFn: fetchEvidenceList });
  const { data: anomalies } = useQuery({ queryKey: ['anomaliesList'], queryFn: () => fetchAnomalies() });
  const { data: entities } = useQuery({ queryKey: ['entitiesList'], queryFn: () => fetchEntities() });
  const { data: graph } = useQuery({ queryKey: ['graphData'], queryFn: () => fetchGraph() });

  const exhibitsCount = evidence?.length || 0;
  const highAnomalies = anomalies?.filter((a) => a.severity === 'HIGH') || [];
  const mediumAnomalies = anomalies?.filter((a) => a.severity === 'MEDIUM') || [];

  // Breakdown by source type with new editorial palette
  const sourceBreakdown: Record<string, { count: number; color: string; label: string }> = {
    whatsapp: { count: 0, color: '#315FCE', label: 'WhatsApp Chat Exports' },
    bank_pdf: { count: 0, color: '#E7B75B', label: 'Bank Statement PDFs' },
    bank_csv: { count: 0, color: '#B9A4D8', label: 'Bank Statement CSVs' },
    calllog: { count: 0, color: '#8FA820', label: 'CDR Cellular Tower Logs' },
    image: { count: 0, color: '#F05A3A', label: 'Screenshots & Media' },
  };

  evidence?.forEach((ev) => {
    if (sourceBreakdown[ev.source_type]) {
      sourceBreakdown[ev.source_type].count += 1;
    }
  });

  const [activeTabAnomaly, setActiveTabAnomaly] = useState<string>('ALL');

  const filteredAnomalies =
    activeTabAnomaly === 'HIGH'
      ? highAnomalies
      : activeTabAnomaly === 'MEDIUM'
      ? mediumAnomalies
      : anomalies || [];

  return (
    <div className="space-y-10 max-w-7xl mx-auto pb-16">

      {/* ═══════════════════════════════════════════════
          SECTION A — CASE HEADER
      ═══════════════════════════════════════════════ */}
      <section className="border-b border-border pb-8 space-y-6">
        {/* Top bar: case ID + category + integrity badge */}
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-mono text-xs font-bold text-ink bg-ivory-dark border border-border px-2.5 py-1 rounded-sm tracking-widest uppercase">
            PRM-2026-0042
          </span>
          <span className="section-label">Fraud / Syndicated</span>
          <TierBadge tier={integrity?.intact ? 'VERIFIED BY CODE' : 'TAMPERED'} size="sm" />
        </div>

        {/* Big serif headline */}
        <div>
          <h1 className="font-serif text-5xl sm:text-7xl font-black text-ink tracking-tight leading-[0.9]">
            The Alpha Wealth Syndicate
          </h1>
          <p className="font-serif italic text-2xl text-ink-secondary mt-2">Reconstruction</p>
        </div>

        {/* 2-col editorial grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
          {/* Left: editorial prose */}
          <p className="text-sm text-ink-secondary font-sans leading-relaxed">
            Between <strong className="text-ink">12 March 2026</strong> and{' '}
            <strong className="text-ink">15 March 2026</strong>, victim{' '}
            <strong className="text-ink">Meera Joshi</strong> was solicited via an encrypted VIP
            WhatsApp advisory channel, inducing capital transfers totaling{' '}
            <strong className="text-ink">INR 2,50,000.00</strong> through an ostensible
            institutional investment pool. PRAMAAN has autonomously ingested 10 multi-format
            exhibits, reconstructed transaction layering across mule funnels, identified spatial cell
            tower transitions to Jaipur, and exposed altered bank ledger balances.
          </p>

          {/* Right: metadata card */}
          <div className="bg-surface-raised border border-border rounded-lg p-5 font-mono text-xs space-y-3">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <span className="section-label">Case Category</span>
              <span className="text-tomato font-mono font-bold text-xs">FRAUD / SYNDICATED</span>
            </div>
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <span className="section-label">Primary Target</span>
              <span className="font-semibold text-ink text-xs">Meera Joshi — ₹2.5L Loss</span>
            </div>
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <span className="section-label">Entities Resolved</span>
              <span className="font-semibold text-ink text-xs">{entities?.length || 59} Records</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="section-label">Ground Truth</span>
              <span className="font-bold text-lime-dark text-xs">10/10 RECOVERED</span>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          SECTION B — 4 STAT COLUMNS
      ═══════════════════════════════════════════════ */}
      <section className="border-y border-border py-6 grid grid-cols-2 md:grid-cols-4 divide-x divide-border">
        <div className="px-6 first:pl-0 space-y-1">
          <div className="section-label">01 / Events</div>
          <div className="font-serif text-4xl font-black text-ink leading-none">745</div>
          <div className="text-xs text-ink-tertiary font-sans">Synced across 10 files</div>
        </div>
        <div className="px-6 space-y-1">
          <div className="section-label">02 / Entities</div>
          <div className="font-serif text-4xl font-black text-ink leading-none">
            {entities?.length || 59}
          </div>
          <div className="text-xs text-ink-tertiary font-sans">Names, phones, VPAs</div>
        </div>
        <div className="px-6 space-y-1">
          <div className="section-label text-tomato">03 / Anomalies</div>
          <div className="font-serif text-4xl font-black text-tomato leading-none">
            {anomalies?.length || 25}
          </div>
          <div className="text-xs text-tomato/70 font-sans">{highAnomalies.length} High Severity</div>
        </div>
        <div className="px-6 space-y-1">
          <div className="section-label text-lime-dark">04 / Benchmark</div>
          <div className="font-serif text-4xl font-black text-lime-dark leading-none">94.7%</div>
          <div className="text-xs text-lime-dark/70 font-sans">F1 Indic Resolution</div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          SECTION C — ASYMMETRIC 12-COL GRID
      ═══════════════════════════════════════════════ */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-8">

        {/* LEFT: Primary Findings & Leads (7 cols) */}
        <div className="lg:col-span-7 space-y-5">
          {/* Section header + filter pills */}
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-tomato" />
              <h2 className="font-serif font-bold text-lg text-ink">Primary Findings &amp; Leads</h2>
            </div>
            <div className="flex items-center gap-1 font-mono text-[10px]">
              {(['ALL', 'HIGH', 'MEDIUM'] as const).map((lvl) => (
                <button
                  key={lvl}
                  type="button"
                  onClick={() => setActiveTabAnomaly(lvl)}
                  className={`px-2.5 py-1 rounded-sm transition-colors cursor-pointer uppercase tracking-wide ${
                    activeTabAnomaly === lvl
                      ? 'bg-ink text-surface-raised font-bold'
                      : 'bg-ivory-dark text-ink-secondary hover:text-ink border border-border'
                  }`}
                >
                  {lvl}
                </button>
              ))}
            </div>
          </div>

          {/* Anomaly cards */}
          <div className="space-y-3">
            {filteredAnomalies.slice(0, 6).map((anom, idx) => {
              const isHigh = anom.severity === 'HIGH';
              return (
                <article
                  key={anom.id || idx}
                  className={`rounded-md border p-4 transition-all space-y-2.5 ${
                    isHigh
                      ? 'anomaly-row-high border-l-4 border-l-tomato border-border'
                      : 'anomaly-row-medium border-l-4 border-l-ochre border-border'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-[11px] font-bold text-ink-secondary">
                        FINDING §{String(idx + 1).padStart(2, '0')}
                      </span>
                      <span
                        className={`text-[9px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded-sm border ${
                          isHigh
                            ? 'text-tomato bg-tomato-light border-tomato/40'
                            : 'text-ochre-dark bg-ochre-light border-ochre/40'
                        }`}
                      >
                        {anom.severity} RISK · {anom.kind.replace('ANOMALY_', '').replace('PATTERN_', '')}
                      </span>
                    </div>
                    {anom.exhibit_id && (
                      <ExhibitChip exhibitId={anom.exhibit_id} eventId={anom.event_ids?.[0]} />
                    )}
                  </div>

                  <p className="text-xs text-ink font-sans leading-relaxed">{anom.description}</p>

                  <div className="pt-2 border-t border-border/60 flex items-center justify-between text-[11px] font-mono">
                    <TierBadge tier="LEAD" size="sm" />
                    <button
                      type="button"
                      onClick={() => {
                        if (anom.event_ids?.[0]) {
                          openSourceViewer(anom.event_ids[0]);
                        } else {
                          navigate('/authenticity');
                        }
                      }}
                      className="text-cobalt hover:underline font-semibold flex items-center gap-1 cursor-pointer"
                    >
                      <span>Audit source</span>
                      <ArrowUpRight className="w-3 h-3" />
                    </button>
                  </div>
                </article>
              );
            })}
          </div>

          <div className="pt-1 flex justify-end">
            <Link
              to="/authenticity"
              className="text-xs font-mono font-bold text-cobalt hover:underline flex items-center gap-1.5"
            >
              <span>View all {anomalies?.length || 25} anomalies</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        {/* RIGHT: Timeline + Fund Layering + DNA bar (5 cols) */}
        <div className="lg:col-span-5 space-y-5">

          {/* Incident Timeline */}
          <div className="bg-surface-raised border border-border rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2 border-b border-border pb-3">
              <Clock className="w-4 h-4 text-cobalt" />
              <h3 className="font-serif font-bold text-sm text-ink">
                Incident Reconstruction Timeline
              </h3>
            </div>

            <div className="space-y-3">
              {/* Phase I */}
              <div className="p-3 bg-ivory rounded-md border border-border space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] font-bold text-cobalt">12 MAR · 14:22</span>
                  <span className="font-mono text-[9px] bg-ivory-dark border border-border px-1.5 py-0.5 rounded-sm text-ink-secondary">
                    PHASE I
                  </span>
                </div>
                <div className="font-sans font-semibold text-xs text-ink">First Contact Solicitation</div>
                <p className="text-[11px] text-ink-secondary leading-relaxed">
                  Added to "Alpha Wealth Club" via +91 98201 23456. Initial pitch for guaranteed 28% monthly returns.
                </p>
                <div className="pt-1 flex items-center justify-between">
                  <ExhibitChip exhibitId="EXH-01" />
                  <span className="font-mono text-[10px] text-ink-tertiary">WhatsApp Group</span>
                </div>
              </div>

              {/* Phase II — GT-04 anomaly node: tomato accent */}
              <div className="p-3 bg-tomato-light rounded-md border border-tomato/40 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] font-bold text-tomato">14 MAR 23:45 – 15 MAR 05:59</span>
                  <span className="font-mono text-[9px] bg-tomato text-white px-1.5 py-0.5 rounded-sm font-bold">
                    GT-04 ANOMALY
                  </span>
                </div>
                <div className="font-sans font-semibold text-xs text-tomato flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>6h 14m Silence Gap</span>
                </div>
                <p className="text-[11px] text-ink leading-relaxed">
                  Critical blackout period between victim debit and mule payout. Chat logs wiped during fund consolidation.
                </p>
                <div className="pt-1 flex items-center justify-between">
                  <ExhibitChip exhibitId="EXH-02" />
                  <span className="font-mono text-[10px] text-tomato font-bold">Unexplained Gap</span>
                </div>
              </div>

              {/* Phase III — GT-08 anomaly node: ochre accent */}
              <div className="p-3 bg-ochre-light rounded-md border border-ochre/40 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] font-bold text-ochre-dark">15 MAR · 11:30</span>
                  <span className="font-mono text-[9px] bg-ochre text-white px-1.5 py-0.5 rounded-sm font-bold">
                    GT-08 ANOMALY
                  </span>
                </div>
                <div className="font-sans font-semibold text-xs text-ink">Statement Balance Tampering</div>
                <p className="text-[11px] text-ink-secondary leading-relaxed">
                  PNB row 8 shows INR 2,20,000 balance instead of calculated INR 1,90,000 (+INR 30,000 fabrication).
                </p>
                <div className="pt-1 flex items-center justify-between">
                  <ExhibitChip exhibitId="EXH-03" />
                  <span className="font-mono text-[10px] text-ochre-dark font-semibold">Row 8 Discrepancy</span>
                </div>
              </div>

              {/* Phase IV */}
              <div className="p-3 bg-ivory rounded-md border border-border space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] font-bold text-cobalt">15 MAR · 16:45</span>
                  <span className="font-mono text-[9px] bg-ivory-dark border border-border px-1.5 py-0.5 rounded-sm text-ink-secondary">
                    PHASE IV
                  </span>
                </div>
                <div className="font-sans font-semibold text-xs text-ink">Jaipur Tower Extraction</div>
                <p className="text-[11px] text-ink-secondary leading-relaxed">
                  Device 1 drops Noida Sector 62 towers and registers on Jaipur Malviya Nagar cell tower for cash liquidation.
                </p>
                <div className="pt-1 flex items-center justify-between">
                  <ExhibitChip exhibitId="EXH-06" />
                  <span className="font-mono text-[10px] text-lime-dark font-semibold">CDR Cell Transition</span>
                </div>
              </div>
            </div>
          </div>

          {/* Fund Layering card */}
          <div className="bg-surface-raised border border-border rounded-lg p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Compass className="w-4 h-4 text-ochre-dark" />
                <h4 className="font-serif font-bold text-sm text-ink">Syndicate Fund Layering (GT-02)</h4>
              </div>
              <span className="font-mono text-[10px] text-tomato bg-tomato-light border border-tomato/40 px-2 py-0.5 rounded-sm font-bold uppercase">
                Mule Funnel
              </span>
            </div>

            <p className="text-[11px] text-ink-secondary font-sans leading-relaxed">
              Algorithmic graph correlation discovered immediate forwarding of pooled credits to intermediary mule accounts prior to ATM liquidation in Rajasthan.
            </p>

            {/* Visual flow */}
            <div className="bg-ivory rounded-md border border-border space-y-2 p-3 font-mono text-xs">
              {/* Victim */}
              <div className="flex items-center justify-between p-2.5 bg-surface-raised rounded-md border border-border">
                <div>
                  <div className="section-label">Origin Node (Victim)</div>
                  <div className="font-bold text-ink mt-0.5">Meera Joshi</div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-tomato">-₹2,50,000</div>
                  <div className="text-[9px] text-ink-tertiary">HDFC A/C 9821</div>
                </div>
              </div>

              {/* Arrow */}
              <div className="text-center text-[10px] text-ochre-dark font-bold py-0.5">
                ↓ UPI: vikram.invest@okhdfcbank
              </div>

              {/* Mule A */}
              <div className="flex items-center justify-between p-2.5 bg-surface-raised rounded-md border border-ochre/30">
                <div>
                  <div className="font-mono text-[10px] text-ochre-dark font-bold uppercase">Mule A (Funnel Hub)</div>
                  <div className="font-bold text-ink mt-0.5">Rohan Verma</div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-ochre-dark">360% Forwarded</div>
                  <div className="text-[9px] text-ink-tertiary">Within 24 Hours</div>
                </div>
              </div>

              {/* Arrow */}
              <div className="text-center text-[10px] text-ochre-dark font-bold py-0.5">
                ↓ RTGS / Cash Extraction
              </div>

              {/* Destination */}
              <div className="flex items-center justify-between p-2.5 bg-surface-raised rounded-md border border-border">
                <div>
                  <div className="section-label">Destination Node</div>
                  <div className="font-bold text-ink mt-0.5">Mule B / Jaipur ATM</div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-lime-dark">ATM Cash-Out</div>
                  <div className="text-[9px] text-ink-tertiary">Tower 404-45-8921</div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-ink-tertiary text-[11px] font-mono">Identified via NetworkX cycles</span>
              <Link
                to="/graph"
                className="text-cobalt hover:underline font-bold font-mono flex items-center gap-1 text-[11px]"
              >
                <span>Inspect in Knowledge Graph</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          </div>

          {/* Evidence DNA bar */}
          <div className="bg-surface-raised border border-border rounded-lg p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <h4 className="font-serif font-bold text-sm text-ink flex items-center gap-2">
                <FolderArchive className="w-4 h-4 text-cobalt" />
                <span>Evidence Artifact DNA ({exhibitsCount} Exhibits)</span>
              </h4>
              <span className="font-mono text-[10px] text-ink-tertiary uppercase tracking-wide">SHA-256</span>
            </div>

            {/* Segmented bar */}
            <div className="space-y-1.5">
              <div className="h-3.5 w-full flex rounded-sm overflow-hidden border border-border">
                {Object.entries(sourceBreakdown).map(([stype, meta]) => {
                  if (meta.count === 0) return null;
                  const pct = ((meta.count / (exhibitsCount || 1)) * 100).toFixed(1);
                  return (
                    <div
                      key={stype}
                      style={{ width: `${pct}%`, backgroundColor: meta.color }}
                      title={`${meta.label}: ${meta.count} files (${pct}%)`}
                      className="h-full cursor-pointer hover:opacity-80 transition-opacity"
                    />
                  );
                })}
              </div>
              <div className="flex items-center justify-between text-[10px] font-mono text-ink-tertiary pt-1">
                <span>0 MB Network Transmission</span>
                <span>100% Ingested Read-Only</span>
              </div>
            </div>

            {/* Legend */}
            <div className="space-y-1.5 font-mono text-xs">
              {Object.entries(sourceBreakdown).map(([stype, meta]) => {
                if (meta.count === 0) return null;
                return (
                  <div
                    key={stype}
                    className="ledger-row flex items-center justify-between py-1.5"
                  >
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-xs shrink-0" style={{ backgroundColor: meta.color }} />
                      <span className="text-ink font-sans text-xs">{meta.label}</span>
                    </div>
                    <span className="bg-ivory-dark px-2 py-0.5 rounded-sm border border-border text-ink font-bold text-[11px]">
                      {meta.count} {meta.count > 1 ? 'files' : 'file'}
                    </span>
                  </div>
                );
              })}
            </div>

            <div className="pt-2 border-t border-border flex justify-between items-center text-xs font-mono">
              <span className="text-ink-tertiary text-[11px]">All exhibits signed &amp; timestamped</span>
              <Link to="/evidence" className="font-bold text-cobalt hover:underline flex items-center gap-1">
                <span>Open Evidence Vault</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          SECTION D — AI INVESTIGATION AGENTS
      ═══════════════════════════════════════════════ */}
      <section className="bg-lavender-light border border-lavender/30 rounded-xl p-6 space-y-5">
        <div className="flex items-center gap-2.5">
          <Sparkles className="w-5 h-5 text-lavender-dark" />
          <h2 className="font-serif font-bold text-xl text-ink">AI Investigation Agents</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

          {/* Agent 1: Entity Extractor */}
          <div className="bg-surface-raised rounded-lg border border-border p-4 space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-md bg-cobalt/10 flex items-center justify-center shrink-0">
                <Users className="w-4 h-4 text-cobalt" />
              </div>
              <div>
                <div className="font-sans font-semibold text-sm text-ink">Entity Resolution Engine</div>
                <div className="text-ink-secondary text-xs font-sans">Regex + Indic NER pipeline</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold uppercase tracking-wide text-cobalt bg-cobalt/10 border border-cobalt/20 px-2 py-0.5 rounded-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-cobalt" />
                Active
              </span>
              <span className="text-xs text-ink-secondary font-mono">{entities?.length || 59} entities resolved</span>
            </div>
            <Link
              to="/entities"
              className="inline-flex items-center gap-1 text-cobalt font-mono text-xs font-bold hover:underline"
            >
              Inspect Entities →
            </Link>
          </div>

          {/* Agent 2: Anomaly Detector */}
          <div className="bg-surface-raised rounded-lg border border-border p-4 space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-md bg-tomato/10 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-4 h-4 text-tomato" />
              </div>
              <div>
                <div className="font-sans font-semibold text-sm text-ink">Anomaly Detection Agent</div>
                <div className="text-ink-secondary text-xs font-sans">Timeline, funnel &amp; image forensics</div>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold uppercase tracking-wide text-tomato bg-tomato-light border border-tomato/30 px-2 py-0.5 rounded-sm">
                {anomalies?.length || 25} flagged
              </span>
              <span className="text-xs text-ink-secondary font-mono">{highAnomalies.length} HIGH</span>
            </div>
            <Link
              to="/authenticity"
              className="inline-flex items-center gap-1 text-tomato font-mono text-xs font-bold hover:underline"
            >
              View Anomalies →
            </Link>
          </div>

          {/* Agent 3: AI Claim Generator */}
          <div className="bg-surface-raised rounded-lg border border-border p-4 space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-md bg-lavender/20 flex items-center justify-center shrink-0">
                <Sparkles className="w-4 h-4 text-lavender-dark" />
              </div>
              <div>
                <div className="font-sans font-semibold text-sm text-ink">Forensic Claim Drafter</div>
                <div className="text-ink-secondary text-xs font-sans">Ollama LLM or deterministic fallback</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold uppercase tracking-wide text-lavender-dark bg-lavender-light border border-lavender/30 px-2 py-0.5 rounded-sm">
                Pending Review
              </span>
            </div>
            <Link
              to="/review"
              className="inline-flex items-center gap-1 text-lavender-dark font-mono text-xs font-bold hover:underline"
            >
              Review Queue →
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};
