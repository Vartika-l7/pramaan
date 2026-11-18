import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CheckSquare,
  Check,
  X,
  Edit2,
  ArrowRight,
  ShieldCheck,
  Clock,
  Layers,
  FileCode,
  Keyboard,
  FileText,
  Sparkles,
} from 'lucide-react';
import { fetchEventSource } from '../lib/api';
import { TierBadge } from '../components/ui/TierBadge';
import { ExhibitChip } from '../components/evidence/ExhibitChip';

export const ReviewQueuePage: React.FC = () => {
  const queryClient = useQueryClient();

  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [editedText, setEditedText] = useState<string>('');

  const { data: queueData, isLoading } = useQuery({
    queryKey: ['reviewQueue'],
    queryFn: async () => {
      const res = await fetch('/api/review/queue');
      return res.json();
    },
  });

  const items = [...(queueData?.claims || []), ...(queueData?.edges || [])];
  const currentItem = items[selectedIndex] || null;

  // Fetch underlying source context for the selected item's primary ref
  const primaryRefId = currentItem?.refs?.[0] || currentItem?.event_ids?.[0];
  const { data: sourceContext } = useQuery({
    queryKey: ['eventSource', primaryRefId],
    queryFn: () => (primaryRefId ? fetchEventSource(primaryRefId) : null),
    enabled: !!primaryRefId,
  });

  const reviewMutation = useMutation({
    mutationFn: async ({
      itemId,
      decision,
      modifiedText,
    }: {
      itemId: string;
      decision: string;
      modifiedText?: string;
    }) => {
      const res = await fetch(`/api/review/${itemId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, modified_text: modifiedText }),
      });
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviewQueue'] });
      setIsEditing(false);
    },
  });

  // Hotkey navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (isEditing) return;

      if (e.key === 'j' || e.key === 'ArrowDown') {
        setSelectedIndex((prev) => Math.min(prev + 1, items.length - 1));
      } else if (e.key === 'k' || e.key === 'ArrowUp') {
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === 'a' && currentItem) {
        reviewMutation.mutate({ itemId: currentItem.id, decision: 'APPROVED' });
      } else if (e.key === 'r' && currentItem) {
        reviewMutation.mutate({ itemId: currentItem.id, decision: 'REJECTED' });
      } else if (e.key === 'e' && currentItem) {
        setIsEditing(true);
        setEditedText(currentItem.text || currentItem.reason_text || '');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [items.length, currentItem, isEditing]);

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col space-y-4 max-w-7xl mx-auto font-sans">
      {/* Top Header */}
      <div className="flex items-center justify-between border-b border-border pb-4 shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-sans text-xs font-bold uppercase tracking-wider text-cobalt bg-cobalt-light px-2.5 py-1 rounded-full">
              Adjudication Desk
            </span>
            <span className="text-ink-tertiary">·</span>
            <span className="font-sans text-xs text-ink-secondary">Human-in-the-Loop Queue</span>
          </div>
          <h1 className="font-serif font-bold text-3xl text-ink mt-1 tracking-tight">
            AI Claim & Relationship Review
          </h1>
        </div>

        {/* Hotkey Guide Pill */}
        <div className="hidden md:flex items-center gap-3 bg-surface-raised px-4 py-2 rounded-xl border border-border text-xs text-ink-secondary shadow-xs">
          <span className="font-semibold text-ink flex items-center gap-1.5">
            <Keyboard className="w-3.5 h-3.5 text-cobalt" />
            Hotkeys:
          </span>
          <span><kbd className="font-mono bg-ivory px-1.5 py-0.5 rounded border border-border font-bold text-ink">J</kbd> / <kbd className="font-mono bg-ivory px-1.5 py-0.5 rounded border border-border font-bold text-ink">K</kbd> navigate</span>
          <span><kbd className="font-mono bg-ivory px-1.5 py-0.5 rounded border border-border font-bold text-ink">A</kbd> approve</span>
          <span><kbd className="font-mono bg-ivory px-1.5 py-0.5 rounded border border-border font-bold text-ink">R</kbd> reject</span>
          <span><kbd className="font-mono bg-ivory px-1.5 py-0.5 rounded border border-border font-bold text-ink">E</kbd> edit</span>
        </div>
      </div>

      {/* Split Dual-Pane View */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-0">
        {/* LEFT PANE (5 COLS): RISK-SORTED REVIEW QUEUE */}
        <div className="lg:col-span-5 bg-surface-raised border border-border rounded-xl flex flex-col min-h-0 shadow-xs overflow-hidden">
          <div className="p-4 border-b border-border bg-surface flex items-center justify-between shrink-0">
            <span className="text-xs font-bold text-ink uppercase tracking-wider">
              Pending Adjudication ({items.length})
            </span>
            <span className="text-2xs text-ink-secondary font-mono">
              SORTED BY FORENSIC RISK
            </span>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-border/60">
            {isLoading ? (
              <div className="p-10 text-center text-xs text-ink-secondary">Loading verification queue...</div>
            ) : items.length === 0 ? (
              <div className="p-10 text-center text-xs text-ink-secondary">All AI claims adjudicated. Queue clear.</div>
            ) : (
              items.map((item, idx) => {
                const isSelected = idx === selectedIndex;
                const isClaim = !!item.text;

                return (
                  <div
                    key={item.id}
                    onClick={() => {
                      setSelectedIndex(idx);
                      setIsEditing(false);
                    }}
                    className={`p-4 transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-cobalt-light/50 border-l-4 border-l-cobalt shadow-xs'
                        : 'hover:bg-ivory/60'
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-ink-secondary">
                          #{String(idx + 1).padStart(2, '0')}
                        </span>
                        <span className="font-sans text-2xs uppercase tracking-wider font-bold px-2 py-0.5 rounded-full bg-surface-raised border border-border text-ink">
                          {isClaim ? 'AI CLAIM' : 'GRAPH EDGE'}
                        </span>
                      </div>
                      <TierBadge tier={item.tier || 'LEAD'} size="sm" />
                    </div>

                    <p className="text-xs text-ink line-clamp-2 leading-relaxed font-sans font-medium">
                      {item.text || item.reason_text}
                    </p>

                    <div className="mt-2.5 flex items-center justify-between text-2xs text-ink-secondary">
                      <span>Citations: {item.refs?.length || item.event_ids?.length || 0} exhibit records</span>
                      <span className="font-mono text-ink-tertiary">{item.id.slice(0, 10)}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT PANE (7 COLS): EVIDENCE CITATION INSPECTION */}
        <div className="lg:col-span-7 bg-surface-raised border border-border rounded-xl flex flex-col min-h-0 shadow-xs overflow-hidden">
          {currentItem ? (
            <div className="flex-1 flex flex-col min-h-0">
              {/* Item Header */}
              <div className="p-6 border-b border-border bg-surface shrink-0 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-xs font-bold text-cobalt bg-cobalt-light px-2.5 py-1 rounded-md border border-cobalt/20">
                      ITEM {String(selectedIndex + 1).padStart(2, '0')}
                    </span>
                    <span className="font-sans text-xs uppercase tracking-wider font-bold text-ink-secondary">
                      {currentItem.kind || currentItem.edge_type}
                    </span>
                  </div>

                  {/* Decision Action Buttons */}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() =>
                        reviewMutation.mutate({ itemId: currentItem.id, decision: 'APPROVED' })
                      }
                      className="flex items-center gap-1.5 px-3.5 py-1.5 bg-lime-light hover:bg-lime-light/80 text-lime-dark text-xs font-sans font-bold rounded-lg border border-lime-dark/30 transition-all cursor-pointer shadow-xs"
                    >
                      <Check className="w-4 h-4" />
                      <span>Approve [A]</span>
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        reviewMutation.mutate({ itemId: currentItem.id, decision: 'REJECTED' })
                      }
                      className="flex items-center gap-1.5 px-3.5 py-1.5 bg-tomato-light hover:bg-tomato-light/80 text-tomato text-xs font-sans font-bold rounded-lg border border-tomato/30 transition-all cursor-pointer shadow-xs"
                    >
                      <X className="w-4 h-4" />
                      <span>Reject [R]</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        setIsEditing(!isEditing);
                        setEditedText(currentItem.text || currentItem.reason_text || '');
                      }}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-surface hover:bg-ivory text-ink text-xs font-sans font-semibold rounded-lg border border-border transition-all cursor-pointer shadow-xs"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                      <span>Edit [E]</span>
                    </button>
                  </div>
                </div>

                {/* Proposed Claim Prose or Edit Mode */}
                {isEditing ? (
                  <div className="space-y-3 pt-2">
                    <textarea
                      value={editedText}
                      onChange={(e) => setEditedText(e.target.value)}
                      rows={3}
                      className="w-full text-sm font-sans text-ink bg-surface-raised border border-cobalt rounded-lg p-3.5 focus:outline-hidden ring-2 ring-cobalt/20"
                    />
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => setIsEditing(false)}
                        className="px-3 py-1 text-xs text-ink-secondary hover:text-ink cursor-pointer"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          reviewMutation.mutate({
                            itemId: currentItem.id,
                            decision: 'APPROVED',
                            modifiedText: editedText,
                          })
                        }
                        className="px-4 py-1.5 bg-cobalt text-white text-xs font-sans font-semibold rounded-lg hover:bg-cobalt-dark transition-colors cursor-pointer"
                      >
                        Save &amp; Approve
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="pt-1">
                    <span className="text-2xs font-sans uppercase tracking-wider text-ink-tertiary font-bold block mb-1">
                      Proposed Forensic Claim
                    </span>
                    <p className="font-serif text-lg font-bold text-ink leading-relaxed">
                      "{currentItem.text || currentItem.reason_text}"
                    </p>
                  </div>
                )}
              </div>

              {/* Source Evidence Context */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-sans text-xs uppercase tracking-wider font-bold text-ink flex items-center gap-2">
                      <FileCode className="w-4 h-4 text-cobalt" />
                      Underlying Source Citation &amp; Context
                    </span>
                    <span className="font-sans text-2xs text-lime-dark font-bold bg-lime-light px-2.5 py-1 rounded-full border border-lime-dark/30">
                      SEC. 63 BSA IMMUTABLE
                    </span>
                  </div>

                  {sourceContext ? (
                    <div className="space-y-4">
                      {/* File Coordinates */}
                      <div className="bg-surface p-4 rounded-xl border border-border flex items-center justify-between text-xs font-sans">
                        <div>
                          <span className="text-ink-secondary">Exhibit File: </span>
                          <span className="font-bold text-ink">{sourceContext.filename}</span>
                        </div>
                        <div className="font-mono text-2xs text-ink-secondary">
                          SHA-256: {sourceContext.sha256?.slice(0, 16)}...
                        </div>
                      </div>

                      {/* Raw Artifact Extract Window */}
                      <div className="bg-ivory-dark/40 text-ink font-mono text-xs p-5 rounded-xl border border-border leading-relaxed overflow-x-auto space-y-1">
                        {sourceContext.context_before?.map((line: string, i: number) => (
                          <div key={`b-${i}`} className="text-ink-tertiary opacity-60">
                            {line || ' '}
                          </div>
                        ))}

                        <div className="bg-ochre-light text-ink font-semibold my-2 px-3 py-1.5 rounded border-l-4 border-ochre-dark shadow-xs">
                          {sourceContext.target_lines?.map((line: string, i: number) => (
                            <div key={`t-${i}`}>{line}</div>
                          ))}
                        </div>

                        {sourceContext.context_after?.map((line: string, i: number) => (
                          <div key={`a-${i}`} className="text-ink-tertiary opacity-60">
                            {line || ' '}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="p-8 text-center text-xs text-ink-secondary bg-surface rounded-xl border border-border">
                      Loading raw database source context lines...
                    </div>
                  )}
                </div>

                {/* Exhibit References Chip List */}
                <div>
                  <span className="font-sans text-2xs uppercase tracking-wider text-ink-tertiary font-bold block mb-2">
                    Referenced Exhibit IDs
                  </span>
                  <div className="flex items-center gap-2 flex-wrap">
                    {(currentItem.refs || currentItem.event_ids || []).map((ref: string) => (
                      <ExhibitChip key={ref} exhibitId={ref.slice(0, 10)} eventId={ref} />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-10 text-center text-ink-secondary space-y-2">
              <CheckSquare className="w-10 h-10 opacity-30 text-ink" />
              <div className="font-serif text-lg font-semibold text-ink">No Item Selected</div>
              <p className="text-xs max-w-sm">
                Select a forensic claim or relationship edge from the left queue to inspect its raw evidentiary basis.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
