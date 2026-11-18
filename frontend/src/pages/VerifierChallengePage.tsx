import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Scale,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  ShieldAlert,
} from 'lucide-react';
import { TierBadge } from '../components/ui/TierBadge';
import { ExhibitChip } from '../components/evidence/ExhibitChip';

export const VerifierChallengePage: React.FC = () => {
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<'verifier' | 'challenge'>('verifier');

  // Queries
  const { data: claims, isLoading: claimsLoading } = useQuery({
    queryKey: ['claimsList'],
    queryFn: async () => {
      const res = await fetch('/api/claims');
      return res.json();
    },
  });

  const { data: verifierReport, mutate: runVerifier, isPending: verifierPending } = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/verify/claims', { method: 'POST' });
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['claimsList'] });
    },
  });

  const { mutate: draftClaims, isPending: draftPending } = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/ai/draft', { method: 'POST' });
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['claimsList'] });
    },
  });

  const { data: challengeData, mutate: runChallenge, isPending: challengePending } = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/challenge/run', { method: 'POST' });
      return res.json();
    },
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="border-b border-border pb-5 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-2xs font-mono uppercase tracking-widest text-ink-secondary">
            <span>Dossier Section 08</span>
            <span>·</span>
            <span>Forensic Verification & Challenge Engine</span>
          </div>
          <h1 className="font-serif font-bold text-3xl text-ink mt-1.5 tracking-tight">
            Claim Verifier & Adversarial Cross-Examination
          </h1>
          <p className="text-xs text-ink-secondary mt-2 max-w-3xl leading-relaxed">
            Non-negotiable core standard: <b className="text-ink">No source, no claim.</b> The AI proposes structured interpretive leads; a deterministic Python verifier strips any sentence lacking an exact database exhibit citation (Rules V1–V5), and an adversarial challenger pre-empts defence courtroom motions.
          </p>
        </div>

        <div className="font-mono text-xs text-ink-secondary bg-surface-raised px-3 py-1.5 rounded-[3px] border border-border self-start md:self-auto">
          <span>Active Claims: </span>
          <span className="font-bold text-ink">{claims?.length || 0}</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-border text-xs font-mono">
        <button
          type="button"
          onClick={() => setActiveTab('verifier')}
          className={`flex items-center gap-2 px-4 py-2.5 border-b-2 font-bold transition-colors cursor-pointer ${
            activeTab === 'verifier'
              ? 'border-cobalt text-cobalt bg-surface-raised'
              : 'border-transparent text-ink-secondary hover:text-ink'
          }`}
        >
          <Scale className="w-4 h-4 text-cobalt" />
          <span>Deterministic Claim Verifier (Rules V1–V5)</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('challenge')}
          className={`flex items-center gap-2 px-4 py-2.5 border-b-2 font-bold transition-colors cursor-pointer ${
            activeTab === 'challenge'
              ? 'border-tomato text-tomato bg-surface-raised'
              : 'border-transparent text-ink-secondary hover:text-ink'
          }`}
        >
          <ShieldAlert className="w-4 h-4 text-tomato" />
          <span>Adversarial Challenger (Cross-Examination Mode)</span>
        </button>
      </div>

      {/* TAB 1: CLAIM VERIFIER */}
      {activeTab === 'verifier' && (
        <div className="space-y-6">
          {/* Action Toolbar */}
          <div className="bg-surface-raised p-4 rounded-[4px] border border-border flex flex-wrap items-center justify-between gap-4 shadow-xs">
            <div className="space-y-1">
              <span className="text-xs font-bold text-ink uppercase tracking-wider font-mono">
                Deterministic Three-Tier Pipeline
              </span>
              <p className="text-2xs text-ink-secondary font-mono">
                1. AI Drafts Claims → 2. Verifier Strips Uncited Claims (Rules V1–V5) → 3. Human Adjudicates
              </p>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                disabled={draftPending}
                onClick={() => draftClaims()}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-surface border border-border hover:bg-ivory-dark text-ink text-xs font-mono rounded-[3px] cursor-pointer transition-colors shadow-xs"
              >
                <Cpu className={`w-3.5 h-3.5 ${draftPending ? 'animate-spin' : ''}`} />
                <span>{draftPending ? 'Drafting...' : '1. Draft Claims (Local AI)'}</span>
              </button>

              <button
                type="button"
                disabled={verifierPending}
                onClick={() => runVerifier()}
                className="flex items-center gap-1.5 px-3.5 py-1.5 bg-cobalt hover:bg-cobalt-dark text-white text-xs font-mono font-medium rounded-[3px] cursor-pointer transition-colors shadow-xs"
              >
                <ShieldCheck className={`w-3.5 h-3.5 ${verifierPending ? 'animate-spin' : ''}`} />
                <span>{verifierPending ? 'Verifying...' : '2. Run Deterministic Verifier'}</span>
              </button>
            </div>
          </div>

          {/* Verification Report Metric Bar */}
          {verifierReport && (
            <div className="bg-surface-raised border border-border rounded-[4px] p-5 space-y-4 shadow-xs">
              <div className="flex items-center justify-between text-xs font-mono border-b border-border pb-2.5">
                <span className="font-bold text-ink uppercase tracking-wider">
                  Verification Execution Statistics
                </span>
                <span className="text-ink-secondary font-mono text-2xs">RULES V1–V5 APPLIED</span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
                <div className="bg-ivory p-3 rounded-[3px] border border-border">
                  <span className="text-ink-secondary text-[10px] uppercase">Proposed Claims:</span>
                  <div className="text-2xl font-bold text-ink mt-1">{verifierReport.proposed_count}</div>
                </div>
                <div className="bg-lime-light p-3 rounded-[3px] border border-lime-dark/30">
                  <span className="text-lime-dark text-[10px] uppercase font-bold">Verified by Code:</span>
                  <div className="text-2xl font-bold text-lime-dark mt-1">{verifierReport.verified_count}</div>
                </div>
                <div className="bg-tomato-light p-3 rounded-[3px] border border-tomato/30">
                  <span className="text-tomato text-[10px] uppercase font-bold">Removed (Uncited V4):</span>
                  <div className="text-2xl font-bold text-tomato mt-1">{verifierReport.removed_count}</div>
                </div>
                <div className="bg-ochre-light p-3 rounded-[3px] border border-ochre/30">
                  <span className="text-ochre-dark text-[10px] uppercase font-bold">Rewritten (Guilt V5):</span>
                  <div className="text-2xl font-bold text-ochre-dark mt-1">{verifierReport.modified_count}</div>
                </div>
              </div>

              {/* Removed Claims Callout */}
              {verifierReport.removed_claims?.length > 0 && (
                <div className="pt-2 border-t border-border space-y-2">
                  <span className="text-2xs font-mono uppercase font-bold text-tomato block tracking-wider">
                    Enforcing Rule V4: Claims Removed for Incomplete Citation
                  </span>
                  {verifierReport.removed_claims.map((rm: any, idx: number) => (
                    <div
                      key={idx}
                      className="bg-tomato-light border border-tomato/30 rounded-[3px] p-3 text-xs space-y-1 font-mono"
                    >
                      <div className="text-tomato font-bold">✗ {rm.reason}</div>
                      <div className="text-ink text-xs italic font-sans">"{rm.text}"</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Claims Store Table */}
          <div className="bg-surface-raised border border-border rounded-[4px] overflow-hidden shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
            <div className="px-5 py-3 border-b border-border bg-surface text-xs font-mono font-bold text-ink flex items-center justify-between">
              <span>REGISTERED FORENSIC CLAIMS ({claims?.length || 0})</span>
              <span className="text-ink-secondary font-normal text-2xs">IMMUTABLE REPOSITORY</span>
            </div>

            <div className="divide-y divide-border">
              {claimsLoading ? (
                <div className="p-10 text-center text-xs font-mono text-ink-secondary">Loading claims from SQLite...</div>
              ) : claims?.length === 0 ? (
                <div className="p-10 text-center text-xs font-mono text-ink-secondary">
                  No claims drafted yet. Click '1. Draft Claims' above to generate structured leads.
                </div>
              ) : (
                claims?.map((c: any) => {
                  const isVerified = c.status === 'VERIFIED' || c.status === 'APPROVED';
                  const isRemoved = c.status === 'REMOVED';
                  return (
                    <div
                      key={c.id}
                      className={`p-4 space-y-2.5 transition-colors ${
                        isRemoved ? 'bg-tomato-light/40 opacity-75' : 'hover:bg-ivory'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs font-mono">
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-2xs font-bold px-1.5 py-0.5 rounded border uppercase ${
                              isVerified
                                ? 'bg-lime-light text-lime-dark border-lime-dark/30'
                                : isRemoved
                                ? 'bg-tomato-light text-tomato border-tomato/30'
                                : 'bg-ochre-light text-ochre-dark border-ochre/30'
                            }`}
                          >
                            {c.status}
                          </span>
                          <span className="font-semibold text-ink uppercase text-[11px]">{c.kind}</span>
                        </div>

                        <div className="flex items-center gap-1.5">
                          {c.source_refs?.map((refId: string) => (
                            <ExhibitChip key={refId} exhibitId={refId.slice(0, 8)} />
                          ))}
                        </div>
                      </div>

                      <p className="text-xs text-ink font-sans leading-relaxed font-medium">{c.text}</p>

                      {c.verifier_notes && (
                        <div className="text-2xs font-mono text-ink-secondary pt-1 border-t border-border/50">
                          Verifier Note: {c.verifier_notes}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: CHALLENGER CROSS-EXAMINATION */}
      {activeTab === 'challenge' && (
        <div className="space-y-6">
          <div className="bg-surface-raised p-4 rounded-[4px] border border-border flex flex-wrap items-center justify-between gap-4 shadow-xs">
            <div className="space-y-1">
              <span className="text-xs font-bold text-ink uppercase tracking-wider font-mono">
                Adversarial Defence Vulnerability Scan
              </span>
              <p className="text-2xs text-ink-secondary">
                Pre-empts courtroom objections against chat gaps, inverted timestamps, assumed timezones, and unauthenticated device exports.
              </p>
            </div>

            <button
              type="button"
              disabled={challengePending}
              onClick={() => runChallenge()}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-tomato hover:bg-tomato-dark text-white text-xs font-mono font-medium rounded-[3px] cursor-pointer transition-colors shadow-xs"
            >
              <AlertTriangle className={`w-3.5 h-3.5 ${challengePending ? 'animate-spin' : ''}`} />
              <span>{challengePending ? 'Scanning Arguments...' : 'Run Cross-Examination Scan'}</span>
            </button>
          </div>

          {/* Objections List */}
          {challengeData && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs font-mono text-ink-secondary">
                <span className="font-bold text-ink uppercase">
                  ANTICIPATED DEFENCE OBJECTIONS ({challengeData.total_objections})
                </span>
                <span className="text-tomato font-bold">
                  {challengeData.high_severity_count} HIGH-RISK VULNERABILITIES IDENTIFIED
                </span>
              </div>

              <div className="space-y-3.5">
                {challengeData.objections?.map((obj: any, idx: number) => (
                  <div
                    key={idx}
                    className="bg-surface-raised border border-border rounded-[4px] p-5 space-y-3 shadow-xs hover:border-border-strong transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <span
                          className={`text-2xs font-mono font-bold px-1.5 py-0.5 rounded border uppercase ${
                            obj.severity === 'HIGH'
                              ? 'bg-tomato-light text-tomato border-tomato/30'
                              : 'bg-ochre-light text-ochre-dark border-ochre/30'
                          }`}
                        >
                          {obj.severity} RISK
                        </span>
                        <h4 className="font-serif font-bold text-base text-ink">{obj.title}</h4>
                      </div>
                      <span className="text-2xs font-mono text-ink-secondary bg-surface px-1.5 py-0.5 rounded border border-border uppercase">
                        {obj.type}
                      </span>
                    </div>

                    <div className="bg-ivory p-3.5 rounded-[3px] border border-border text-xs space-y-1">
                      <span className="text-2xs font-mono uppercase text-ink-secondary font-bold block">
                        Cross-Examination Argument (Opposing Counsel):
                      </span>
                      <p className="text-ink leading-relaxed font-sans">{obj.argument}</p>
                    </div>

                    <div className="bg-lime-light/80 p-3.5 rounded-[3px] border border-lime-dark/30 text-xs space-y-1">
                      <span className="text-2xs font-mono uppercase text-lime-dark font-bold block flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Prosecution Remedy / Forensic Countermeasure:
                      </span>
                      <p className="text-ink leading-relaxed font-sans font-medium">{obj.suggested_fix}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
