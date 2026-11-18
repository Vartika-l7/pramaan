import React, { useEffect, useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import cytoscape from 'cytoscape';
// @ts-ignore
import fcose from 'cytoscape-fcose';
import {
  Network,
  Filter,
  Info,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ExternalLink,
  Shield,
  Layers,
  X,
  Compass,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import { fetchGraph, fetchEdgeDetail, reviewEdge } from '../lib/api';
import { TierBadge } from '../components/ui/TierBadge';
import { ExhibitChip } from '../components/evidence/ExhibitChip';

try {
  cytoscape.use(fcose);
} catch (e) {
  // Ignore re-registration
}

export const KnowledgeGraphPage: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const queryClient = useQueryClient();

  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [selectedTier, setSelectedTier] = useState<string>('ALL');
  const [minStrength, setMinStrength] = useState<number>(0.0);

  const { data: graphData, isLoading } = useQuery({
    queryKey: ['graphData', selectedTier, minStrength],
    queryFn: () =>
      fetchGraph({
        tier: selectedTier === 'ALL' ? undefined : selectedTier,
        min_strength: minStrength,
      }),
  });

  const { data: edgeDetail, isLoading: edgeLoading } = useQuery({
    queryKey: ['edgeDetail', selectedEdgeId],
    queryFn: () => (selectedEdgeId ? fetchEdgeDetail(selectedEdgeId) : null),
    enabled: !!selectedEdgeId,
  });

  const reviewMutation = useMutation({
    mutationFn: ({ edgeId, decision }: { edgeId: string; decision: 'APPROVED' | 'REJECTED' }) =>
      reviewEdge(edgeId, decision),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['graphData'] });
      queryClient.invalidateQueries({ queryKey: ['edgeDetail', selectedEdgeId] });
    },
  });

  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: {
        nodes: graphData.nodes,
        edges: graphData.edges,
      },
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'font-family': 'DM Sans, sans-serif',
            'font-size': '11px',
            'font-weight': 600,
            color: '#242D3A',
            'text-valign': 'bottom',
            'text-margin-y': 5,
            width: 32,
            height: 32,
            'background-color': '#FFFFFF',
            'border-width': 1.5,
            'border-color': '#DDD9CF',
          },
        },
        // Shape and color differentiation by node type
        {
          selector: 'node[type = "PERSON"]',
          style: {
            shape: 'ellipse',
            'background-color': '#EEF2FC',
            'border-color': '#315FCE',
            'border-width': 2,
          },
        },
        {
          selector: 'node[type = "PHONE"]',
          style: {
            shape: 'round-rectangle',
            'background-color': '#F5F9DC',
            'border-color': '#8FA820',
            'border-width': 1.5,
          },
        },
        {
          selector: 'node[type = "UPI"]',
          style: {
            shape: 'diamond',
            'background-color': '#FDF5E4',
            'border-color': '#A07820',
            'border-width': 2,
          },
        },
        {
          selector: 'node[type = "ACCOUNT"]',
          style: {
            shape: 'rectangle',
            'background-color': '#FEF0EC',
            'border-color': '#F05A3A',
            'border-width': 2,
          },
        },
        {
          selector: 'node[type = "DEVICE"]',
          style: {
            shape: 'hexagon',
            'background-color': '#F3F0FB',
            'border-color': '#6B4FA8',
            'border-width': 1.5,
          },
        },
        {
          selector: 'node[type = "LOCATION"]',
          style: {
            shape: 'barrel',
            'background-color': '#F4F0E7',
            'border-color': '#77766F',
            'border-width': 1.5,
          },
        },
        {
          selector: 'node[type = "EXHIBIT"]',
          style: {
            shape: 'barrel',
            'background-color': '#FFFFFF',
            'border-color': '#F05A3A',
            'border-width': 2,
          },
        },
        // Edge styling
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': '#DDD9CF',
            'target-arrow-color': '#DDD9CF',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(edge_type)',
            'font-family': 'IBM Plex Mono, monospace',
            'font-size': '9px',
            color: '#A09E97',
            'text-rotation': 'autorotate',
            'text-margin-y': -8,
            'arrow-scale': 0.9,
          },
        },
        // Edge styling by tier
        {
          selector: 'edge[tier = "APPROVED"]',
          style: {
            'line-color': '#8FA820',
            'target-arrow-color': '#8FA820',
            width: 2.5,
          },
        },
        {
          selector: 'edge[edge_type = "PATTERN_FUNNEL"]',
          style: {
            'line-color': '#F05A3A',
            'target-arrow-color': '#F05A3A',
            width: 3,
            'line-style': 'dashed',
          },
        },
        // Selection state
        {
          selector: 'edge:selected',
          style: {
            width: 3.5,
            'line-color': '#315FCE',
            'target-arrow-color': '#315FCE',
          },
        },
      ],
      layout: {
        name: 'fcose',
        quality: 'proof',
        randomize: false,
        animate: true,
        animationDuration: 400,
        nodeSeparation: 130,
        idealEdgeLength: 110,
      } as any,
    });

    cy.on('tap', 'edge', (evt) => {
      const edge = evt.target;
      setSelectedEdgeId(edge.id());
    });

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedEdgeId(null);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [graphData]);

  return (
    <div className="flex h-full gap-0">
      {/* Left Panel */}
      <div className="w-72 bg-surface-raised border-r border-border flex flex-col shrink-0">
        {/* Header */}
        <div className="px-5 py-4 border-b border-border">
          <h2 className="font-serif text-xl font-bold text-ink">Knowledge Graph</h2>
          {graphData && (
            <p className="text-xs text-ink-tertiary mt-0.5 font-mono">
              {graphData.total_nodes || 0} nodes · {graphData.total_edges || 0} edges
            </p>
          )}
        </div>

        {/* Filter Controls */}
        <div className="px-4 py-3 border-b border-border space-y-3">
          {/* Tier Filter */}
          <div>
            <label className="section-label block mb-1.5">Tier</label>
            <select
              value={selectedTier}
              onChange={(e) => setSelectedTier(e.target.value)}
              className="bg-ivory border border-border rounded text-sm text-ink py-1.5 px-2 w-full"
            >
              <option value="ALL">All Tiers</option>
              <option value="LEAD">Lead</option>
              <option value="APPROVED">Approved</option>
            </select>
          </div>

          {/* Strength Slider */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="section-label">Min Strength</label>
              <span className="font-mono text-xs font-semibold text-ink">
                {(minStrength * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={minStrength}
              onChange={(e) => setMinStrength(parseFloat(e.target.value))}
              className="w-full accent-cobalt"
            />
          </div>
        </div>

        {/* Entity Type Legend */}
        <div className="px-4 py-3 border-b border-border">
          <p className="section-label mb-2">Entity Types</p>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-xs text-ink-secondary">
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: '#315FCE' }} />
              <span>PERSON</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-ink-secondary">
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: '#8FA820' }} />
              <span>PHONE</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-ink-secondary">
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: '#A07820' }} />
              <span>UPI</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-ink-secondary">
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: '#F05A3A' }} />
              <span>ACCOUNT</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-ink-secondary">
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: '#6B4FA8' }} />
              <span>DEVICE</span>
            </div>
          </div>
        </div>

        {/* Selected Edge Details Panel */}
        <div className="flex-1 overflow-y-auto px-4 py-3">
          {!selectedEdgeId ? (
            <div className="text-xs text-ink-tertiary text-center py-8">
              <Network className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p>Click an edge to inspect the relationship</p>
            </div>
          ) : edgeLoading ? (
            <div className="py-8 text-center text-ink-secondary text-xs font-mono">
              Loading link details…
            </div>
          ) : edgeDetail ? (
            <div className="space-y-4">
              {/* Edge header */}
              <div className="flex items-start justify-between">
                <div>
                  <p className="section-label mb-0.5">Selected Edge</p>
                  <h4 className="font-serif font-bold text-sm text-ink">
                    {edgeDetail.edge_type || 'Relationship'}
                  </h4>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedEdgeId(null)}
                  className="p-1 hover:bg-ivory rounded text-ink-tertiary hover:text-ink cursor-pointer transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Metadata row */}
              <div className="bg-ivory rounded border border-border p-3 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="section-label">Tier</span>
                  <TierBadge tier={edgeDetail.tier || 'LEAD'} size="sm" />
                </div>
                <div className="flex items-center justify-between">
                  <span className="section-label">Strength</span>
                  <span className="font-mono font-bold text-ink">
                    {((edgeDetail.strength || 1) * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Why this link */}
              <div>
                <p className="font-serif italic text-xs text-ink-secondary mb-1.5">
                  Why this link
                </p>
                <p className="text-xs text-ink leading-relaxed bg-ivory rounded border border-border p-3">
                  {edgeDetail.reason_text}
                </p>
              </div>

              {/* Supporting exhibits */}
              {edgeDetail.supporting_events?.length > 0 && (
                <div>
                  <p className="section-label mb-2">Supporting Exhibits</p>
                  <div className="space-y-2">
                    {edgeDetail.supporting_events.map((ev: any) => (
                      <div
                        key={ev.id}
                        className="bg-ivory rounded border border-border p-2.5 space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <ExhibitChip exhibitId={ev.exhibit_id} eventId={ev.id} />
                          <span className="font-mono text-[10px] text-ink-tertiary">
                            {ev.ts_utc?.slice(0, 16).replace('T', ' ')}
                          </span>
                        </div>
                        <p className="font-mono text-[11px] text-ink truncate">{ev.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Review Actions */}
              <div className="pt-3 border-t border-border space-y-2">
                <p className="section-label">Investigator Decision</p>
                <div className="flex flex-col gap-2">
                  <button
                    type="button"
                    disabled={reviewMutation.isPending}
                    onClick={() =>
                      reviewMutation.mutate({ edgeId: selectedEdgeId, decision: 'APPROVED' })
                    }
                    className="flex items-center justify-center gap-1.5 py-1.5 px-3 bg-lime-light text-lime-dark border border-lime-dark/30 hover:bg-lime rounded text-xs font-medium transition-colors cursor-pointer"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Approve</span>
                  </button>
                  <button
                    type="button"
                    disabled={reviewMutation.isPending}
                    onClick={() =>
                      reviewMutation.mutate({ edgeId: selectedEdgeId, decision: 'REJECTED' })
                    }
                    className="flex items-center justify-center gap-1.5 py-1.5 px-3 bg-tomato-light text-tomato border border-tomato/30 hover:bg-tomato hover:text-white rounded text-xs font-medium transition-colors cursor-pointer"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    <span>Reject</span>
                  </button>
                  <button
                    type="button"
                    disabled={reviewMutation.isPending}
                    className="flex items-center justify-center gap-1.5 py-1.5 px-3 bg-ochre-light text-ochre-dark border border-ochre/30 rounded text-xs font-medium transition-colors cursor-pointer hover:bg-ochre/20"
                  >
                    <HelpCircle className="w-3.5 h-3.5" />
                    <span>Mark as Lead</span>
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {/* Graph Canvas */}
      <div className="flex-1 bg-ivory-dark relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center text-ink-secondary text-sm font-mono z-10">
            Loading graph…
          </div>
        )}
        <div ref={containerRef} className="w-full h-full" />
      </div>
    </div>
  );
};
