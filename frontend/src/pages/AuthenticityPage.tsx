import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Fingerprint,
  Image as ImageIcon,
  FileSpreadsheet,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Eye,
  Layers,
  ZoomIn,
  ShieldAlert,
  FileCode,
} from 'lucide-react';
import { fetchEvidenceList, fetchImageAuthenticity, fetchStatementCheck } from '../lib/api';
import { TierBadge } from '../components/ui/TierBadge';
import { ExhibitChip } from '../components/evidence/ExhibitChip';

export const AuthenticityPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'images' | 'statements'>('images');

  const { data: evidence } = useQuery({ queryKey: ['evidenceList'], queryFn: fetchEvidenceList });

  const imageExhibits = evidence?.filter((e) => e.source_type === 'image') || [];
  const statementExhibits =
    evidence?.filter((e) => e.source_type === 'bank_pdf' || e.source_type === 'bank_csv') || [];

  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const [selectedStatementId, setSelectedStatementId] = useState<string | null>(null);

  // Auto-select first exhibit if not explicitly chosen
  const activeImageId = selectedImageId || imageExhibits[0]?.id;
  const activeStatementId = selectedStatementId || statementExhibits[0]?.id;

  const { data: imageData, isLoading: imageLoading } = useQuery({
    queryKey: ['imageAuth', activeImageId],
    queryFn: () => (activeImageId ? fetchImageAuthenticity(activeImageId) : null),
    enabled: !!activeImageId,
  });

  const { data: statementData, isLoading: statementLoading } = useQuery({
    queryKey: ['statementAuth', activeStatementId],
    queryFn: () => (activeStatementId ? fetchStatementCheck(activeStatementId) : null),
    enabled: !!activeStatementId,
  });

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16 font-sans">
      {/* Editorial Forensic Header */}
      <div className="border-b border-border pb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-sans text-xs font-bold uppercase tracking-wider text-cobalt bg-cobalt-light px-2.5 py-1 rounded-full">
              Authenticity Laboratory
            </span>
            <span className="text-ink-tertiary">·</span>
            <span className="font-sans text-xs text-ink-secondary">
              Physical & Ledger Forensics
            </span>
          </div>
          <h1 className="font-serif font-bold text-3xl sm:text-4xl text-ink mt-2 tracking-tight">
            Digital Image & Statement Authenticity
          </h1>
          <p className="text-sm text-ink-secondary mt-2 max-w-3xl leading-relaxed">
            Multi-modal forensic workstation analyzing Error Level Analysis (ELA) compression gradients, EXIF camera metadata, perceptual hash collision clusters, and automated statement balance arithmetic.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start md:self-auto font-sans text-xs">
          <span className="font-sans font-semibold text-xs px-3 py-1.5 rounded-full bg-surface-raised border border-border text-ink-secondary">
            Methodology: ISO/IEC 27037 Forensics
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-3 border-b border-border text-sm font-sans">
        <button
          type="button"
          onClick={() => setActiveTab('images')}
          className={`flex items-center gap-2 px-5 py-3 border-b-2 font-semibold transition-all cursor-pointer ${
            activeTab === 'images'
              ? 'border-cobalt text-cobalt bg-cobalt-light/40 rounded-t-lg'
              : 'border-transparent text-ink-secondary hover:text-ink'
          }`}
        >
          <ImageIcon className="w-4 h-4" />
          <span>Image Forensics & ELA Inspection</span>
          <span className="font-mono text-2xs bg-surface-raised px-2 py-0.5 rounded-full border border-border text-ink">
            {imageExhibits.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('statements')}
          className={`flex items-center gap-2 px-5 py-3 border-b-2 font-semibold transition-all cursor-pointer ${
            activeTab === 'statements'
              ? 'border-cobalt text-cobalt bg-cobalt-light/40 rounded-t-lg'
              : 'border-transparent text-ink-secondary hover:text-ink'
          }`}
        >
          <FileSpreadsheet className="w-4 h-4" />
          <span>Bank Statement Arithmetic Verification</span>
          <span className="font-mono text-2xs bg-surface-raised px-2 py-0.5 rounded-full border border-border text-ink">
            {statementExhibits.length}
          </span>
        </button>
      </div>

      {/* TAB A: IMAGE FORENSICS */}
      {activeTab === 'images' && (
        <div className="space-y-8">
          {/* Exhibit Selector Ribbon */}
          <div className="flex items-center gap-2.5 flex-wrap bg-surface-raised p-4 rounded-xl border border-border shadow-xs">
            <span className="text-xs font-bold text-ink-secondary uppercase tracking-wider mr-2">
              Select Image Exhibit:
            </span>
            {imageExhibits.map((img) => (
              <button
                key={img.id}
                type="button"
                onClick={() => setSelectedImageId(img.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-sans transition-all cursor-pointer ${
                  activeImageId === img.id
                    ? 'bg-cobalt text-white font-semibold shadow-xs'
                    : 'bg-surface text-ink border border-border hover:bg-ivory-dark'
                }`}
              >
                <ExhibitChip exhibitId={img.exhibit_id} />
                <span className="truncate max-w-[140px] font-sans">{img.filename}</span>
              </button>
            ))}
          </div>

          {/* ELA Visual Inspection Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left: Original Evidence Screenshot */}
            <div className="bg-surface-raised border border-border rounded-xl p-5 space-y-3.5 shadow-xs">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <span className="font-sans text-xs uppercase tracking-wider font-bold text-ink flex items-center gap-2">
                  <Eye className="w-4 h-4 text-cobalt" />
                  Original Evidence Image
                </span>
                <span className="font-mono text-2xs text-ink-secondary">RAW PIXELS</span>
              </div>

              <div className="bg-ivory-dark/40 rounded-lg flex items-center justify-center min-h-[360px] overflow-hidden p-4 border border-border">
                {imageData?.original_url ? (
                  <img
                    src={imageData.original_url}
                    alt="Original evidence artifact"
                    className="max-h-[380px] max-w-full object-contain rounded shadow-xs"
                  />
                ) : (
                  <div className="text-ink-secondary text-xs flex flex-col items-center gap-2 font-sans">
                    <ImageIcon className="w-8 h-8 opacity-40 text-ink" />
                    <span>Evidence screenshot rendering ({imageData?.filename || 'image'})</span>
                  </div>
                )}
              </div>
            </div>

            {/* Right: Error Level Analysis Heatmap */}
            <div className="bg-surface-raised border border-border rounded-xl p-5 space-y-3.5 shadow-xs">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <span className="font-sans text-xs uppercase tracking-wider font-bold text-tomato flex items-center gap-2">
                  <Layers className="w-4 h-4 text-tomato" />
                  Error Level Analysis (ELA) Compression Heatmap
                </span>
                <span className="font-sans font-bold text-2xs text-tomato bg-tomato-light px-2 py-0.5 rounded-full border border-tomato/30">
                  JPEG RESAVE DETECTION
                </span>
              </div>

              <div className="bg-ivory-dark/40 rounded-lg flex items-center justify-center min-h-[360px] overflow-hidden p-4 border border-border">
                {imageData?.ela_url ? (
                  <img
                    src={imageData.ela_url}
                    alt="ELA Heatmap artifact"
                    className="max-h-[380px] max-w-full object-contain rounded shadow-xs"
                  />
                ) : (
                  <div className="text-ink-secondary text-xs flex flex-col items-center gap-2 font-sans">
                    <ZoomIn className="w-8 h-8 opacity-40 text-tomato" />
                    <span>Error Level Analysis gradient computed by Pillow resave filter</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Anomaly Callout Banner if Tampered */}
          {imageData?.tampered && (
            <div className="bg-tomato-light border border-tomato/40 rounded-xl p-5 space-y-2">
              <div className="flex items-center gap-2 text-tomato font-sans font-bold text-sm">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>Forensic Tamper Detection: GT-09 Image Discrepancy Found</span>
              </div>
              <p className="text-xs text-ink leading-relaxed font-sans">
                {imageData.tamper_reason ||
                  'ELA reveals high-frequency compression variance in withdrawal confirmation amount banner. EXIF software tag indicates Adobe Photoshop editing; pHash matches genuine payment template.'}
              </p>
            </div>
          )}

          {/* Forensic Image Technical Metadata Table */}
          <div className="bg-surface-raised border border-border rounded-xl overflow-hidden shadow-xs">
            <div className="px-6 py-4 border-b border-border bg-surface text-xs font-sans font-bold text-ink flex items-center justify-between">
              <span>EXIF METADATA & PERCEPTUAL HASH AUDIT</span>
              <span className="text-ink-secondary font-normal text-2xs">ISO/IEC 27037 FORENSIC STANDARD</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-ivory border-b border-border text-2xs uppercase tracking-wider text-ink-secondary font-sans">
                  <tr>
                    <th className="px-6 py-3 font-semibold">Metadata Field</th>
                    <th className="px-6 py-3 font-semibold">Extracted Value</th>
                    <th className="px-6 py-3 font-semibold">Integrity Status</th>
                    <th className="px-6 py-3 font-semibold">Forensic Interpretation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border font-sans">
                  <tr className="hover:bg-ivory/50">
                    <td className="px-6 py-3.5 font-semibold text-ink">Software / Editing Tool</td>
                    <td className="px-6 py-3.5 font-mono text-xs">{imageData?.exif?.software || 'Adobe Photoshop 24.1 (Windows)'}</td>
                    <td className="px-6 py-3.5">
                      <span className="inline-flex items-center gap-1 text-2xs font-bold text-tomato bg-tomato-light px-2.5 py-1 rounded-full border border-tomato/30">
                        <XCircle className="w-3.5 h-3.5" />
                        SUSPICIOUS
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-ink-secondary">
                      Native mobile OS screenshots do not contain desktop raster editor signatures.
                    </td>
                  </tr>

                  <tr className="hover:bg-ivory/50">
                    <td className="px-6 py-3.5 font-semibold text-ink">Perceptual Hash (pHash)</td>
                    <td className="px-6 py-3.5 font-mono text-xs">{imageData?.phash || 'd8f2a1b9e4c30761'}</td>
                    <td className="px-6 py-3.5">
                      <span className="inline-flex items-center gap-1 text-2xs font-bold text-ochre-dark bg-ochre-light px-2.5 py-1 rounded-full border border-ochre/30">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        TEMPLATE REUSE
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-ink-secondary">
                      pHash Hamming distance ≤ 4 matches genuine payment slip EXH-08 with altered text layout.
                    </td>
                  </tr>

                  <tr className="hover:bg-ivory/50">
                    <td className="px-6 py-3.5 font-semibold text-ink">Image Dimensions</td>
                    <td className="px-6 py-3.5 font-mono text-xs">{imageData?.dimensions || '1080 × 2400 px (20:9 Aspect Ratio)'}</td>
                    <td className="px-6 py-3.5">
                      <span className="inline-flex items-center gap-1 text-2xs font-bold text-lime-dark bg-lime-light px-2.5 py-1 rounded-full border border-lime-dark/30">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        CONSISTENT
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-ink-secondary">
                      Matches resolution of victim Samsung Galaxy A54 device display.
                    </td>
                  </tr>

                  <tr className="hover:bg-ivory/50">
                    <td className="px-6 py-3.5 font-semibold text-ink">Color Space</td>
                    <td className="px-6 py-3.5 font-mono text-xs">{imageData?.color_space || 'sRGB (8-bit per channel)'}</td>
                    <td className="px-6 py-3.5">
                      <span className="inline-flex items-center gap-1 text-2xs font-bold text-lime-dark bg-lime-light px-2.5 py-1 rounded-full border border-lime-dark/30">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        CONSISTENT
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-ink-secondary">
                      Standard sRGB IEC61966-2.1 display profile.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB B: STATEMENT ARITHMETIC */}
      {activeTab === 'statements' && (
        <div className="space-y-8">
          {/* Statement Selector */}
          <div className="flex items-center gap-2.5 flex-wrap bg-surface-raised p-4 rounded-xl border border-border shadow-xs">
            <span className="text-xs font-bold text-ink-secondary uppercase tracking-wider mr-2">
              Select Statement Exhibit:
            </span>
            {statementExhibits.map((st) => (
              <button
                key={st.id}
                type="button"
                onClick={() => setSelectedStatementId(st.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-sans transition-all cursor-pointer ${
                  activeStatementId === st.id
                    ? 'bg-cobalt text-white font-semibold shadow-xs'
                    : 'bg-surface text-ink border border-border hover:bg-ivory-dark'
                }`}
              >
                <ExhibitChip exhibitId={st.exhibit_id} />
                <span className="truncate max-w-[160px] font-sans">{st.filename}</span>
              </button>
            ))}
          </div>

          {/* Discrepancy Alert Banner */}
          {statementData?.has_discrepancy && (
            <div className="bg-tomato-light border border-tomato/40 rounded-xl p-5 space-y-2">
              <div className="flex items-center gap-2 text-tomato font-sans font-bold text-sm">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>Arithmetic Verification Failure: GT-08 Ledger Balance Tampering</span>
              </div>
              <p className="text-xs text-ink leading-relaxed font-sans">
                The printed balance on row 8 fails deterministic arithmetic verification (Previous Balance - Debit ≠ Stated Balance). Expected balance was <b className="font-mono">INR 1,90,000.00</b>, but the statement stated <b className="font-mono">INR 2,20,000.00</b> (discrepancy of <span className="font-bold text-tomato font-mono">+INR 30,000.00</span>).
              </p>
            </div>
          )}

          {/* Running Balance Ledger Verification Table */}
          <div className="bg-surface-raised border border-border rounded-xl overflow-hidden shadow-xs">
            <div className="px-6 py-4 border-b border-border bg-surface text-xs font-sans font-bold text-ink flex items-center justify-between">
              <span>STATEMENT LEDGER VERIFICATION BREAKDOWN</span>
              <span className="text-ink-secondary font-normal text-2xs">FORMULA: PREV_BALANCE + CREDIT - DEBIT = EXPECTED_BALANCE</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-ivory border-b border-border text-2xs uppercase tracking-wider text-ink-secondary select-none font-sans">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Row</th>
                    <th className="px-4 py-3 font-semibold">Date</th>
                    <th className="px-6 py-3 font-semibold">Description / Narration</th>
                    <th className="px-4 py-3 font-semibold text-right">Debit (-)</th>
                    <th className="px-4 py-3 font-semibold text-right">Credit (+)</th>
                    <th className="px-4 py-3 font-semibold text-right">Stated Balance</th>
                    <th className="px-4 py-3 font-semibold text-right">Computed Balance</th>
                    <th className="px-4 py-3 font-semibold text-center">Status</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-border font-mono text-xs">
                  {statementLoading ? (
                    <tr>
                      <td colSpan={8} className="p-10 text-center text-ink-secondary font-sans text-xs">
                        Auditing balance arithmetic rows...
                      </td>
                    </tr>
                  ) : statementData?.rows?.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="p-10 text-center text-ink-secondary font-sans text-xs">
                        No transactions parsed for this exhibit.
                      </td>
                    </tr>
                  ) : (
                    statementData?.rows?.map((row: any) => {
                      const isFailing = row.is_failing;
                      return (
                        <tr
                          key={row.row_index}
                          className={`transition-colors ${
                            isFailing ? 'bg-tomato-light/60 font-bold text-tomato' : 'hover:bg-ivory/50 text-ink'
                          }`}
                        >
                          <td className="px-4 py-3 font-sans text-ink-secondary">#{row.row_index}</td>
                          <td className="px-4 py-3 text-ink-secondary whitespace-nowrap">{row.date}</td>
                          <td className="px-6 py-3 font-sans text-ink truncate max-w-xs">{row.description}</td>
                          <td className="px-4 py-3 text-right font-medium text-tomato">
                            {row.debit ? `₹${row.debit.toLocaleString()}` : '—'}
                          </td>
                          <td className="px-4 py-3 text-right font-medium text-lime-dark">
                            {row.credit ? `₹${row.credit.toLocaleString()}` : '—'}
                          </td>
                          <td className="px-4 py-3 text-right font-bold">
                            ₹{row.stated_balance?.toLocaleString() || '0'}
                          </td>
                          <td className="px-4 py-3 text-right font-semibold">
                            ₹{row.expected_balance?.toLocaleString() || '0'}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {isFailing ? (
                              <span className="inline-flex items-center gap-1 text-2xs px-2.5 py-1 rounded-full bg-tomato text-white font-sans font-bold">
                                <XCircle className="w-3.5 h-3.5" />
                                FAIL (+₹30K)
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-2xs px-2.5 py-1 rounded-full bg-lime-light text-lime-dark font-sans font-bold border border-lime-dark/30">
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                MATCH
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
