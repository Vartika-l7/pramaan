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
  Search,
  Users,
} from 'lucide-react';
import { fetchGraph, fetchEdgeDetail, reviewEdge, fetchEntities, fetchEntityDetail } from '../lib/api';
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
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [entitySearch, setEntitySearch] = useState('');
  const [activeSidePanel, setActiveSidePanel] = useState<'edge' | 'entities'>('entities');
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

  // Folded Entities Queries
  const { data: entitiesList } = useQuery({
    queryKey: ['entitiesList'],
    queryFn: () => fetchEntities(),
  });

  const { data: entityDetail } = useQuery({
    queryKey: ['entityDetail', selectedEntityId],
    queryFn: () => (selectedEntityId ? fetchEntityDetail(selectedEntityId) : null),
    enabled: !!selectedEntityId,
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
        {
          selector: 'node[type = "PERSON"]',
          style: {
            shape: 'ellipse',
            'background-color': '#EEF2FC',
            'border-color': '#2149B8',
          },
        },
        {
          selector: 'node[type = "PHONE"]',
          style: {
            shape: 'round-rectangle',
            'background-color': '#EFF8EA',
            'border-color': '#2A6624',
          },
        },
        {
          selector: 'node[type = "ACCOUNT"], node[type = "UPI"]',
          style: {
            shape: 'diamond',
            'background-color': '#FDF4EB',
            'border-color': '#9C5418',
          },
        },
        {
          selector: 'edge',
          style: {
            width: 'mapData(strength, 0.5, 1.0, 1.5, 3.5)',
            'line-color': '#DDD9CF',
            'target-arrow-color': '#DDD9CF',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(edge_type)',
            'font-family': 'DM Sans, sans-serif',
            'font-size': '9px',
            color: '#5C6470',
            'text-rotation': 'autorotate',
            'text-background-opacity': 0.85,
            'text-background-color': '#FFFFFF',
            'text-background-padding': '2px',
          },
        },
        {
          selector: 'edge[tier = "APPROVED"]',
          style: {
            'line-color': '#2A6624',
            'target-arrow-color': '#2A6624',
            width: 2.5,
          },
        },
        {
          selector: 'edge[tier = "VERIFIED BY CODE"]',
          style: {
            'line-color': '#2149B8',
            'target-arrow-color': '#2149B8',
          },
        },
        {
          selector: 'edge:selected',
          style: {
            'line-color': '#2149B8',
            'target-arrow-color': '#2149B8',
            width: 4,
          },
        },
      ],
      layout: {
        name: 'fcose',
        randomize: false,
        animate: false,
        fit: true,
        padding: 40,
        nodeSeparation: 80,
      } as any,
    });

    cy.on('tap', 'edge', (evt) => {
      const edge = evt.target;
      setSelectedEdgeId(edge.id());
      setActiveSidePanel('edge');
    });

    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      setSelectedEntityId(node.id());
      setActiveSidePanel('entities');
    });

    cyRef.current = cy;
  }, [graphData]);

  const filteredEntities = entitiesList?.filter((ent) =>
    entitySearch ? ent.display.toLowerCase().includes(entitySearch.toLowerCase()) || ent.type.toLowerCase().includes(entitySearch.toLowerCase()) : true
  );

  return (
    <div className="h-[calc(100vh-7rem)] flex flex-col font-sans -m-6">
      {/* Top Filter Bar */}
      <div className="h-14 border-b border-border bg-surface-raised px-6 flex items-center justify-between shrink-0 select-none">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Network className="w-4 h-4 text-cobalt" />
            <span className="font-serif font-bold text-base text-ink">Forensic Knowledge Graph</span>
          </div>
          <span className="text-border">|</span>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-ink-secondary">Strength &ge;</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={minStrength}
              onChange={(e) => setMinStrength(parseFloat(e.target.value))}
              className="w-20 cursor-pointer accent-cobalt"
            />
            <span className="font-mono text-xs">{minStrength.toFixed(2)}</span>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <button
            type="button"
            onClick={() => setActiveSidePanel('entities')}
            className={`px-3 py-1.5 rounded-lg border font-medium cursor-pointer transition-colors ${
              activeSidePanel === 'entities' ? 'bg-cobalt text-white border-cobalt' : 'bg-surface border-border text-ink-secondary'
            }`}
          >
            Entities Search
          </button>
        </div>
      </div>

      {/* Main Canvas + Folded Inspector */}
      <div className="flex-1 flex overflow-hidden relative">
        <div ref={containerRef} className="flex-1 bg-ivory cursor-grab active:cursor-grabbing" />

        {/* Side Panel (Entities Folded or Edge Inspector) */}
        <aside className="w-96 border-l border-border bg-surface-raised flex flex-col h-full shadow-lg z-10 overflow-hidden">
          {activeSidePanel === 'entities' ? (
            <div className="flex flex-col h-full p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <span className="font-bold text-xs uppercase tracking-wider text-ink flex items-center gap-1.5">
                  <Users className="w-3.5 h-3.5 text-cobalt" />
                  Entities &amp; Mentions ({entitiesList?.length || 0})
                </span>
              </div>
              <div className="flex items-center gap-2 px-2.5 py-1 text-xs border border-border rounded-lg bg-surface">
                <Search className="w-3.5 h-3.5 text-ink-tertiary" />
                <input
                  type="text"
                  placeholder="Filter entities..."
                  value={entitySearch}
                  onChange={(e) => setEntitySearch(e.target.value)}
                  className="bg-transparent border-none outline-hidden text-xs text-ink w-full"
                />
              </div>

              <div className="flex-1 overflow-y-auto space-y-1.5 divide-y divide-border/50">
                {filteredEntities?.map((ent) => (
                  <div
                    key={ent.id}
                    onClick={() => setSelectedEntityId(ent.id)}
                    className={`p-2 rounded-lg cursor-pointer text-xs transition-colors ${
                      selectedEntityId === ent.id ? 'bg-cobalt-light text-cobalt font-semibold' : 'hover:bg-ivory text-ink'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="truncate">{ent.display}</span>
                      <span className="font-mono text-2xs uppercase px-1.5 py-0.5 rounded bg-surface border border-border">
                        {ent.type}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {selectedEntityId && entityDetail && (
                <div className="p-3 bg-ivory rounded-lg border border-border text-xs space-y-2 mt-auto">
                  <div className="font-bold text-ink">{entityDetail.display}</div>
                  <div className="text-2xs text-ink-secondary">Mentions: {entityDetail.mentions?.length || 0}</div>
                  <div className="max-h-24 overflow-y-auto space-y-1 text-2xs font-mono">
                    {entityDetail.mentions?.map((m: any, idx: number) => (
                      <div key={idx} className="truncate p-1 bg-surface rounded border border-border">
                        Span: [{m.char_start}:{m.char_end}] · {m.extractor}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 space-y-4 overflow-y-auto h-full text-xs">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <span className="font-bold uppercase tracking-wider text-ink">Correlated Edge Inspector</span>
                <button type="button" onClick={() => setActiveSidePanel('entities')} className="text-ink-tertiary hover:text-ink">
                  <X className="w-4 h-4" />
                </button>
              </div>
              {edgeLoading ? (
                <div>Loading edge details...</div>
              ) : edgeDetail ? (
                <div className="space-y-3">
                  <div className="p-3 bg-surface rounded border border-border">
                    <span className="text-2xs text-ink-tertiary uppercase block">Correlation Type</span>
                    <span className="font-bold text-sm text-ink">{edgeDetail.edge_type}</span>
                  </div>
                  <div>
                    <span className="text-2xs text-ink-tertiary uppercase block mb-1">Reason / Forensic Basis</span>
                    <p className="text-ink text-xs leading-relaxed bg-surface p-2.5 rounded border border-border">
                      {edgeDetail.reason_text}
                    </p>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Evidence Strength:</span>
                    <span className="font-mono font-bold text-cobalt">{(edgeDetail.strength * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ) : (
                <div>Click an edge in the graph to inspect forensic correlation basis.</div>
              )}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
};
