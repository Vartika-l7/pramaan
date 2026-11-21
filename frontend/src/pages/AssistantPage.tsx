import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { MessageSquare, Send, Sparkles, ShieldAlert, BookOpen, PlusCircle, Network, Compass, ChevronDown, ChevronUp } from 'lucide-react';

export const AssistantPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialFocus = searchParams.get('focus') || undefined;

  const [question, setQuestion] = useState('');
  const [language, setLanguage] = useState<'en' | 'hi'>('en');
  const [focusEntity, setFocusEntity] = useState<string | undefined>(initialFocus);
  const [starters, setStarters] = useState<string[]>([]);
  const [messages, setMessages] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedTrace, setExpandedTrace] = useState<Record<number, boolean>>({});

  useEffect(() => {
    fetch('/api/assistant/starters')
      .then((r) => r.json())
      .then((d) => setStarters(d.starters || []))
      .catch(() => {});
  }, []);

  const sendQuestion = async (qText: string) => {
    if (!qText.trim()) return;
    setLoading(true);
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
      setMessages((prev) => [...prev, { question: qText, response: data }]);
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
          ? (data.leads || []).map((l: any) => `- [${l.tier}] ${l.title}: ${l.reason} (Next: ${l.what_to_check_next})`).join('\n')
          : endpoint === 'challenge'
          ? (data.objections || []).map((o: any) => `- [${o.severity}] ${o.title}: ${o.argument}`).join('\n')
          : (data.entries || []).map((e: any) => `- ${e.date}: ${e.summary}`).join('\n');
      setMessages((prev) => [
        ...prev,
        {
          question: label,
          response: {
            answer: text || 'No items found.',
            claims: [],
            mode: 'deterministic',
            how_i_got_this: { question: label, tool_calls: [{ tool: endpoint, args: {}, records_returned: 1 }], verifier_removed: [], model: 'deterministic' },
          },
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const promoteAnswer = async (resp: any) => {
    const refs = (resp.claims || []).flatMap((c: any) => c.refs || []);
    await fetch('/api/assistant/promote', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: resp.answer, refs }),
    });
    alert('Added to Review Queue as PROPOSED claim.');
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <h1 className="font-serif text-2xl font-bold text-ink flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-cobalt" />
            Investigator Assistant
          </h1>
          <p className="text-xs text-ink-secondary mt-1">
            Retrieval-first forensic Q&amp;A. Answers cite verified records only; unverified claims are removed.
            {focusEntity && <span className="ml-2 font-mono text-cobalt">Focus: {focusEntity}</span>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as 'en' | 'hi')}
            className="text-xs border border-border rounded px-2 py-1 bg-surface"
          >
            <option value="en">English</option>
            <option value="hi">Hindi (model-translated)</option>
          </select>
        </div>
      </div>

      {/* Starter chips & quick actions */}
      <div className="flex flex-wrap gap-2">
        {starters.map((s, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => sendQuestion(s)}
            className="text-xs px-3 py-1.5 rounded-full border border-border bg-surface hover:bg-ivory text-ink"
          >
            {s}
          </button>
        ))}
        <button
          type="button"
          onClick={() => runQuickAction('leads', 'Suggest next leads')}
          className="text-xs px-3 py-1.5 rounded-full border border-cobalt/40 bg-surface text-cobalt font-semibold flex items-center gap-1"
        >
          <Sparkles className="w-3.5 h-3.5" /> Suggest next leads
        </button>
        <button
          type="button"
          onClick={() => runQuickAction('challenge', 'Challenge this case')}
          className="text-xs px-3 py-1.5 rounded-full border border-tomato/40 bg-surface text-tomato font-semibold flex items-center gap-1"
        >
          <ShieldAlert className="w-3.5 h-3.5" /> Challenge this case
        </button>
        <button
          type="button"
          onClick={() => runQuickAction('diary', 'Draft case diary')}
          className="text-xs px-3 py-1.5 rounded-full border border-border bg-surface text-ink font-semibold flex items-center gap-1"
        >
          <BookOpen className="w-3.5 h-3.5" /> Draft case diary
        </button>
      </div>

      {/* Conversation */}
      <div className="space-y-4">
        {messages.map((m, idx) => (
          <div key={idx} className="bg-surface-raised border border-border rounded-xl p-4 space-y-3">
            <div className="text-xs font-semibold text-ink-secondary">Q: {m.question}</div>
            <div className="text-sm text-ink whitespace-pre-wrap leading-relaxed">{m.response.answer}</div>
            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border/60">
              <span className="font-mono text-2xs px-2 py-0.5 rounded bg-ivory border border-border text-ink-secondary">
                {m.response.mode}
              </span>
              <button
                type="button"
                onClick={() => promoteAnswer(m.response)}
                className="text-2xs px-2.5 py-1 rounded border border-border bg-surface hover:bg-ivory flex items-center gap-1"
              >
                <PlusCircle className="w-3 h-3" /> Add to review queue
              </button>
              <button
                type="button"
                onClick={() => navigate('/graph')}
                className="text-2xs px-2.5 py-1 rounded border border-border bg-surface hover:bg-ivory flex items-center gap-1"
              >
                <Network className="w-3 h-3" /> Show on graph
              </button>
              <button
                type="button"
                onClick={() => navigate('/events')}
                className="text-2xs px-2.5 py-1 rounded border border-border bg-surface hover:bg-ivory flex items-center gap-1"
              >
                <Compass className="w-3 h-3" /> Show on reconstruction
              </button>
              <button
                type="button"
                onClick={() => setExpandedTrace((p) => ({ ...p, [idx]: !p[idx] }))}
                className="ml-auto text-2xs text-cobalt font-semibold flex items-center gap-1"
              >
                How I got this {expandedTrace[idx] ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>
            </div>
            {expandedTrace[idx] && m.response.how_i_got_this && (
              <pre className="text-2xs font-mono bg-ivory p-3 rounded border border-border overflow-x-auto">
                {JSON.stringify(m.response.how_i_got_this, null, 2)}
              </pre>
            )}
          </div>
        ))}
      </div>

      {/* Input */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          sendQuestion(question);
        }}
        className="flex gap-2"
      >
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about entities, timelines, transfers, locations, or anomalies (English / Hindi / Hinglish)..."
          className="flex-1 px-3 py-2 text-sm border border-border rounded-lg bg-surface text-ink"
        />
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 rounded-lg bg-cobalt text-white text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
        >
          <Send className="w-3.5 h-3.5" /> {loading ? 'Searching...' : 'Ask'}
        </button>
      </form>
    </div>
  );
};
