import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import cytoscape from 'cytoscape';
// @ts-ignore
import fcose from 'cytoscape-fcose';
import {
  Search,
  CheckCircle2,
  XCircle,
  MessageSquare,
  Compass,
} from 'lucide-react';
import { fetchGraph, fetchEdgeDetail, reviewEdge, fetchEntities, fetchEntityDetail } from '../lib/api';
import { useAppStore } from '../lib/store';
import { WorkspaceHeader } from '../components/ui/WorkspaceHeader';
import { TierBadge } from '../components/ui/TierBadge';
import { ExhibitChip } from '../components/evidence/ExhibitChip';
import { SkeletonBlock, EmptyState } from '../components/ui/Skeleton';

try {
  cytoscape.use(fcose);
} catch {
  // Already registered
}

const BASIS_LABELS: Record<string, string> = {
  exact_identifier: 'Exact Identifier Match',
  shared_device: 'Shared Device (Deterministic)',
  time_window: 'Time-and-Place Co-occurrence',
  spatial: 'Spatial Proximity / Trajectory',
  inferred: 'Deterministic Similarity / Perceptual Hash Score',
};

const NODE_TYPES = [
  { value: 'ALL', label: 'All node types' },
  { value: 'PERSON', label: 'People' },
  { value: 'PHONE', label: 'Phones' },
  { value: 'UPI', label: 'UPI IDs' },
  { value: 'ACCOUNT', label: 'Accounts' },
  { value: 'DEVICE', label: 'Devices' },
  { value: 'IP', label: 'IP Addresses' },
  { value: 'EMAIL_ADDRESS', label: 'Email Addresses' },
  { value: 'URL', label: 'URLs' },
  { value: 'EXHIBIT', label: 'Exhibits' },
  { value: 'LOCATION', label: 'Locations' },
  { value: 'EPISODE', label: 'Episodes' },
];

export const KnowledgeGraphPage: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const selectedEntityId = useAppStore((s) => s.selectedEntityId);
  const setSelectedEntityId = useAppStore((s) => s.setSelectedEntityId);

  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [nodeTypeFilter, setNodeTypeFilter] = useState('ALL');
  const [selectedTier, setSelectedTier] = useState('ALL');
  const [minStrength, setMinStrength] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [timeFrom, setTimeFrom] = useState('');
  const [timeTo, setTimeTo] = useState('');

  const { data: graphData, isLoading } = useQuery({
    queryKey: ['graphData', nodeTypeFilter, selectedTier, minStrength, searchQuery],
    queryFn: () =>
      fetchGraph({
        type: nodeTypeFilter === 'ALL' ? undefined : nodeTypeFilter,
        tier: selectedTier === 'ALL' ? undefined : selectedTier,
        min_strength: minStrength,
      }),
  });

  const { data: edgeDetail, isLoading: edgeLoading } = useQuery({
    queryKey: ['edgeDetail', selectedEdgeId],
    queryFn: () => (selectedEdgeId ? fetchEdgeDetail(selectedEdgeId) : null),
    enabled: !!selectedEdgeId,
  });

  const { data: entityDetail } = useQuery({
    queryKey: ['entityDetail', selectedEntityId],
    queryFn: () => (selectedEntityId ? fetchEntityDetail(selectedEntityId) : null),
    enabled: !!selectedEntityId,
  });

  const { data: entitiesList } = useQuery({
    queryKey: ['entitiesList'],
    queryFn: () => fetchEntities(),
  });

  const reviewMutation = useMutation({
    mutationFn: ({ edgeId, decision }: { edgeId: string; decision: 'APPROVED' | 'REJECTED' }) =>
      reviewEdge(edgeId, decision),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['graphData'] });
      queryClient.invalidateQueries({ queryKey: ['edgeDetail', selectedEdgeId] });
      queryClient.invalidateQueries({ queryKey: ['reviewQueue'] });
    },
  });

  // Filter nodes & edges while preserving 1-hop neighborhood and matching edge reason_text
  const rawNodes = graphData?.nodes || [];
  const rawEdges = graphData?.edges || [];
  const qLower = searchQuery.trim().toLowerCase();

  const timeAllowedIds = new Set(
    rawNodes
      .filter((n: any) => {
        const d = n.data || n;
        if (timeFrom && d.ts_utc && d.ts_utc < timeFrom) return false;
        if (timeTo && d.ts_utc && d.ts_utc > timeTo) return false;
        return true;
      })
      .map((n: any) => (n.data || n).id)
  );

  let filteredNodes = rawNodes.filter((n: any) => timeAllowedIds.has((n.data || n).id));
  let filteredEdges = rawEdges.filter((e: any) => {
    const d = e.data || e;
    return timeAllowedIds.has(d.source) && timeAllowedIds.has(d.target);
  });

  if (qLower) {
    const directMatchedNodeIds = new Set(
      filteredNodes
        .filter((n: any) => {
          const d = n.data || n;
          return (
            (d.label || '').toLowerCase().includes(qLower) ||
            (d.id || '').toLowerCase().includes(qLower) ||
            (d.type || '').toLowerCase().includes(qLower)
          );
        })
        .map((n: any) => (n.data || n).id)
    );

    const matchedEdges = filteredEdges.filter((e: any) => {
      const d = e.data || e;
      return (
        directMatchedNodeIds.has(d.source) ||
        directMatchedNodeIds.has(d.target) ||
        (d.reason_text || '').toLowerCase().includes(qLower) ||
        (d.edge_type || '').toLowerCase().includes(qLower)
      );
    });

    const keepNodeIds = new Set(directMatchedNodeIds);
    matchedEdges.forEach((e: any) => {
      const d = e.data || e;
      keepNodeIds.add(d.source);
      keepNodeIds.add(d.target);
    });

    filteredNodes = filteredNodes.filter((n: any) => keepNodeIds.has((n.data || n).id));
    filteredEdges = matchedEdges;
  }

  const keyCorrelationEdges = filteredEdges
    .map((e: any) => e.data || e)
    .filter((d: any) => d.edge_type !== 'PART_OF_EPISODE' && d.edge_type !== 'OBSERVED_AT')
    .sort((a: any, b: any) => (b.strength || 0) - (a.strength || 0));

  useEffect(() => {
    if (!containerRef.current || filteredNodes.length === 0) return;
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: { nodes: filteredNodes, edges: filteredEdges },
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'font-family': 'Manrope, IBM Plex Sans, sans-serif',
            'font-size': '11px',
            'font-weight': 600,
            color: '#20283A',
            'text-valign': 'bottom',
            'text-margin-y': 6,
            width: 30,
            height: 30,
            'background-color': '#FFFFFF',
            'border-width': 1.5,
            'border-color': '#C9C6BC',
          },
        },
        {
          selector: 'node[type = "PERSON"]',
          style: { 'background-color': '#EAF2F4', 'border-color': '#316A78' },
        },
        {
          selector: 'node[type = "LOCATION"], node[type = "EPISODE"]',
          style: { shape: 'diamond', 'background-color': '#EEF2F8', 'border-color': '#5576A5' },
        },
        {
          selector: 'node:selected',
          style: { 'border-width': 3, 'border-color': '#20283A' },
        },
        {
          selector: 'edge',
          style: {
            width: 1.8,
            'line-color': '#C9C6BC',
            'target-arrow-color': '#C9C6BC',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
          },
        },
        {
          selector: 'edge[tier = "LEAD"]',
          style: { 'line-color': '#5576A5', 'target-arrow-color': '#5576A5', 'line-style': 'dashed' },
        },
        {
          selector: 'edge[tier = "VERIFIED BY CODE"]',
          style: { 'line-color': '#316A78', 'target-arrow-color': '#316A78' },
        },
        {
          selector: 'edge[tier = "APPROVED"]',
          style: { 'line-color': '#246B4F', 'target-arrow-color': '#246B4F', width: 2.5 },
        },
        {
          selector: 'edge:selected',
          style: { 'line-color': '#D95749', 'target-arrow-color': '#D95749', width: 3 },
        },
      ],
      layout: { name: 'fcose', animate: false, nodeRepulsion: 5500, idealEdgeLength: 90 } as any,
    });

    cy.on('tap', 'edge', (evt) => {
      setSelectedEdgeId(evt.target.id());
    });

    cy.on('tap', 'node', (evt) => {
      setSelectedEntityId(evt.target.id());
      setSelectedEdgeId(null);
    });

    if (selectedEntityId) {
      const target = cy.getElementById(selectedEntityId);
      if (target && target.length > 0) {
        target.select();
        cy.center(target);
      }
    }

    cyRef.current = cy;
    return () => {
      cy.destroy();
    };
  }, [graphData, nodeTypeFilter, selectedTier, minStrength, searchQuery, timeFrom, timeTo]);

  return (
    <div className="max-w-7xl mx-auto space-y-4 h-[calc(100vh-8.5rem)] flex flex-col">
      <WorkspaceHeader
        workspace="investigation"
        title="Knowledge Graph"
        subtitle="Cross-source entity and relationship network. Correlated links remain LEADs until human-approved in Review and Report."
      />

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-5 min-h-0">
        {/* Slim Left Filter Column */}
        <aside className="lg:col-span-3 editorial-card p-5 space-y-4 overflow-y-auto text-xs">
          <div className="space-y-1.5">
            <label htmlFor="graph-search" className="section-label block">Search Entities</label>
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 border border-border rounded bg-paper">
              <Search className="w-3.5 h-3.5 text-muted shrink-0" />
              <input
                id="graph-search"
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Name, phone, UPI…"
                className="w-full bg-transparent outline-none text-xs text-ink"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="graph-node-type" className="section-label block">Node Type</label>
            <select
              id="graph-node-type"
              value={nodeTypeFilter}
              onChange={(e) => setNodeTypeFilter(e.target.value)}
              className="w-full px-2.5 py-1.5 border border-border rounded bg-paper text-xs text-ink"
            >
              {NODE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="graph-tier" className="section-label block">Tier</label>
            <select
              id="graph-tier"
              value={selectedTier}
              onChange={(e) => setSelectedTier(e.target.value)}
              className="w-full px-2.5 py-1.5 border border-border rounded bg-paper text-xs text-ink"
            >
              <option value="ALL">All tiers</option>
              <option value="VERIFIED BY CODE">VERIFIED BY CODE</option>
              <option value="LEAD">LEAD</option>
              <option value="APPROVED">APPROVED</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label htmlFor="graph-strength" className="section-label">Min Strength</label>
              <span className="font-mono text-ink font-semibold">{minStrength.toFixed(2)}</span>
            </div>
            <input
              id="graph-strength"
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={minStrength}
              onChange={(e) => setMinStrength(parseFloat(e.target.value))}
              className="w-full accent-amber"
            />
          </div>

          <div className="space-y-1.5">
            <span className="section-label block">Time Range (UTC)</span>
            <input
              type="date"
              value={timeFrom}
              onChange={(e) => setTimeFrom(e.target.value)}
              aria-label="Start date"
              className="w-full px-2 py-1 border border-border rounded bg-paper text-xs font-mono"
            />
            <input
              type="date"
              value={timeTo}
              onChange={(e) => setTimeTo(e.target.value)}
              aria-label="End date"
              className="w-full px-2 py-1 border border-border rounded bg-paper text-xs font-mono"
            />
          </div>

          <div className="pt-2 border-t border-border text-[11px] text-muted font-mono">
            Showing {filteredNodes.length} nodes · {filteredEdges.length} links
          </div>
        </aside>

        {/* Center Full-Height Analytical Canvas */}
        <div className="lg:col-span-6 forensic-grid-bg border border-border rounded-2xl shadow-card relative overflow-hidden min-h-[380px]">
          {isLoading ? (
            <SkeletonBlock className="h-full w-full" />
          ) : filteredNodes.length === 0 ? (
            <div className="h-full flex items-center justify-center p-6">
              <EmptyState
                title="No graph nodes to display"
                description="Upload exhibits and click Run Pipeline in the top bar to build the cross-source knowledge graph."
              />
            </div>
          ) : (
            <div ref={containerRef} className="w-full h-full" />
          )}
        </div>

        {/* Right Detail Panel ("Why this link" / Node Profile) */}
        <aside className="lg:col-span-3 editorial-card p-5 overflow-y-auto space-y-4 text-xs">
          {selectedEdgeId ? (
            edgeLoading ? (
              <SkeletonBlock className="h-40" />
            ) : edgeDetail ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <span className="section-label">Why This Link</span>
                  <TierBadge tier={edgeDetail.tier} size="sm" />
                </div>
                <div className="font-mono text-ink font-semibold">
                  {edgeDetail.src} → {edgeDetail.dst}
                </div>
                <div className="p-2.5 bg-paper border border-border rounded space-y-1.5">
                  <div className="text-[11px] text-muted uppercase font-semibold">
                    Basis: {BASIS_LABELS[edgeDetail.basis] || edgeDetail.basis}
                  </div>
                  <p className="text-ink leading-relaxed">{edgeDetail.reason_text}</p>
                  <div className="font-mono text-[11px] text-muted pt-1 border-t border-border">
                    Deterministic strength: {Math.round((edgeDetail.strength || 0) * 100)}% (feature-derived, never model-stated)
                  </div>
                </div>
                <div className="space-y-1.5">
                  <span className="section-label block">Source Chips</span>
                  <div className="flex flex-wrap gap-1.5">
                    {(edgeDetail.supporting_events || []).map((ev: any) => (
                      <ExhibitChip key={ev.id} exhibitId={ev.exhibit_id} eventId={ev.id} />
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2 pt-2 border-t border-border">
                  <button
                    type="button"
                    onClick={() => reviewMutation.mutate({ edgeId: edgeDetail.id, decision: 'APPROVED' })}
                    className="flex-1 inline-flex items-center justify-center gap-1 py-1.5 rounded bg-approved text-white font-semibold cursor-pointer"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Approve</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => reviewMutation.mutate({ edgeId: edgeDetail.id, decision: 'REJECTED' })}
                    className="flex-1 inline-flex items-center justify-center gap-1 py-1.5 rounded border border-vermilion text-vermilion font-semibold cursor-pointer"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    <span>Reject</span>
                  </button>
                </div>
              </div>
            ) : null
          ) : entityDetail ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <span className="section-label">{entityDetail.type}</span>
                <span className="font-mono text-[11px] text-muted">{entityDetail.mentions?.length || 0} mentions</span>
              </div>
              <h3 className="font-serif text-base font-bold text-ink">{entityDetail.display}</h3>
              <div className="flex flex-col gap-2">
                <button
                  type="button"
                  onClick={() => navigate(`/assistant?focus=${encodeURIComponent(entityDetail.display)}`)}
                  className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-md bg-[#316A78] hover:bg-[#24525D] text-white font-semibold cursor-pointer transition-colors"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Ask about this</span>
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/reconstruction')}
                  className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-md border border-[#C9C6BC] bg-[#F5F4F0] hover:bg-[#ECEAE3] text-[#20283A] font-medium cursor-pointer transition-colors"
                >
                  <Compass className="w-3.5 h-3.5 text-[#5576A5]" />
                  <span>Show on reconstruction</span>
                </button>
              </div>
              <div className="space-y-1.5 pt-2 border-t border-border">
                <span className="section-label block">Recent Mentions</span>
                {(entityDetail.mentions || []).slice(0, 6).map((m: any) => (
                  <div key={m.id} className="p-2 bg-paper border border-border rounded space-y-1">
                    <div className="flex items-center justify-between">
                      {m.exhibit_id && <ExhibitChip exhibitId={m.exhibit_id} eventId={m.event_id} />}
                      <TierBadge tier={m.tier} size="sm" />
                    </div>
                    <p className="text-[11px] text-muted truncate">{m.text}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <span className="section-label block">Inspector</span>
              <p className="text-muted">
                Click any node to inspect mentions or ask the Assistant. Click any edge (or select a correlated link below) for the &ldquo;Why this link&rdquo; breakdown.
              </p>
              {keyCorrelationEdges.length > 0 && (
                <div className="space-y-1.5 pt-2 border-t border-border">
                  <span className="section-label block">
                    {qLower ? 'Matching Correlation Links' : 'Cross-Source Correlation Links'} ({keyCorrelationEdges.length})
                  </span>
                  <div className="space-y-1 max-h-56 overflow-y-auto">
                    {keyCorrelationEdges.slice(0, 15).map((edge: any) => (
                      <button
                        key={edge.id}
                        type="button"
                        onClick={() => setSelectedEdgeId(edge.id)}
                        className="w-full text-left p-2 rounded border border-border bg-paper hover:border-amber cursor-pointer space-y-0.5"
                      >
                        <div className="flex items-center justify-between gap-1 font-mono text-[10px]">
                          <span className="font-bold text-amber">{edge.edge_type}</span>
                          <span className="text-muted">{Math.round((edge.strength || 0) * 100)}%</span>
                        </div>
                        <div className="text-[11px] text-ink leading-snug">{edge.reason_text}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {entitiesList && entitiesList.length > 0 && (
                <div className="space-y-1 pt-2 border-t border-border">
                  <span className="section-label block">Quick Select Entity</span>
                  {entitiesList.slice(0, 8).map((ent) => (
                    <button
                      key={ent.id}
                      type="button"
                      onClick={() => setSelectedEntityId(ent.id)}
                      className="w-full text-left px-2 py-1.5 rounded hover:bg-paper-subtle flex items-center justify-between cursor-pointer"
                    >
                      <span className="font-medium text-ink truncate">{ent.display}</span>
                      <span className="font-mono text-[10px] text-muted">{ent.type}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
};
