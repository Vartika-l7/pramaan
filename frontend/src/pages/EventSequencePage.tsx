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

        return {
          id: ev.id,
          group: laneMode === 'source' ? ev.source_type : ev.actor || 'System / Network',
          start: new Date(ev.ts_utc),
          content: `<div class="truncate font-sans text-xs">${ev.kind}: ${ev.text?.slice(0, 36) || ev.actor || ''}</div>`,
          className: itemClass,
        };
      })
    );

    // Timeline Options (Light Editorial Theme)
    const options: any = {
      orientation: 'top',
      stack: false,
      zoomMin: 1000 * 60 * 15,
      zoomMax: 1000 * 60 * 60 * 24 * 30,
      minHeight: '440px',
      maxHeight: '620px',
      margin: { item: 10, axis: 6 },
    };

    if (timelineInstance.current) {
      timelineInstance.current.setData({ groups: new DataSet(groups), items });
    } else {
      timelineInstance.current = new Timeline(timelineRef.current, items, new DataSet(groups), options);
      timelineInstance.current.on('select', (props) => {
        if (props.items && props.items.length > 0) {
          openSourceViewer(props.items[0]);
        }
      });
    }

    return () => {
      if (timelineInstance.current) {
        timelineInstance.current.destroy();
        timelineInstance.current = null;
      }
    };
  }, [filteredEvents, laneMode, anomalies, openSourceViewer]);

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16 font-sans">
      {/* 1. Header */}
      <div className="border-b border-border pb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-sans text-xs font-bold uppercase tracking-wider text-cobalt bg-cobalt-light px-2.5 py-1 rounded-full">
              Timeline Reconstruction
            </span>
            <span className="text-ink-tertiary">·</span>
            <span className="font-sans text-xs text-ink-secondary">Multi-Source Synchronized Sequence</span>
          </div>
          <h1 className="font-serif font-bold text-3xl sm:text-4xl text-ink mt-2 tracking-tight">
            Chronological Event Horizon
          </h1>
          <p className="text-sm text-ink-secondary mt-2 max-w-3xl leading-relaxed">
            Correlates 745 multi-modal timestamps across mobile handsets, WhatsApp message exports, bank ledger debits, and telecom cellular tower handoffs.
          </p>
        </div>

        {/* Source Filter Tabs */}
        <div className="flex items-center gap-1.5 flex-wrap bg-surface-raised p-1.5 rounded-xl border border-border text-xs shadow-xs">
          {['ALL', 'whatsapp', 'bank_pdf', 'calllog', 'image'].map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => setFilterSource(st)}
              className={`px-3 py-1.5 rounded-lg font-sans font-medium uppercase tracking-wider transition-all cursor-pointer ${
                filterSource === st
                  ? 'bg-cobalt text-white font-semibold shadow-xs'
                  : 'text-ink-secondary hover:text-ink hover:bg-ivory'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* 2. Interactive Lane Switcher & Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 bg-surface-raised p-4 rounded-xl border border-border shadow-xs">
        <div className="flex items-center gap-2">
          <span className="font-sans text-xs font-bold text-ink-secondary uppercase tracking-wider mr-2">
            Group Lanes By:
          </span>
          <button
            type="button"
            onClick={() => setLaneMode('source')}
            className={`px-4 py-2 rounded-lg text-xs font-sans font-semibold transition-all cursor-pointer ${
              laneMode === 'source'
                ? 'bg-ink text-white shadow-xs'
                : 'bg-surface text-ink-secondary hover:text-ink border border-border'
            }`}
          >
            Evidence Source File
          </button>
          <button
            type="button"
            onClick={() => setLaneMode('actor')}
            className={`px-4 py-2 rounded-lg text-xs font-sans font-semibold transition-all cursor-pointer ${
              laneMode === 'actor'
                ? 'bg-ink text-white shadow-xs'
                : 'bg-surface text-ink-secondary hover:text-ink border border-border'
            }`}
          >
            Primary Actor / Persona
          </button>
        </div>

        {/* Search Input */}
        <div className="relative min-w-[280px]">
          <Search className="w-4 h-4 text-ink-tertiary absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search keyword, amount, or persona..."
            className="w-full text-xs font-sans pl-10 pr-4 py-2 bg-surface rounded-lg border border-border focus:outline-hidden focus:border-cobalt transition-colors text-ink placeholder:text-ink-tertiary"
          />
        </div>
      </div>

      {/* 3. Vis-Timeline Container & Spatial Side Rail */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Timeline Canvas (9 Cols) */}
        <div className="lg:col-span-9 bg-surface-raised border border-border rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <span className="font-sans text-xs uppercase tracking-wider font-bold text-ink flex items-center gap-2">
              <Clock className="w-4 h-4 text-cobalt" />
              Unified Forensic Timeline View
            </span>
            <span className="text-2xs text-ink-secondary">
              CLICK CHIP TO OPEN EVIDENCE DOSSIER
            </span>
          </div>

          {eventsLoading ? (
            <div className="py-24 text-center text-xs text-ink-secondary">
              Synchronizing multi-source timestamps...
            </div>
          ) : (
            <div ref={timelineRef} className="timeline-container w-full" />
          )}

          {/* Timeline Anomaly Notice Banner */}
          <div className="bg-tomato-light border border-tomato/30 rounded-xl p-4 flex items-start gap-3 text-xs text-ink leading-relaxed">
            <AlertTriangle className="w-4 h-4 text-tomato shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-tomato block mb-0.5">
                GT-04 Anomaly: 6-Hour Silence Blackout Window Identified
              </span>
              Between <b className="font-mono">14 Mar 23:45 UTC</b> and <b className="font-mono">15 Mar 05:59 UTC</b>, zero incoming or outgoing chat messages were recorded despite automated debit confirmations continuing on mule bank accounts.
            </div>
          </div>
        </div>

        {/* Spatial Tower & Mobility Side Column (3 Cols) */}
        <div className="lg:col-span-3 bg-surface-raised border border-border rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <span className="font-sans text-xs uppercase tracking-wider font-bold text-ink flex items-center gap-2">
              <Compass className="w-4 h-4 text-ochre-dark" />
              Spatial Movement
            </span>
            <span className="font-mono text-2xs text-ink-secondary">GT-10</span>
          </div>

          <p className="text-xs text-ink-secondary leading-relaxed">
            Cellular tower CDR logs track suspect movement during fund liquidation.
          </p>

          <div className="space-y-2 pt-1">
            {Object.keys(locationsMap).length === 0 ? (
              <div className="text-xs text-ink-secondary">No cell towers found.</div>
            ) : (
              Object.entries(locationsMap).map(([locId, count]) => {
                const isJaipur = locId.toLowerCase().includes('jaipur');
                const isSelected = selectedLocation === locId;

                return (
                  <button
                    key={locId}
                    type="button"
                    onClick={() => setSelectedLocation(isSelected ? null : locId)}
                    className={`w-full text-left p-3 rounded-lg border transition-all cursor-pointer flex items-center justify-between ${
                      isSelected
                        ? 'bg-cobalt-light border-cobalt text-cobalt font-semibold'
                        : isJaipur
                        ? 'bg-lime-light border-lime-dark/30 hover:border-lime-dark text-ink'
                        : 'bg-surface border-border hover:bg-ivory text-ink'
                    }`}
                  >
                    <div className="space-y-0.5">
                      <div className="font-sans text-xs font-semibold flex items-center gap-1.5">
                        <MapPin className={`w-3.5 h-3.5 ${isJaipur ? 'text-lime-dark' : 'text-ink-secondary'}`} />
                        <span>{locId}</span>
                      </div>
                      {isJaipur && (
                        <span className="font-sans text-2xs text-lime-dark font-bold block">
                          Exit Location (ATM cash-out)
                        </span>
                      )}
                    </div>
                    <span className="font-mono text-xs bg-surface-raised px-2 py-0.5 rounded border border-border text-ink-secondary">
                      {count}
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
