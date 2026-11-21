import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { DataSet } from 'vis-data';
import { Timeline } from 'vis-timeline/standalone';
import 'vis-timeline/styles/vis-timeline-graph2d.css';
import {
  Search,
  MapPin,
  AlertTriangle,
  Play,
  SkipBack,
  SkipForward,
  RefreshCw,
} from 'lucide-react';
import { fetchEvents, fetchAnomalies, fetchSequence, generateSequence, fetchScene, fetchSceneReplay } from '../lib/api';
import { useAppStore } from '../lib/store';
import { WorkspaceHeader } from '../components/ui/WorkspaceHeader';
import { ExhibitChip } from '../components/evidence/ExhibitChip';
import { SkeletonBlock, EmptyState } from '../components/ui/Skeleton';

export const ReconstructionPage: React.FC = () => {
  const timelineRef = useRef<HTMLDivElement>(null);
  const timelineInstance = useRef<Timeline | null>(null);

  const openSourceViewer = useAppStore((s) => s.openSourceViewer);
  const selectedEventId = useAppStore((s) => s.selectedEventId);
  const setSelectedEventId = useAppStore((s) => s.setSelectedEventId);
  const selectedLocationId = useAppStore((s) => s.selectedLocationId);
  const setSelectedLocationId = useAppStore((s) => s.setSelectedLocationId);

  const [laneMode, setLaneMode] = useState<'source' | 'actor'>('source');
  const [filterSource, setFilterSource] = useState('ALL');
  const [filterActor, setFilterActor] = useState('ALL');
  const [filterDate, setFilterDate] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEpisodeId, setSelectedEpisodeId] = useState<string | undefined>(undefined);
  const [replayIdx, setReplayIdx] = useState(0);

  const { data: events, isLoading: eventsLoading } = useQuery({
    queryKey: ['eventsList', filterSource],
    queryFn: () =>
      fetchEvents({
        source: filterSource === 'ALL' ? undefined : filterSource,
        limit: 1000,
      }),
  });

  const { data: anomalies } = useQuery({
    queryKey: ['anomaliesList'],
    queryFn: () => fetchAnomalies(),
  });

  const { data: sequenceData, refetch: refetchSequence } = useQuery({
    queryKey: ['eventSequence'],
    queryFn: fetchSequence,
  });

  const { data: sceneData } = useQuery({
    queryKey: ['crimeScene', selectedEpisodeId],
    queryFn: () => fetchScene(selectedEpisodeId),
  });

  const { data: replayData } = useQuery({
    queryKey: ['crimeSceneReplay', selectedEpisodeId],
    queryFn: () => fetchSceneReplay(selectedEpisodeId),
  });

  const actorsList = useMemo(() => {
    const s = new Set<string>();
    (events || []).forEach((ev) => {
      if (ev.actor) s.add(ev.actor);
    });
    return Array.from(s).sort();
  }, [events]);

  const filteredEvents = useMemo(() => {
    return (events || []).filter((ev) => {
      if (filterActor !== 'ALL' && ev.actor !== filterActor) return false;
      if (filterDate && !(ev.ts_utc || '').startsWith(filterDate)) return false;
      if (selectedLocationId && ev.location_id !== selectedLocationId) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const hay = `${ev.text || ''} ${ev.actor || ''} ${ev.counterparty || ''} ${ev.kind || ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [events, filterActor, filterDate, selectedLocationId, searchQuery]);

  const replaySteps = replayData?.steps || [];
  const currentStep = replaySteps[replayIdx] || null;

  useEffect(() => {
    setReplayIdx(0);
  }, [selectedEpisodeId, replaySteps.length]);

  // Sync timeline selection with replay step
  useEffect(() => {
    if (currentStep?.event_id && timelineInstance.current) {
      try {
        timelineInstance.current.setSelection([currentStep.event_id]);
      } catch {
        // ignore if filtered out
      }
    }
  }, [currentStep?.event_id]);

  // Build vis-timeline
  useEffect(() => {
    if (!timelineRef.current || filteredEvents.length === 0) return;

    const groups =
      laneMode === 'source'
        ? [
            { id: 'whatsapp', content: 'WhatsApp' },
            { id: 'social_media', content: 'Social Media' },
            { id: 'bank_pdf', content: 'Bank PDF' },
            { id: 'bank_csv', content: 'Bank CSV' },
            { id: 'calllog', content: 'Mobile / CDR' },
            { id: 'cloud', content: 'Cloud' },
            { id: 'email', content: 'Email' },
            { id: 'network_log', content: 'Network' },
            { id: 'image', content: 'Media / CCTV' },
          ]
        : Array.from(new Set(filteredEvents.map((e) => e.actor || 'System'))).map((a) => ({
            id: a,
            content: a,
          }));

    const items = new DataSet<any>(
      filteredEvents.map((ev) => {
        const isAnomaly = anomalies?.some((a) => a.event_ids?.includes(ev.id));
        const label = ev.amount ? `₹${ev.amount.toLocaleString()}` : ev.actor || ev.kind;
        return {
          id: ev.id,
          group: laneMode === 'source' ? ev.source_type : ev.actor || 'System',
          start: new Date(ev.ts_utc),
          content: `<span class="text-[11px] font-mono px-1">${label}</span>`,
          className: isAnomaly ? 'bg-vermilion-light border-vermilion text-vermilion' : 'bg-paper border-border-strong text-ink',
          title: `${ev.ts_utc} | ${ev.text || ev.kind}`,
        };
      })
    );

    if (timelineInstance.current) {
      timelineInstance.current.destroy();
    }

    const tl = new Timeline(timelineRef.current, items, new DataSet(groups), {
      stack: true,
      height: '250px',
      margin: { item: 8, axis: 12 },
      zoomMin: 1000 * 60 * 5,
    });

    tl.on('select', (props) => {
      if (props.items?.length) {
        const id = props.items[0];
        setSelectedEventId(id);
        openSourceViewer(id);
      }
    });

    timelineInstance.current = tl;
    return () => {
      tl.destroy();
    };
  }, [filteredEvents, laneMode, anomalies]);

  // Plain coordinate canvas projection for Locations (NO map tiles, NO country/state outlines)
  const observations = sceneData?.spatial_observations || [];
  const projectedPoints = useMemo(() => {
    const withCoords = observations.filter((o: any) => typeof o.lat === 'number' && typeof o.lon === 'number');
    if (withCoords.length === 0) return [];
    const lats = withCoords.map((o: any) => o.lat);
    const lons = withCoords.map((o: any) => o.lon);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);
    const padLat = Math.max(0.01, (maxLat - minLat) * 0.15);
    const padLon = Math.max(0.01, (maxLon - minLon) * 0.15);

    return withCoords.map((o: any, idx: number) => {
      const x = 40 + ((o.lon - (minLon - padLon)) / ((maxLon + padLon) - (minLon - padLon))) * 320;
      const y = 200 - ((o.lat - (minLat - padLat)) / ((maxLat + padLat) - (minLat - padLat))) * 160;
      return { ...o, x, y, idx };
    });
  }, [observations]);

  const impossibleTravelIds = new Set(
    (sceneData?.anomalies || [])
      .filter((a: any) => a.kind === 'impossible_travel')
      .flatMap((a: any) => a.event_ids || [])
  );

  return (
    <div className="max-w-7xl mx-auto space-y-5 pb-12">
      <WorkspaceHeader
        workspace="investigation"
        title="Crime Scene Reconstruction"
        subtitle="Synchronized event sequence, offline spatial coordinate canvas, and step-by-step scene replay."
        actions={
          <div className="flex items-center gap-2">
            <div className="inline-flex rounded border border-border bg-panel p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setLaneMode('source')}
                className={`px-2.5 py-1 rounded cursor-pointer ${laneMode === 'source' ? 'bg-amber text-white font-semibold' : 'text-muted'}`}
              >
                By Source
              </button>
              <button
                type="button"
                onClick={() => setLaneMode('actor')}
                className={`px-2.5 py-1 rounded cursor-pointer ${laneMode === 'actor' ? 'bg-amber text-white font-semibold' : 'text-muted'}`}
              >
                By Actor
              </button>
            </div>
            <button
              type="button"
              onClick={async () => {
                await generateSequence();
                refetchSequence();
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-border bg-panel text-xs font-medium text-ink hover:border-amber cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5 text-amber" />
              <span>Regenerate Sequence</span>
            </button>
          </div>
        }
      />

      {/* Filters Bar */}
      <div className="bg-panel border border-border rounded p-3 flex flex-wrap items-center gap-3 text-xs">
        <div className="flex items-center gap-1.5 px-2.5 py-1 border border-border rounded bg-paper flex-1 min-w-[180px]">
          <Search className="w-3.5 h-3.5 text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter text, account, device…"
            className="bg-transparent outline-none w-full text-ink"
          />
        </div>
        <select
          value={filterSource}
          onChange={(e) => setFilterSource(e.target.value)}
          aria-label="Filter by source"
          className="px-2.5 py-1 border border-border rounded bg-paper text-ink"
        >
          <option value="ALL">All sources</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="social_media">Social Media</option>
          <option value="calllog">Mobile / CDR</option>
          <option value="bank_pdf">Bank PDF</option>
          <option value="bank_csv">Bank CSV</option>
          <option value="cloud">Cloud</option>
          <option value="email">Email</option>
          <option value="network_log">Network</option>
          <option value="image">Media / CCTV</option>
        </select>
        <select
          value={filterActor}
          onChange={(e) => setFilterActor(e.target.value)}
          aria-label="Filter by person or actor"
          className="px-2.5 py-1 border border-border rounded bg-paper text-ink"
        >
          <option value="ALL">All persons / actors</option>
          {actorsList.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        <input
          type="date"
          value={filterDate}
          onChange={(e) => setFilterDate(e.target.value)}
          aria-label="Filter by date"
          className="px-2.5 py-1 border border-border rounded bg-paper font-mono text-ink"
        />
        {selectedLocationId && (
          <button
            type="button"
            onClick={() => setSelectedLocationId(null)}
            className="px-2 py-1 rounded bg-amber-light border border-amber-border text-amber font-mono cursor-pointer"
          >
            Location: {selectedLocationId} ×
          </button>
        )}
      </div>

      {/* AREA 1: EVENT SEQUENCE TIMELINE */}
      <section className="bg-panel border border-border rounded p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <span className="section-label">1. Event Sequence Timeline ({filteredEvents.length} events)</span>
          <span className="font-mono text-[11px] text-muted">Click any event to open Source Viewer</span>
        </div>
        {eventsLoading ? (
          <SkeletonBlock className="h-56" />
        ) : filteredEvents.length === 0 ? (
          <EmptyState
            title="No events in timeline"
            description="Upload exhibits and run the pipeline to populate the cross-source event sequence."
          />
        ) : (
          <div ref={timelineRef} className="w-full" />
        )}
      </section>

      {/* AREA 2 & 3: LOCATIONS CANVAS + SCENE REPLAY */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* AREA 2: LOCATIONS PANEL (Plain offline coordinate canvas) */}
        <section className="lg:col-span-5 bg-panel border border-border rounded p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-border pb-2">
            <span className="section-label flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-amber" />
              2. Locations (Offline Coordinate Canvas)
            </span>
            <span className="font-mono text-[11px] text-muted">{projectedPoints.length} plotted</span>
          </div>

          {projectedPoints.length === 0 ? (
            <EmptyState
              title="No spatial coordinates"
              description="Spatial observations with lat/lon from CDR towers, cloud logs, or EXIF will appear on this coordinate grid."
            />
          ) : (
            <svg viewBox="0 0 400 230" className="w-full h-56 bg-paper border border-border rounded" role="img" aria-label="Spatial observations coordinate plot">
              {/* Grid lines only (no map tiles or outlines) */}
              {[60, 120, 180].map((y) => (
                <line key={`hy-${y}`} x1="20" y1={y} x2="380" y2={y} stroke="#E8D9CC" strokeDasharray="3 3" />
              ))}
              {[100, 200, 300].map((x) => (
                <line key={`vx-${x}`} x1={x} y1="20" x2={x} y2="210" stroke="#E8D9CC" strokeDasharray="3 3" />
              ))}
              {/* Movement lines */}
              {projectedPoints.map((pt: any, i: number) => {
                if (i === 0) return null;
                const prev = projectedPoints[i - 1];
                const isImpossible = impossibleTravelIds.has(pt.source_event_id);
                return (
                  <line
                    key={`seg-${i}`}
                    x1={prev.x}
                    y1={prev.y}
                    x2={pt.x}
                    y2={pt.y}
                    stroke={isImpossible ? '#DB4A2B' : '#C97B1A'}
                    strokeWidth={isImpossible ? 2 : 1.5}
                    strokeDasharray={isImpossible ? '4 2' : undefined}
                  />
                );
              })}
              {/* Points + Accuracy circles */}
              {projectedPoints.map((pt: any, i: number) => {
                const isActive =
                  currentStep?.location && pt.place_name && currentStep.location.includes(pt.place_name);
                const isImpossible = impossibleTravelIds.has(pt.source_event_id);
                return (
                  <g
                    key={`pt-${i}`}
                    onClick={() => setSelectedLocationId(pt.place_name || pt.location_id)}
                    className="cursor-pointer"
                  >
                    <circle
                      cx={pt.x}
                      cy={pt.y}
                      r={Math.min(26, Math.max(8, (pt.accuracy_m || 200) / 50))}
                      fill={isImpossible ? '#DB4A2B' : '#C97B1A'}
                      fillOpacity={0.14}
                      stroke={isImpossible ? '#DB4A2B' : '#C97B1A'}
                      strokeOpacity={0.45}
                    />
                    <circle
                      cx={pt.x}
                      cy={pt.y}
                      r={isActive ? 6 : 4}
                      fill={isImpossible ? '#DB4A2B' : isActive ? '#2E5E6E' : '#C97B1A'}
                    />
                    <text x={pt.x + 7} y={pt.y + 3} fontSize="9" fill="#2B1B17" fontFamily="IBM Plex Mono, monospace">
                      {pt.place_name || pt.location_id || `Pt ${i + 1}`}
                    </text>
                  </g>
                );
              })}
            </svg>
          )}
        </section>

        {/* AREA 3: SCENE REPLAY CONTROL */}
        <section className="lg:col-span-7 bg-panel border border-border rounded p-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-2">
            <span className="section-label flex items-center gap-1.5">
              <Play className="w-3.5 h-3.5 text-amber" />
              3. Scene Replay ({replaySteps.length} steps)
            </span>
            <select
              value={selectedEpisodeId || ''}
              onChange={(e) => setSelectedEpisodeId(e.target.value || undefined)}
              aria-label="Select episode"
              className="text-xs border border-border rounded px-2 py-1 bg-paper text-ink"
            >
              <option value="">All episodes (full window)</option>
              {(sequenceData?.episodes || []).map((ep: any) => (
                <option key={ep.id} value={ep.id}>{ep.title}</option>
              ))}
            </select>
          </div>

          {replaySteps.length === 0 ? (
            <EmptyState
              title="No replay steps available"
              description="Generate the event sequence to step through correlated episodes."
            />
          ) : (
            <div className="space-y-3">
              {/* Scrubber Controls */}
              <div className="flex items-center gap-3 bg-paper border border-border rounded p-2.5">
                <button
                  type="button"
                  onClick={() => setReplayIdx((i) => Math.max(0, i - 1))}
                  disabled={replayIdx === 0}
                  aria-label="Previous step"
                  className="p-1.5 rounded border border-border bg-panel disabled:opacity-40 cursor-pointer"
                >
                  <SkipBack className="w-3.5 h-3.5" />
                </button>
                <input
                  type="range"
                  min={0}
                  max={Math.max(0, replaySteps.length - 1)}
                  value={replayIdx}
                  onChange={(e) => setReplayIdx(Number(e.target.value))}
                  aria-label="Replay step scrubber"
                  className="flex-1 accent-amber"
                />
                <button
                  type="button"
                  onClick={() => setReplayIdx((i) => Math.min(replaySteps.length - 1, i + 1))}
                  disabled={replayIdx >= replaySteps.length - 1}
                  aria-label="Next step"
                  className="p-1.5 rounded border border-border bg-panel disabled:opacity-40 cursor-pointer"
                >
                  <SkipForward className="w-3.5 h-3.5" />
                </button>
                <span className="font-mono text-xs text-muted">
                  Step {replayIdx + 1} / {replaySteps.length}
                </span>
              </div>

              {/* Active Step Detail Card */}
              {currentStep && (
                <div className="p-4 bg-paper border border-amber-border rounded space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-semibold text-ink">{currentStep.ts_utc}</span>
                    {currentStep.exhibit_id && (
                      <ExhibitChip exhibitId={currentStep.exhibit_id} eventId={currentStep.event_id} />
                    )}
                  </div>
                  <div className="grid grid-cols-3 gap-2 pt-1">
                    <div>
                      <span className="section-label block">Who</span>
                      <span className="font-semibold text-ink">{currentStep.actor || '—'}</span>
                    </div>
                    <div>
                      <span className="section-label block">Device / Source</span>
                      <span className="font-mono text-ink">{currentStep.source_type || '—'}</span>
                    </div>
                    <div>
                      <span className="section-label block">Where</span>
                      <span className="font-medium text-ink">{currentStep.location || 'not established'}</span>
                    </div>
                  </div>
                  <p className="text-ink pt-1 border-t border-border">{currentStep.summary || currentStep.text}</p>
                </div>
              )}
            </div>
          )}
        </section>
      </div>

      {/* Synced Event & Episode List (with Original vs Corrected Time) */}
      <section className="bg-panel border border-border rounded p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <span className="section-label">Chronological Steps &amp; Clock Offsets</span>
          <span className="font-mono text-[11px] text-muted">Showing up to 50 matching events</span>
        </div>
        {filteredEvents.length === 0 ? (
          <EmptyState title="No matching events" description="Adjust filters above to view events." />
        ) : (
          <div className="divide-y divide-border max-h-80 overflow-y-auto text-xs">
            {filteredEvents.slice(0, 50).map((ev: any) => {
              const hasOffset = ev.clock_offset_seconds && ev.clock_offset_seconds !== 0;
              const isSelected = selectedEventId === ev.id;
              return (
                <div
                  key={ev.id}
                  onClick={() => {
                    setSelectedEventId(ev.id);
                    openSourceViewer(ev.id);
                  }}
                  className={`py-2.5 px-3 flex items-center justify-between gap-4 cursor-pointer transition-colors duration-150 ${
                    isSelected ? 'bg-amber-light' : 'hover:bg-paper-subtle'
                  }`}
                >
                  <div className="space-y-0.5 min-w-0">
                    <div className="flex items-center gap-2 font-mono text-[11px]">
                      <span className="font-semibold text-ink">{ev.ts_utc?.slice(0, 19).replace('T', ' ')}</span>
                      {hasOffset && (
                        <span className="text-amber" title="Original uncorrected timestamp">
                          (orig: {ev.ts_original}, offset {ev.clock_offset_seconds}s)
                        </span>
                      )}
                      <span className="text-muted">· {ev.actor || ev.kind}</span>
                    </div>
                    <p className="text-ink truncate">{ev.text || ev.kind}</p>
                  </div>
                  <div className="shrink-0">
                    {ev.exhibit_id && <ExhibitChip exhibitId={ev.exhibit_id} eventId={ev.id} />}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
};
