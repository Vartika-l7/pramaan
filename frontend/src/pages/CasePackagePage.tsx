import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Package,
  FileText,
  Terminal,
  ExternalLink,
  Lock,
  HardDriveDownload,
} from 'lucide-react';
import { fetchIntegrityStatus } from '../lib/api';

export const CasePackagePage: React.FC = () => {
  const [verifierOutput, setVerifierOutput] = useState<string | null>(null);

  const { data: integrity } = useQuery({ queryKey: ['integrityStatus'], queryFn: fetchIntegrityStatus });

  const buildMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/report/build', { method: 'POST' });
      return res.json();
    },
  });

  const runVerifierDemo = () => {
    setVerifierOutput(`$ python verifier.py --package .
======================================================================
PRAMAAN STANDALONE FORENSIC CASE PACKAGE VERIFIER
======================================================================
Case Reference: PRM-2026-0042
Exhibits in Manifest: 10
Expected Merkle Root: ${integrity?.merkle_root || '7f3a8b29...c9e1'}
Signing Key (Ed25519): 9b4a1f... verified

--- [CHECK 1/4] Re-hashing Evidence Files ---
  [PASS] EXH-01 (whatsapp_group_alpha_wealth.txt): SHA-256 MATCH
  [PASS] EXH-02 (whatsapp_chat_meera_vikram.txt): SHA-256 MATCH
  [PASS] EXH-03 (bank_statement_meera.pdf): SHA-256 MATCH
  [PASS] EXH-04 (bank_statement_mule_A.pdf): SHA-256 MATCH
  [PASS] EXH-05 (bank_statement_mule_B.csv): SHA-256 MATCH
  [PASS] EXH-06 (call_log_device1.csv): SHA-256 MATCH
  [PASS] EXH-07 (call_log_device2.csv): SHA-256 MATCH
  [PASS] EXH-08 (screenshot_payment_genuine.png): SHA-256 MATCH
  [PASS] EXH-09 (screenshot_withdrawal_edited.jpg): SHA-256 MATCH
  [PASS] EXH-10 (screenshot_reused_a.png): SHA-256 MATCH

--- [CHECK 2/4] Merkle Root Audit ---
  [PASS] Recomputed Merkle root matches manifest: ${integrity?.merkle_root || '7f3a8b29...c9e1'}

--- [CHECK 3/4] Custody Ledger Hash Chain ---
  [PASS] Append-only hash chain valid across all custody records from genesis.

--- [CHECK 4/4] Ed25519 Digital Signature ---
  [PASS] Ed25519 signature in manifest.sig validated against public key.

======================================================================
FINAL VERDICT: ALL CRYPTOGRAPHIC INTEGRITY AUDITS PASSED
Section 63 BSA compliance valid. Case package is intact and tamper-evident.
======================================================================`);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="border-b border-border pb-5 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-2xs font-mono uppercase tracking-widest text-ink-secondary">
            <span>Dossier Section 09</span>
            <span>·</span>
            <span>Court Certification & Package Export</span>
          </div>
          <h1 className="font-serif font-bold text-3xl text-ink mt-1.5 tracking-tight">
            Case Package & BSA Section 63 Certificate
          </h1>
          <p className="text-xs text-ink-secondary mt-2 max-w-3xl leading-relaxed">
            Assembles the signed court report PDF with Section 63 Bharatiya Sakshya Adhiniyam certificate, sorted exhibit manifests, Ed25519 digital signature, and an offline standalone verifier into a portable archive.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start md:self-auto font-mono text-xs">
          <span className="bg-lime-light text-lime-dark border border-lime-dark/30 px-3 py-1.5 rounded-[3px] font-semibold flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5" />
            <span>Ed25519 Sealed</span>
          </span>
        </div>
      </div>

      {/* Package Generation Action Card */}
      <div className="bg-surface-raised p-6 rounded-[4px] border border-border flex flex-col md:flex-row items-start md:items-center justify-between gap-5 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <Package className="w-4 h-4 text-cobalt" />
            <h3 className="font-serif font-bold text-base text-ink">
              Generate & Export Sealed Case Package (.ZIP)
            </h3>
          </div>
          <p className="text-xs text-ink-secondary max-w-2xl leading-relaxed">
            Package bundles <code className="font-mono text-ink bg-ivory px-1 py-0.5 rounded border border-border">report.pdf</code>, <code className="font-mono text-ink bg-ivory px-1 py-0.5 rounded border border-border">manifest.json</code>, <code className="font-mono text-ink bg-ivory px-1 py-0.5 rounded border border-border">manifest.sig</code>, and the standalone zero-dependency <code className="font-mono text-ink bg-ivory px-1 py-0.5 rounded border border-border">verifier.py</code>.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            disabled={buildMutation.isPending}
            onClick={() => buildMutation.mutate()}
            className="flex items-center gap-2 px-4 py-2 bg-cobalt hover:bg-cobalt-dark text-white text-xs font-mono font-medium rounded-[3px] cursor-pointer transition-colors shadow-xs"
          >
            <Package className={`w-3.5 h-3.5 ${buildMutation.isPending ? 'animate-spin' : ''}`} />
            <span>{buildMutation.isPending ? 'Assembling Archive...' : 'Build Court Package'}</span>
          </button>

          <a
            href="/api/report/download"
            download
            className="flex items-center gap-2 px-4 py-2 bg-lime-dark hover:bg-lime-dark/90 text-white text-xs font-mono font-semibold rounded-[3px] cursor-pointer transition-colors shadow-xs"
          >
            <HardDriveDownload className="w-3.5 h-3.5" />
            <span>Download ZIP Package</span>
          </a>
        </div>
      </div>

      {/* Package Contents Breakdown Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Package Inventory */}
        <div className="bg-surface-raised border border-border rounded-[4px] p-5 space-y-4 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <div className="flex items-center justify-between border-b border-border pb-2.5">
            <h4 className="font-serif font-bold text-base text-ink flex items-center gap-2">
              <FileText className="w-4 h-4 text-cobalt" />
              <span>Official Case Artifacts Manifest</span>
            </h4>
            <span className="font-mono text-2xs text-ink-secondary uppercase">Tamper-Evident Format</span>
          </div>

          <div className="space-y-3 text-xs font-mono">
            {/* report.pdf */}
            <div className="p-3 bg-surface rounded-[3px] border border-border flex items-start justify-between gap-3 shadow-xs">
              <div className="space-y-1">
                <span className="font-bold text-ink">01 · report.pdf</span>
                <div className="text-[11px] text-ink-secondary font-sans leading-relaxed">
                  Section 63 BSA Certificate, factual findings, parsed transactions, and exhibit references.
                </div>
              </div>
              <a
                href="/api/report/pdf"
                target="_blank"
                rel="noreferrer"
                className="text-xs font-sans font-bold text-cobalt hover:underline flex items-center gap-1 shrink-0 bg-surface-raised px-2 py-1 rounded border border-border"
              >
                <span>View PDF</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            {/* manifest.json + sig */}
            <div className="p-3 bg-surface rounded-[3px] border border-border space-y-1 shadow-xs">
              <span className="font-bold text-ink">02 · manifest.json & manifest.sig</span>
              <div className="text-[11px] text-ink-secondary font-sans leading-relaxed">
                Lexicographically sorted SHA-256 evidence digests signed with the investigator's Ed25519 private key.
              </div>
            </div>

            {/* verifier.py */}
            <div className="p-3 bg-surface rounded-[3px] border border-border space-y-1 shadow-xs">
              <span className="font-bold text-ink">03 · verifier.py</span>
              <div className="text-[11px] text-ink-secondary font-sans leading-relaxed">
                Zero-dependency, fully offline verification script executable on any standard Python 3.10+ interpreter.
              </div>
            </div>

            {/* defence_weakness_report.html */}
            <div className="p-3 bg-surface rounded-[3px] border border-border space-y-1 shadow-xs">
              <span className="font-bold text-ink">04 · defence_weakness_report.html</span>
              <div className="text-[11px] text-ink-secondary font-sans leading-relaxed">
                Confidential prosecution advisory on chat silence gaps, timestamp drift, and anticipated defence challenges.
              </div>
            </div>
          </div>
        </div>

        {/* Right: Standalone Verifier Terminal Simulator */}
        <div className="bg-surface-raised border border-border rounded-[4px] p-5 space-y-4 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <h4 className="font-serif font-bold text-base text-ink flex items-center gap-2">
                <Terminal className="w-4 h-4 text-ink" />
                <span>Standalone Verifier Simulator</span>
              </h4>
              <button
                type="button"
                onClick={runVerifierDemo}
                className="px-2.5 py-1 bg-surface border border-border hover:bg-ivory-dark text-xs font-mono font-medium rounded-[3px] cursor-pointer transition-colors shadow-xs"
              >
                Execute Verifier Now
              </button>
            </div>
            <p className="text-2xs text-ink-secondary mt-2 font-mono">
              Simulates terminal output from executing: <code className="text-ink font-bold">$ python verifier.py --package .</code>
            </p>
          </div>

          <div className="bg-[#242D3A] text-[#F4F0E7] font-mono text-[11px] p-4 rounded-[4px] overflow-x-auto min-h-[260px] max-h-[320px] leading-relaxed border border-border shadow-inner">
            {verifierOutput ? (
              <pre className="whitespace-pre-wrap">{verifierOutput}</pre>
            ) : (
              <div className="text-ink-secondary py-16 text-center space-y-2">
                <Terminal className="w-6 h-6 mx-auto opacity-50" />
                <div>Click 'Execute Verifier Now' to run offline cryptographic audit.</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
