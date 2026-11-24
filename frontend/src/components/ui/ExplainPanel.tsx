import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Info } from 'lucide-react';
import { ExhibitChip } from '../evidence/ExhibitChip';
import { HashChip } from './HashChip';

export interface ExplainPayload {
  what_model_saw: {
    record_ids: string[];
    exhibits: Array<{ exhibit_id: string; event_id?: string; filename?: string }>;
  };
  what_model_said: {
    ai_run_id?: string | null;
    record_sha256?: string | null;
    model_name: string;
    model_version?: string;
    parameters?: Record<string, any>;
    raw_output: string;
    ts_utc?: string | null;
  };
  what_verifier_kept_and_removed: {
    notes?: string | null;
    kept: Array<{ id?: string; text?: string }>;
    removed: Array<{ claim_id?: string; text?: string; reason?: string }>;
  };
  who_approved: {
    approved: boolean;
    decision?: string | null;
    reviewer?: string | null;
    ts?: string | null;
    label: string;
  };
}

interface ExplainPanelProps {
  explain?: ExplainPayload | null;
  defaultOpen?: boolean;
  compact?: boolean;
  label?: string;
}

export const ExplainPanel: React.FC<ExplainPanelProps> = ({
  explain,
  defaultOpen = false,
  compact = false,
  label = 'Explain',
}) => {
  const [open, setOpen] = useState(defaultOpen);

  if (!explain) return null;

  const saw = explain.what_model_saw || { record_ids: [], exhibits: [] };
  const said = explain.what_model_said || { model_name: 'Deterministic', raw_output: '' };
  const ver = explain.what_verifier_kept_and_removed || { kept: [], removed: [] };
  const who = explain.who_approved || { approved: false, label: 'not yet approved' };

  return (
    <div className="border border-border rounded-lg bg-paper/80 text-xs overflow-hidden">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        aria-expanded={open}
        className={`w-full flex items-center justify-between gap-2 ${
          compact ? 'px-3 py-2' : 'px-3.5 py-2.5'
        } text-left text-ink-secondary hover:text-ink hover:bg-paper-subtle/60 cursor-pointer transition-colors duration-150`}
      >
        <span className="inline-flex items-center gap-1.5 font-semibold">
          <Info className="w-3.5 h-3.5 text-violet shrink-0" aria-hidden="true" />
          <span>{label}</span>
          {said.ai_run_id && (
            <span className="font-mono text-[10px] text-muted font-normal">({said.model_name})</span>
          )}
        </span>
        {open ? <ChevronUp className="w-3.5 h-3.5 text-muted" /> : <ChevronDown className="w-3.5 h-3.5 text-muted" />}
      </button>

      {open && (
        <div
          onClick={(e) => e.stopPropagation()}
          className="border-t border-border p-3.5 space-y-3.5 bg-panel text-xs"
        >
          {/* 1. What the model saw */}
          <div className="space-y-1">
            <div className="section-label">1. What the model saw</div>
            <div className="flex flex-wrap items-center gap-1.5">
              {(saw.exhibits || []).map((ex, i) => (
                <ExhibitChip
                  key={`${ex.exhibit_id}-${ex.event_id || i}`}
                  exhibitId={ex.exhibit_id}
                  eventId={ex.event_id}
                />
              ))}
              {(!saw.exhibits || saw.exhibits.length === 0) && (
                <span className="text-muted">No exhibit chips linked</span>
              )}
            </div>
            {saw.record_ids && saw.record_ids.length > 0 && (
              <div className="font-mono text-[11px] text-muted break-all">
                Record IDs ({saw.record_ids.length}): {saw.record_ids.slice(0, 8).join(', ')}
                {saw.record_ids.length > 8 ? ` … (+${saw.record_ids.length - 8} more)` : ''}
              </div>
            )}
          </div>

          {/* 2. What the model said (raw) */}
          <div className="space-y-1">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="section-label">2. What the model said (raw)</span>
              <span className="font-mono text-[10px] text-muted">
                {said.model_name}
                {said.model_version ? ` · ${said.model_version}` : ''}
                {said.parameters ? ` · temp=${said.parameters.temperature ?? 0}, seed=${said.parameters.seed ?? 42}` : ''}
              </span>
            </div>
            {said.record_sha256 && (
              <div className="flex items-center gap-2 text-[11px] text-muted">
                <span>AI Run Custody SHA-256:</span>
                <HashChip hash={said.record_sha256} />
              </div>
            )}
            <pre className="p-2 bg-paper border border-border rounded font-mono text-[11px] text-ink overflow-x-auto max-h-36 whitespace-pre-wrap break-words">
              {said.raw_output || '(no raw output recorded)'}
            </pre>
          </div>

          {/* 3. What the verifier kept and removed */}
          <div className="space-y-1">
            <div className="section-label">3. What the verifier kept and removed</div>
            {ver.notes && <div className="text-muted">{ver.notes}</div>}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <div className="p-2 rounded border border-teal-border bg-teal-light/60 space-y-1">
                <div className="font-mono text-[10px] font-bold uppercase text-teal">
                  Kept ({ver.kept?.length ?? 0})
                </div>
                {(ver.kept || []).length === 0 ? (
                  <div className="text-[11px] text-muted">None</div>
                ) : (
                  (ver.kept || []).slice(0, 4).map((k, idx) => (
                    <div key={idx} className="text-[11px] text-ink truncate">
                      • {k.text || k.id}
                    </div>
                  ))
                )}
              </div>
              <div className="p-2 rounded border border-vermilion/40 bg-vermilion-light/60 space-y-1">
                <div className="font-mono text-[10px] font-bold uppercase text-vermilion">
                  Removed ({ver.removed?.length ?? 0})
                </div>
                {(ver.removed || []).length === 0 ? (
                  <div className="text-[11px] text-muted">None removed</div>
                ) : (
                  (ver.removed || []).slice(0, 4).map((rem, idx) => (
                    <div key={idx} className="text-[11px] text-vermilion">
                      • {rem.reason || rem.text}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* 4. Who approved it */}
          <div className="flex items-center justify-between pt-1.5 border-t border-border">
            <span className="section-label">4. Who approved it</span>
            <span
              className={`font-mono text-[11px] font-semibold px-2 py-0.5 rounded border ${
                who.approved
                  ? 'bg-approved-light text-approved border-approved-border'
                  : 'bg-amber-light text-amber border-amber-border'
              }`}
            >
              {who.label || 'not yet approved'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
