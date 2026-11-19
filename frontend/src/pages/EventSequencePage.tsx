import React, { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { DataSet } from 'vis-data';
import { Timeline } from 'vis-timeline/standalone';
import 'vis-timeline/styles/vis-timeline-graph2d.css';
import {
  Clock,
  Filter,
  Search,
  MapPin,
  AlertTriangle,
  Layers,
  FileText,
  Radio,
  Compass,
  ArrowRight,
} from 'lucide-react';
import { fetchEvents, fetchAnomalies } from '../lib/api';
import { useAppStore } from '../lib/store';
import { ExhibitChip } from '../components/evidence/ExhibitChip';
import { ForensicEvent } from '../types';

export const EventSequencePage: React.FC = () => {
  const timelineRef = useRef<HTMLDivElement>(null);
  const timelineInstance = useRef<Timeline | null>(null);

  const openSourceViewer = useAppStore((state) => state.openSourceViewer);

  // Single clean grouping toggle: 'source' vs 'actor'
  const [laneMode, setLaneMode] = useState<'source' | 'actor'>('source');
  const [filterSource, setFilterSource] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null);

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

  // Extract unique locations for the spatial side list
  const locationsMap: Record<string, number> = {};
  events?.forEach((ev) => {
    if (ev.location_id) {
      locationsMap[ev.location_id] = (locationsMap[ev.location_id] || 0) + 1;
    }
  });

  // Filter events by text search or location
  const filteredEvents = events?.filter((ev) => {
    if (selectedLocation && ev.location_id !== selectedLocation) return false;
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      (ev.text && ev.text.toLowerCase().includes(q)) ||
      (ev.actor && ev.actor.toLowerCase().includes(q)) ||
      (ev.kind && ev.kind.toLowerCase().includes(q)) ||
      (ev.counterparty && ev.counterparty.toLowerCase().includes(q))
    );
  });

  // Initialize and update vis-timeline
  useEffect(() => {
    if (!timelineRef.current || !filteredEvents) return;

    // Define Groups
    let groups: any[] = [];
    if (laneMode === 'source') {
      groups = [
        { id: 'whatsapp', content: 'WhatsApp Advisory Chat' },
        { id: 'bank_pdf', content: 'Bank Statement (Meera)' },
        { id: 'bank_csv', content: 'Mule Funnel (HDFC/ICICI)' },
        { id: 'calllog', content: 'CDR Mobile Handset' },
        { id: 'image', content: 'Screenshots & Media' },
      ];
    } else {
      const actors = Array.from(new Set(filteredEvents.map((e) => e.actor || 'System / Network')));
      groups = actors.map((act) => ({ id: act, content: act }));
    }

    // Define Items
    const items = new DataSet(
      filteredEvents.map((ev) => {
        const isAnomaly = anomalies?.some((a) => a.event_ids?.includes(ev.id));
        let itemClass = 'timeline-chip-default';

        if (isAnomaly) {
          itemClass = 'timeline-chip-anomaly';
        } else if (ev.source_type === 'whatsapp') {
          itemClass = 'timeline-chip-whatsapp';
        } else if (ev.source_type === 'bank_pdf' || ev.source_type === 'bank_csv') {
          itemClass = 'timeline-chip-bank';
        } else if (ev.source_type === 'calllog') {
          itemClass = 'timeline-chip-call';
        }

        const label = ev.amount ? `₹${ev.amount.toLocaleString()}` : ev.actor || ev.kind;

        return {
          id: ev.id,
          group: laneMode === 'source' ? ev.source_type : ev.actor || 'System / Network',
          start: new Date(ev.ts_utc),
          content: `<div class="timeline-event-chip ${itemClass}">
                      <span class="chip-dot"></span>
                      <span class="chip-text truncate">${label}</span>
                    </div>`,
          title: `${ev.ts_original} (${ev.tz_assumed})\n${ev.actor || 'System'}: ${ev.text || ev.kind}`,
        };
      })
    );

    const options = {
      stack: true,
      zoomMin: 1000 * 60 * 60, // 1 hour min zoom
      zoomMax: 1000 * 60 * 60 * 24 * 30, // 30 days max zoom
      orientation: 'top',
      maxHeight: '400px',
      margin: {
        item: 10,
        axis: 5,
      },
      showCurrentTime: false,
    };

    if (timelineInstance.current) {
      timelineInstance.current.destroy();
    }

    const tl = new Timeline(timelineRef.current, items, groups, options);
    tl.on('select', (properties) => {
      if (properties.items && properties.items.length > 0) {
        const selectedId = properties.items[0];
        openSourceViewer(selectedId);
      }
    });

    timelineInstance.current = tl;

    return () => {
      if (timelineInstance.current) {
        timelineInstance.current.destroy();
        timelineInstance.current = null;
      }
    };
  }, [filteredEvents, laneMode, anomalies]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16 font-sans">
      {/* Editorial Header */}
      <section className="space-y-2 border-b border-border pb-6">
        <div className="flex items-center gap-2">
          <span className="font-sans text-xs font-bold uppercase tracking-wider text-cobalt bg-cobalt-light px-2.5 py-1 rounded-full">
            Crime Scene Reconstruction
          </span>
          <span className="text-ink-tertiary">·</span>
          <span className="font-sans text-xs text-ink-secondary">
            Cross-Source Temporal Alignment
          </span>
        </div>

        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl sm:text-4xl font-bold text-ink tracking-tight">
              Automated Event-Sequence Generator
            </h1>
            <p className="text-sm text-ink-secondary mt-1 max-w-2xl leading-relaxed">
              Unified chronological timeline synchronising multi-device WhatsApp messages, bank debits/credits, cell tower handshakes, and image timestamps.
            </p>
          </div>

          {/* Grouping Toggle */}
          <div className="flex items-center gap-2 bg-surface p-1 rounded-lg border border-border text-xs self-start md:self-auto">
            <span className="px-2 font-medium text-ink-secondary">Group by:</span>
            <button
              type="button"
              onClick={() => setLaneMode('source')}
              className={`px-3 py-1 rounded-md font-semibold transition-colors cursor-pointer ${
                laneMode === 'source'
                  ? 'bg-cobalt text-white shadow-xs'
                  : 'text-ink-secondary hover:text-ink'
              }`}
            >
              Source Lane
            </button>
            <button
              type="button"
              onClick={() => setLaneMode('actor')}
              className={`px-3 py-1 rounded-md font-semibold transition-colors cursor-pointer ${
                laneMode === 'actor'
                  ? 'bg-cobalt text-white shadow-xs'
                  : 'text-ink-secondary hover:text-ink'
              }`}
            >
              Actor Lane
            </button>
          </div>
        </div>
      </section>

      {/* Vis Timeline Container */}
      <div className="bg-surface-raised rounded-xl border border-border p-4 shadow-xs">
        <div className="flex items-center justify-between pb-3 mb-2 border-b border-border text-xs">
          <div className="flex items-center gap-2">
            <Clock className="w-3.5 h-3.5 text-cobalt" />
            <span className="font-sans font-bold uppercase tracking-wider text-ink">
              Multi-Source Synchronized Canvas
            </span>
          </div>
          <span className="text-2xs font-mono text-ink-tertiary">
            CLICK ANY EVENT CHIP TO OPEN EXACT SOURCE
          </span>
        </div>
        <div ref={timelineRef} className="h-80 w-full" />
      </div>

      {/* Split Section: Chronological List & Spatial Thread */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Chronological Feed */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-sans text-xs font-bold uppercase tracking-wider text-ink">
                Chronological Event Sequence ({filteredEvents?.length || 0})
              </span>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 px-2.5 py-1 text-xs border border-border rounded-lg bg-surface">
                <Search className="w-3.5 h-3.5 text-ink-tertiary" />
                <input
                  type="text"
                  placeholder="Filter events..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-transparent border-none outline-hidden text-xs text-ink w-32 focus:w-44 transition-all"
                />
              </div>
            </div>
          </div>

          <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
            {eventsLoading ? (
              <div className="p-8 text-center text-xs text-ink-secondary">Loading forensic events...</div>
            ) : filteredEvents?.length === 0 ? (
              <div className="p-8 text-center text-xs text-ink-secondary">No events match filter.</div>
            ) : (
              filteredEvents?.map((ev) => {
                const isAnomaly = anomalies?.some((a) => a.event_ids?.includes(ev.id));
                return (
                  <div
                    key={ev.id}
                    onClick={() => openSourceViewer(ev.id)}
                    className={`p-3.5 rounded-xl border bg-surface-raised hover:border-cobalt cursor-pointer transition-all text-xs space-y-1.5 ${
                      isAnomaly ? 'border-tomato/50 bg-tomato-light/20' : 'border-border'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-2xs font-bold text-ink-secondary">
                          {ev.ts_original}
                        </span>
                        <span className="text-2xs font-mono text-ink-tertiary">
                          ({ev.tz_assumed})
                        </span>
                      </div>
                      <span className="font-mono text-2xs uppercase px-2 py-0.5 rounded-full bg-ivory border border-border font-semibold">
                        {ev.source_type}
                      </span>
                    </div>

                    <div className="font-medium text-ink text-xs leading-relaxed">
                      {ev.text || `${ev.kind} transaction`}
                    </div>

                    <div className="flex items-center justify-between text-2xs text-ink-secondary pt-1 border-t border-border/60">
                      <span>Actor: <strong className="text-ink">{ev.actor || 'Unknown'}</strong></span>
                      {ev.amount && (
                        <span className="font-mono font-bold text-cobalt">
                          ₹{ev.amount.toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Col: Spatial Locations & Anomalies */}
        <div className="space-y-5">
          {/* Timeline Anomalies */}
          <div className="bg-surface-raised rounded-xl border border-border p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-border pb-2">
              <span className="font-bold text-xs uppercase tracking-wider text-ink flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-tomato" />
                Forensic Anomalies ({anomalies?.length || 0})
              </span>
            </div>
            <div className="space-y-2 text-xs">
              {anomalies?.map((anom) => (
                <div key={anom.id} className="p-2.5 rounded-lg border border-tomato/30 bg-tomato-light text-tomato space-y-1">
                  <div className="font-bold text-2xs uppercase">{anom.kind}</div>
                  <p className="text-2xs leading-normal">{anom.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Spatial Threads */}
          <div className="bg-surface-raised rounded-xl border border-border p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-border pb-2">
              <span className="font-bold text-xs uppercase tracking-wider text-ink flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-cobalt" />
                Cell Tower Locations
              </span>
              {selectedLocation && (
                <button
                  type="button"
                  onClick={() => setSelectedLocation(null)}
                  className="text-2xs text-cobalt font-semibold hover:underline"
                >
                  Clear
                </button>
              )}
            </div>
            <div className="space-y-1.5">
              {Object.entries(locationsMap).map(([loc, count]) => (
                <button
                  key={loc}
                  type="button"
                  onClick={() => setSelectedLocation(selectedLocation === loc ? null : loc)}
                  className={`w-full text-left p-2 rounded-lg text-xs flex items-center justify-between transition-colors ${
                    selectedLocation === loc ? 'bg-cobalt text-white font-semibold' : 'hover:bg-ivory text-ink'
                  }`}
                >
                  <span className="truncate">{loc}</span>
                  <span className="font-mono text-2xs px-1.5 py-0.5 rounded bg-surface border border-border">
                    {count} events
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
