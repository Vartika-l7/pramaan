import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Users,
  Search,
  Phone,
  CreditCard,
  Smartphone,
  Globe,
  MapPin,
  Building,
  Hash,
  ChevronRight,
  X,
  Tag,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';
import { fetchEntities, fetchEntityDetail } from '../lib/api';
import { Entity, Mention } from '../types';
import { ExhibitChip } from '../components/evidence/ExhibitChip';
import { TierBadge } from '../components/ui/TierBadge';

const TYPE_ICONS: Record<string, any> = {
  PERSON: Users,
  PHONE: Phone,
  UPI: CreditCard,
  ACCOUNT: Building,
  DEVICE: Smartphone,
  URL: Globe,
  LOCATION: MapPin,
  IFSC: Hash,
};

const TYPE_BADGE_STYLES: Record<string, string> = {
  PERSON: 'bg-cobalt-light text-cobalt',
  PHONE: 'bg-lime-light text-lime-dark',
  UPI: 'bg-ochre-light text-ochre-dark',
  ACCOUNT: 'bg-tomato-light text-tomato',
  DEVICE: 'bg-lavender-light text-lavender-dark',
  URL: 'bg-ivory-dark text-ink-secondary',
  LOCATION: 'bg-ivory-dark text-ink-secondary',
  IFSC: 'bg-cobalt-light text-cobalt',
};

export const EntitiesPage: React.FC = () => {
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeEntityId, setActiveEntityId] = useState<string | null>(null);

  const { data: entities, isLoading } = useQuery({
    queryKey: ['entitiesList', selectedType, searchQuery],
    queryFn: () => fetchEntities(selectedType === 'ALL' ? undefined : selectedType, searchQuery || undefined),
  });

  const { data: entityDetail, isLoading: detailLoading } = useQuery({
    queryKey: ['entityDetail', activeEntityId],
    queryFn: () => (activeEntityId ? fetchEntityDetail(activeEntityId) : null),
    enabled: !!activeEntityId,
  });

  const types = ['ALL', 'PERSON', 'PHONE', 'UPI', 'ACCOUNT', 'DEVICE', 'URL', 'LOCATION', 'IFSC'];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="border-b border-border pb-5 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="section-label mb-1.5">
            Dossier Section 03 · Entity Extraction &amp; Linguistic Resolution
          </div>
          <h1 className="font-serif text-4xl font-bold text-ink tracking-tight">
            Entities &amp; People
          </h1>
          <p className="text-ink-secondary text-sm mt-2 max-w-3xl leading-relaxed">
            Deterministic extraction of Indian phone numbers, VPA/UPI IDs, IFSC codes, bank accounts, and transliterated Hinglish slang/Devanagari personas, resolved via RapidFuzz and cross-source token alignment.
          </p>
        </div>

        <div className="font-mono text-sm text-ink-secondary bg-surface-raised px-3 py-1.5 rounded-lg border border-border self-start md:self-auto">
          <span>Total Resolved: </span>
          <span className="font-bold text-ink">{entities?.length || 0}</span>
        </div>
      </div>

      {/* Filter Tabs & Search Controls */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          {types.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setSelectedType(t)}
              className={`rounded-full px-4 py-1.5 text-sm transition-colors cursor-pointer font-sans ${
                selectedType === t
                  ? 'bg-cobalt text-white font-medium'
                  : 'bg-surface-raised border border-border text-ink-secondary hover:bg-ivory-dark'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-ink-tertiary absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter by name, phone, UPI..."
            className="w-full pl-9 pr-3 py-2 text-sm bg-surface-raised border border-border rounded-lg outline-none focus:border-cobalt focus:ring-1 focus:ring-cobalt/20 font-sans text-ink placeholder:text-ink-tertiary transition-colors"
          />
        </div>
      </div>

      {/* Entities List */}
      <div className="space-y-2">
        {isLoading ? (
          <div className="py-12 text-center text-ink-tertiary font-mono text-xs">
            Querying resolved entities from SQLite...
          </div>
        ) : entities?.length === 0 ? (
          <div className="py-12 text-center text-ink-tertiary font-mono text-xs">
            No matching entities found in dataset.
          </div>
        ) : (
          entities?.map((ent) => {
            const Icon = TYPE_ICONS[ent.type] || Users;
            const badgeStyle = TYPE_BADGE_STYLES[ent.type] || 'bg-ivory-dark text-ink-secondary';
            const isExpanded = activeEntityId === ent.id;
            return (
              <div
                key={ent.id}
                className="bg-surface-raised border border-border rounded-lg p-4 hover:border-border-strong transition-all"
              >
                <div
                  className="flex items-center justify-between cursor-pointer"
                  onClick={() => setActiveEntityId(isExpanded ? null : ent.id)}
                >
                  <div className="flex items-center gap-3">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-sans font-medium ${badgeStyle}`}>
                      <Icon className="w-3.5 h-3.5" />
                      {ent.type}
                    </span>
                    <span className="font-mono text-sm font-semibold text-ink">
                      {ent.display}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-ink-secondary text-sm font-sans">
                      {ent.mention_count || 0} mentions
                    </span>
                    <TierBadge tier="VERIFIED BY CODE" size="sm" />
                    <ChevronRight
                      className={`w-4 h-4 text-ink-tertiary transition-transform ${isExpanded ? 'rotate-90 text-cobalt' : ''}`}
                    />
                  </div>
                </div>

                {/* Expandable mention list */}
                {isExpanded && (
                  <div className="bg-ivory rounded-lg p-3 mt-3 space-y-2">
                    {detailLoading ? (
                      <div className="text-xs font-mono text-ink-tertiary text-center py-4">
                        Retrieving mention offsets and spans...
                      </div>
                    ) : (
                      <>
                        <div className="font-mono text-xs text-ink-secondary bg-surface-raised p-2.5 rounded-lg border border-border mb-3">
                          <div className="section-label mb-1">Canonical Profile</div>
                          <div className="font-bold text-base text-ink">{entityDetail?.display}</div>
                          <div className="text-ink-tertiary text-xs mt-0.5">
                            Type: <span className="font-semibold text-ink-secondary">{entityDetail?.type}</span>
                          </div>
                        </div>

                        <div className="flex items-center justify-between mb-1.5">
                          <span className="section-label">
                            Source Occurrences ({entityDetail?.mentions?.length || 0})
                          </span>
                          <span className="text-xs font-mono text-ink-tertiary">EXACT OFFSETS</span>
                        </div>

                        {entityDetail?.mentions?.map((m: any) => (
                          <div
                            key={m.id}
                            className="bg-surface-raised border border-border rounded-lg p-3 text-xs space-y-2"
                          >
                            <div className="flex items-center justify-between">
                              <ExhibitChip exhibitId={m.exhibit_id} eventId={m.event_id} />
                              <span className="font-mono text-xs text-ink-tertiary bg-ivory px-2 py-0.5 rounded border border-border">
                                Offset {m.char_start}–{m.char_end}
                              </span>
                            </div>
                            <div className="font-mono text-xs bg-ivory p-2.5 rounded-lg border border-border text-ink-secondary leading-relaxed">
                              "{m.text}"
                            </div>
                          </div>
                        ))}
                      </>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
