import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Send,
  ShieldAlert,
  BookOpen,
  PlusCircle,
  Network,
  Compass,
  ChevronDown,
  ChevronUp,
  Lightbulb,
} from 'lucide-react';
import { useAppStore } from '../lib/store';
import { WorkspaceHeader } from '../components/ui/WorkspaceHeader';
import { TierBadge } from '../components/ui/TierBadge';
import { ExhibitChip } from '../components/evidence/ExhibitChip';
import { EmptyState } from '../components/ui/Skeleton';
import { ExplainPanel } from '../components/ui/ExplainPanel';

export const AssistantPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialFocus = searchParams.get('focus') || undefined;
  const setSelectedEntityId = useAppStore((s) => s.setSelectedEntityId);

  const [question, setQuestion] = useState('');
  const [language, setLanguage] = useState<'en' | 'hi'>('en');
  const [focusEntity] = useState<string | undefined>(initialFocus);
  const [starters, setStarters] = useState<string[]>([]);
  const [messages, setMessages] = useState<any[]>([]);
  const [selectedMsgIdx, setSelectedMsgIdx] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [expandedTrace, setExpandedTrace] = useState<Record<number, boolean>>({});
  const [promotedNotice, setPromotedNotice] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/assistant/starters')
      .then((r) => r.json())
      .then((d) => setStarters(d.starters || []))
      .catch(() => {});
  }, []);

  const sendQuestion = async (qText: string) => {
    if (!qText.trim()) return;
    setLoading(true);
    setPromotedNotice(null);
    try {
      const res = await fetch('/api/assistant/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: qText,
          session_id: 'ui-session',
          focus_entity: focusEntity,
          language,
        }),
      });
      const data = await res.json();
      setMessages((prev) => {
        const next = [...prev, { question: qText, response: data }];
        setSelectedMsgIdx(next.length - 1);
        return next;
      });
      setQuestion('');
    } finally {
      setLoading(false);
    }
  };

  const runQuickAction = async (endpoint: string, label: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/assistant/${endpoint}`);
      const data = await res.json();
      const text =
        endpoint === 'leads'
          ? (data.leads || []).map((l: any) => `- [${l.tier}] ${l.title}: ${l.reason}`).join('\n')
          : endpoint === 'challenge'
          ? (data.objections || []).map((o: any) => `- [${o.severity}] ${o.title}: ${o.argument}`).join('\n')
          : (data.entries || []).map((e: any) => `- ${e.date}: ${e.summary}`).join('\n');
      setMessages((prev) => {
        const next = [
          ...prev,
          {
            question: label,
            response: {
              answer: text || 'No items found.',
              claims: [],
              leads: endpoint === 'leads' ? data.leads || [] : undefined,
              objections: endpoint === 'challenge' ? data.objections || [] : undefined,
              mode: 'deterministic',
              ai_run_id: data.ai_run_id,
              record_sha256: data.record_sha256,
              how_i_got_this: {
                question: label,
                tool_calls: [{ tool: endpoint, args: {}, records_returned: 1 }],
                verifier_removed: [],
                model: 'deterministic',
                ai_run_id: data.ai_run_id,
                record_sha256: data.record_sha256,
              },
            },
          },
        ];
        setSelectedMsgIdx(next.length - 1);
        return next;
      });
    } finally {
      setLoading(false);
    }
  };

  const promoteAnswer = async (resp: any) => {
    const refs = (resp.claims || []).flatMap((c: any) => c.refs || []);
    if (refs.length === 0) {
      setPromotedNotice('Cannot add unsourced answer to Review Queue (Rule V4: No source, no claim).');
      return;
    }
    const res = await fetch('/api/assistant/promote', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: resp.answer, refs, ai_run_id: resp.ai_run_id }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to promote claim' }));
      setPromotedNotice(`Rejected by Verifier: ${err.detail || 'Failed to add to Review Queue'}`);
      return;
    }
    setPromotedNotice('Verified & added to Review Queue (Workspace 1) awaiting human approval.');
  };

  const activeMessage = messages[selectedMsgIdx] || null;
  const activeClaims = activeMessage?.response?.claims || [];

  return (
    <div className="max-w-7xl mx-auto space-y-4 h-[calc(100vh-8.5rem)] flex flex-col">
      <WorkspaceHeader
        workspace="investigation"
        title="Investigator Assistant"
        subtitle="Retrieval-first forensic Q&A. Answers cite verified database records only; unverified claims are removed."
        actions={
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as 'en' | 'hi')}
            aria-label="Response language"
            className="text-xs border border-border rounded px-2.5 py-1.5 bg-panel text-ink"
          >
            <option value="en">English</option>
            <option value="hi">Hindi (model-translated)</option>
          </select>
        }
      />

      {/* Two-Pane Layout: Left Conversation, Right Evidence */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-5 min-h-0">
        {/* LEFT PANE: Conversation */}
        <section className="lg:col-span-7 editorial-card flex flex-col min-h-0 overflow-hidden">
          {/* Quick Actions */}
          <div className="p-3.5 border-b border-border bg-[#F5F4F0] flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => runQuickAction('leads', 'Suggest next leads')}
              className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md border border-[#C1CFE4] bg-[#EEF2F8] text-[#415E87] hover:bg-[#5576A5] hover:text-white font-semibold transition-colors cursor-pointer"
            >
              <Lightbulb className="w-3.5 h-3.5" />
              <span>Suggest next leads</span>
            </button>
            <button
              type="button"
              onClick={() => runQuickAction('challenge', 'Challenge this case')}
              className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md border border-[#EAB5AF] bg-[#FDF0EE] text-[#A63327] hover:bg-[#C74437] hover:text-white font-semibold transition-colors cursor-pointer"
            >
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>Challenge this case</span>
            </button>
            <button
              type="button"
              onClick={() => runQuickAction('diary', 'Draft case diary')}
              className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md border border-[#C9C6BC] bg-white text-[#20283A] hover:border-[#316A78] hover:text-[#24525D] font-semibold transition-colors cursor-pointer"
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>Draft case diary</span>
            </button>
            {focusEntity && (
              <span className="ml-auto font-mono text-[11px] text-[#415E87] bg-[#EEF2F8] px-2.5 py-1 rounded border border-[#C1CFE4]">
                Focus: {focusEntity}
              </span>
            )}
          </div>

          {promotedNotice && (
            <div className="mx-4 mt-3 px-3 py-2 rounded bg-approved-light border border-approved-border text-approved text-xs font-medium">
              {promotedNotice}
            </div>
          )}

          {/* Messages / Starter Chips */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="space-y-4 py-4">
                <EmptyState
                  title="Ask a question about the case evidence"
                  description="Select a starter prompt below or type a query in English, Hindi, or Hinglish."
                />
                <div className="flex flex-wrap gap-2">
                  {starters.map((s, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => sendQuestion(s)}
                      className="text-xs px-3 py-1.5 rounded border border-border bg-paper hover:border-amber text-ink cursor-pointer transition-colors duration-150"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((m, idx) => {
                const r = m.response;
                const isSelected = idx === selectedMsgIdx;
                return (
                  <div
                    key={idx}
                    onClick={() => setSelectedMsgIdx(idx)}
                    className={`border rounded p-4 space-y-3 cursor-pointer transition-colors duration-150 ${
                      isSelected ? 'border-amber bg-paper' : 'border-border bg-panel hover:bg-paper'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-sm text-ink">{m.question}</span>
                      <span className="font-mono text-[10px] px-2 py-0.5 rounded border border-border bg-panel text-muted">
                        {r.mode}
                      </span>
                    </div>

                    {r.leads ? (
                      <div className="space-y-2">
                        {r.leads.map((l: any, lIdx: number) => (
                          <div key={lIdx} className="p-2.5 bg-panel border border-border rounded space-y-2 text-xs">
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-semibold text-ink">{l.title}</span>
                              <TierBadge tier={l.tier || 'LEAD'} size="sm" />
                            </div>
                            <p className="text-muted">{l.reason}</p>
                            <ExplainPanel explain={l.explain} compact label="Explain lead" />
                          </div>
                        ))}
                      </div>
                    ) : r.objections ? (
                      <div className="space-y-2">
                        {r.objections.map((o: any, oIdx: number) => (
                          <div key={oIdx} className="p-2.5 bg-panel border border-border rounded space-y-2 text-xs">
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-semibold text-ink">{o.title}</span>
                              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-vermilion-light text-vermilion border border-vermilion/40">
                                {o.severity}
                              </span>
                            </div>
                            <p className="text-muted">{o.argument}</p>
                            <ExplainPanel explain={o.explain} compact label="Explain objection" />
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-sm text-ink whitespace-pre-line leading-relaxed">{r.answer}</div>
                    )}

                    {/* Action buttons */}
                    <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border text-xs">
                      <button
                        type="button"
                        disabled={!r.claims || r.claims.length === 0}
                        title={
                          !r.claims || r.claims.length === 0
                            ? 'Cannot promote answers with zero cited source records'
                            : 'Verify and send to Review Queue'
                        }
                        onClick={(e) => {
                          e.stopPropagation();
                          promoteAnswer(r);
                        }}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-teal-border bg-teal-light text-teal font-medium cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        <PlusCircle className="w-3.5 h-3.5" />
                        <span>Add to review queue</span>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (focusEntity) setSelectedEntityId(focusEntity);
                          navigate('/graph');
                        }}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-border bg-panel text-ink cursor-pointer"
                      >
                        <Network className="w-3.5 h-3.5 text-amber" />
                        <span>Show on graph</span>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate('/reconstruction');
                        }}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-border bg-panel text-ink cursor-pointer"
                      >
                        <Compass className="w-3.5 h-3.5 text-amber" />
                        <span>Show on reconstruction</span>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedTrace((p) => ({ ...p, [idx]: !p[idx] }));
                        }}
                        className="ml-auto inline-flex items-center gap-1 text-muted hover:text-ink cursor-pointer"
                      >
                        {expandedTrace[idx] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        <span>How I got this</span>
                      </button>
                    </div>

                    {expandedTrace[idx] && r.how_i_got_this && (
                      <pre className="p-3 bg-panel border border-border rounded text-[11px] font-mono overflow-x-auto">
                        {JSON.stringify(r.how_i_got_this, null, 2)}
                      </pre>
                    )}

                    {r.explain && <ExplainPanel explain={r.explain} compact label="Explain answer" />}
                  </div>
                );
              })
            )}
          </div>

          {/* Input Bar */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendQuestion(question);
            }}
            className="p-3.5 border-t border-border bg-[#F5F4F0] flex gap-2.5"
          >
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about entities, timelines, transfers, locations, or anomalies…"
              className="flex-1 px-3.5 py-2 text-sm border border-[#C9C6BC] rounded-md bg-white text-[#20283A] placeholder:text-[#556077] focus:border-[#316A78] outline-none transition-colors"
            />
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-[#316A78] hover:bg-[#24525D] text-white text-xs font-semibold disabled:opacity-55 cursor-pointer transition-colors shadow-sm"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{loading ? 'Querying…' : 'Ask'}</span>
            </button>
          </form>
        </section>

        {/* RIGHT PANE: Cited Evidence */}
        <aside className="lg:col-span-5 editorial-card flex flex-col min-h-0 overflow-hidden">
          <div className="p-4 border-b border-border bg-paper/80 flex items-center justify-between">
            <span className="section-label">Evidence for Selected Answer</span>
            <span className="font-mono text-[11px] text-violet font-semibold bg-violet-light px-2.5 py-0.5 rounded-full border border-violet-border/70">
              {activeClaims.length} cited claims
            </span>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3 text-xs">
            {!activeMessage ? (
              <EmptyState
                title="No answer selected"
                description="Ask a question or click any answer on the left to inspect its cited exhibit chips, quotes, and hashes."
              />
            ) : activeClaims.length === 0 ? (
              <EmptyState
                title="No cited claims for this response"
                description="Either no evidence matched the query (No-Evidence Rule) or the response is an advisory summary."
              />
            ) : (
              activeClaims.map((c: any, idx: number) => (
                <div key={idx} className="p-3 bg-paper border border-border rounded space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <TierBadge tier={c.tier || 'LEAD'} size="sm" />
                    <div className="flex flex-wrap gap-1">
                      {(c.refs || []).map((refId: string) => (
                        <ExhibitChip key={refId} exhibitId="SOURCE" eventId={refId} />
                      ))}
                    </div>
                  </div>
                  <p className="text-ink leading-relaxed">{c.text}</p>
                  {c.quotes && c.quotes.length > 0 && (
                    <blockquote className="pl-2.5 border-l-2 border-teal font-mono text-[11px] text-muted">
                      &ldquo;{c.quotes[0].text || c.quotes[0]}&rdquo;
                    </blockquote>
                  )}
                </div>
              ))
            )}
          </div>
        </aside>
      </div>
    </div>
  );
};
