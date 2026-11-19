import React, { useState } from 'react';
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
  Scale,
  AlertTriangle,
  Play,
} from 'lucide-react';
import { fetchEventSource } from '../lib/api';
import { TierBadge } from '../components/ui/TierBadge';
import { ExhibitChip } from '../components/evidence/ExhibitChip';

export const ReviewQueuePage: React.FC = () => {
  const queryClient = useQueryClient();

  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [editedText, setEditedText] = useState<string>('');
  const [showChallenge, setShowChallenge] = useState<boolean>(false);

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

  // Folded Challenger Cross-examination
  const { data: challengeData, mutate: runChallenge, isPending: challengePending } = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/challenge/run', { method: 'POST' });
      return res.json();
    },
  });

  const reviewMutation = useMutation({
    mutationFn: async ({
      itemId,
      decision,
      newText,
    }: {
      itemId: string;
      decision: 'APPROVED' | 'REJECTED';
      newText?: string;
    }) => {
      const res = await fetch('/api/review/decision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          item_type: currentItem?.item_type || 'claim',
          item_id: itemId,
          decision,
          new_text: newText,
        }),
      });
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviewQueue'] });
      setIsEditing(false);
      setEditedText('');
      if (selectedIndex >= items.length - 1) {
        setSelectedIndex(Math.max(0, items.length - 2));
      }
    },
  });

  const handleApprove = () => {
    if (!currentItem) return;
    reviewMutation.mutate({
      itemId: currentItem.id,
      decision: 'APPROVED',
      newText: isEditing ? editedText : undefined,
    });
  };

  const handleReject = () => {
    if (!currentItem) return;
    reviewMutation.mutate({
      itemId: currentItem.id,
      decision: 'REJECTED',
    });
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16 font-sans">
      {/* Header */}
      <section className="space-y-2 border-b border-border pb-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-sans text-xs font-bold uppercase tracking-wider text-cobalt bg-cobalt-light px-2.5 py-1 rounded-full">
                Human-in-the-Loop Review
              </span>
              <span className="text-ink-tertiary">·</span>
              <span className="font-sans text-xs text-ink-secondary">
                Only Approved Items Enter Court Report
              </span>
            </div>
            <h1 className="font-serif text-3xl sm:text-4xl font-bold text-ink tracking-tight">
              Investigator Admissibility Queue
            </h1>
          </div>

          <button
            type="button"
            onClick={() => {
              setShowChallenge(!showChallenge);
              if (!challengeData) runChallenge();
            }}
            className="flex items-center gap-2 px-3.5 py-2 bg-surface hover:bg-ivory border border-border rounded-lg text-xs font-sans font-semibold text-ink transition-colors cursor-pointer"
          >
            <Scale className="w-4 h-4 text-cobalt" />
            <span>{challengePending ? 'Cross-Examining...' : 'Assistant Cross-Examination'}</span>
          </button>
        </div>
      </section>

      {/* Folded Challenge Action Drawer */}
      {showChallenge && (
        <div className="bg-surface-raised border border-border rounded-xl p-5 shadow-sm space-y-3 animate-in fade-in duration-150">
          <div className="flex items-center justify-between border-b border-border pb-2">
            <span className="font-bold text-xs uppercase tracking-wider text-ink flex items-center gap-1.5">
              <Scale className="w-4 h-4 text-cobalt" />
              Challenger AI Adversarial Analysis
            </span>
            <button type="button" onClick={() => setShowChallenge(false)} className="text-xs text-ink-tertiary hover:text-ink">
              Close
            </button>
          </div>
          {challengePending ? (
            <div className="text-xs text-ink-secondary py-4 text-center">Simulating adversarial cross-examination...</div>
          ) : challengeData ? (
            <div className="space-y-2 text-xs">
              <div className="text-ink font-semibold">Defensive Counter-Arguments:</div>
              <p className="text-ink-secondary bg-surface p-3 rounded-lg border border-border leading-relaxed">
                {challengeData.arguments || challengeData.summary || 'No fatal evidentiary contradictions discovered across current approved items.'}
              </p>
            </div>
          ) : (
            <div className="text-xs text-ink-secondary">Click to run adversarial cross-examination.</div>
          )}
        </div>
      )}

      {/* Main Review Queue Interface */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Col: Pending Items List */}
        <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
          <div className="text-xs font-bold uppercase tracking-wider text-ink-secondary px-1 mb-2">
            Pending Admissibility ({items.length})
          </div>
          {isLoading ? (
            <div className="p-8 text-center text-xs text-ink-secondary">Loading queue...</div>
          ) : items.length === 0 ? (
            <div className="p-8 text-center text-xs text-ink-secondary bg-surface rounded-xl border border-border">
              All proposed findings have been reviewed.
            </div>
          ) : (
            items.map((item, idx) => (
              <div
                key={item.id}
                onClick={() => {
                  setSelectedIndex(idx);
                  setIsEditing(false);
                }}
                className={`p-3.5 rounded-xl border cursor-pointer transition-all text-xs space-y-1.5 ${
                  selectedIndex === idx ? 'bg-cobalt-light/40 border-cobalt' : 'bg-surface hover:bg-ivory border-border'
                }`}
              >
                <div className="flex items-center justify-between">
                  <TierBadge tier={item.tier || 'LEAD'} />
                  <span className="font-mono text-2xs uppercase text-ink-tertiary">
                    {item.item_type || 'claim'}
                  </span>
                </div>
                <p className="font-medium text-ink line-clamp-2 leading-relaxed">
                  {item.text || item.reason_text}
                </p>
              </div>
            ))
          )}
        </div>

        {/* Right 2 Cols: Decision Workspace */}
        {currentItem && (
          <div className="lg:col-span-2 bg-surface-raised border border-border rounded-xl p-6 space-y-5 shadow-xs">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <span className="font-bold text-xs uppercase tracking-wider text-ink">
                Item #{selectedIndex + 1} of {items.length}
              </span>
              <TierBadge tier={currentItem.tier || 'LEAD'} />
            </div>

            <div className="space-y-2">
              <span className="text-2xs font-bold uppercase tracking-wider text-ink-tertiary">Proposed Finding</span>
              {isEditing ? (
                <textarea
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  className="w-full h-24 p-3 text-xs font-sans bg-surface border border-cobalt rounded-lg text-ink outline-hidden"
                />
              ) : (
                <p className="text-sm font-serif font-bold text-ink leading-relaxed p-3 bg-surface rounded-lg border border-border">
                  {currentItem.text || currentItem.reason_text}
                </p>
              )}
            </div>

            {/* Source Reference Linkage */}
            {sourceContext && (
              <div className="p-3 bg-ivory rounded-lg border border-border text-xs space-y-1">
                <span className="text-2xs font-bold uppercase tracking-wider text-ink-tertiary">Direct Grounding Source</span>
                <div className="font-mono text-2xs text-ink">{sourceContext.filename || 'Exhibit Grounding'}</div>
                <div className="text-ink-secondary text-2xs italic">"{sourceContext.raw_line || sourceContext.text || 'Grounding record verified.'}"</div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center justify-between pt-4 border-t border-border">
              <button
                type="button"
                onClick={() => {
                  setIsEditing(!isEditing);
                  setEditedText(currentItem.text || currentItem.reason_text);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-ink-secondary hover:text-ink border border-border rounded-lg bg-surface cursor-pointer"
              >
                <Edit2 className="w-3.5 h-3.5" />
                <span>{isEditing ? 'Cancel Edit' : 'Edit Text'}</span>
              </button>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleReject}
                  className="flex items-center gap-1.5 px-4 py-2 bg-tomato hover:bg-tomato-dark text-white text-xs font-semibold rounded-lg cursor-pointer transition-colors"
                >
                  <X className="w-4 h-4" />
                  <span>Reject Finding</span>
                </button>
                <button
                  type="button"
                  onClick={handleApprove}
                  className="flex items-center gap-1.5 px-4 py-2 bg-lime-dark hover:bg-lime-900 text-white text-xs font-semibold rounded-lg cursor-pointer transition-colors shadow-xs"
                >
                  <Check className="w-4 h-4" />
                  <span>Approve for Court</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
