import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderArchive,
  Users,
  Network,
  Clock,
  Fingerprint,
  CheckSquare,
  Scale,
  Package,
  BarChart3,
  Shield,
  FileCheck,
} from 'lucide-react';

const NAV_ITEMS = [
  { index: '01', to: '/', label: 'Overview', icon: LayoutDashboard },
  { index: '02', to: '/evidence', label: 'Evidence Vault', icon: FolderArchive },
  { index: '03', to: '/entities', label: 'Entities & People', icon: Users },
  { index: '04', to: '/graph', label: 'Knowledge Graph', icon: Network },
  { index: '05', to: '/events', label: 'Event Sequence', icon: Clock },
  { index: '06', to: '/authenticity', label: 'Authenticity Checks', icon: Fingerprint },
  { index: '07', to: '/review', label: 'Review Queue', icon: CheckSquare },
  { index: '08', to: '/verifier', label: 'Verifier & Challenge', icon: Scale },
  { index: '09', to: '/package', label: 'Case Package', icon: Package },
  { index: '10', to: '/metrics', label: 'Metrics & Benchmark', icon: BarChart3 },
];

export const LeftRail: React.FC = () => {
  return (
    <aside className="w-64 bg-surface border-r border-border flex flex-col justify-between shrink-0 select-none">
      {/* Top Section */}
      <div className="p-6">
        {/* Brand Identity */}
        <div className="pb-6 mb-6 border-b border-border/80">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-cobalt flex items-center justify-center text-white shadow-xs">
              <Shield className="w-4 h-4" />
            </div>
            <div>
              <span className="font-serif font-black text-2xl tracking-tight text-ink block leading-none">
                PRAMAAN
              </span>
              <span className="font-sans text-xs text-ink-secondary mt-0.5 block tracking-wider uppercase">
                Forensic Intelligence
              </span>
            </div>
          </div>
        </div>

        {/* Section Title */}
        <div className="px-2 mb-2">
          <span className="font-sans text-xs font-bold uppercase tracking-widest text-ink-tertiary">
            Investigation Modules
          </span>
        </div>

        {/* Navigation Item List */}
        <nav className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-sans transition-all group ${
                    isActive
                      ? 'bg-cobalt text-white font-semibold shadow-xs'
                      : 'text-ink-secondary hover:text-ink hover:bg-ivory-dark/60 font-medium'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <div className="flex items-center gap-3 truncate">
                      <Icon
                        className={`w-4 h-4 shrink-0 transition-colors ${
                          isActive ? 'text-white' : 'text-ink-tertiary group-hover:text-ink'
                        }`}
                      />
                      <span className="truncate">{item.label}</span>
                    </div>
                    <span
                      className={`font-mono text-xs transition-colors ${
                        isActive
                          ? 'text-white/80 font-bold'
                          : 'text-ink-tertiary/60 group-hover:text-ink-secondary'
                      }`}
                    >
                      {item.index}
                    </span>
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer / Trust Badge */}
      <div className="p-5 border-t border-border bg-ivory/50">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-lime-light flex items-center justify-center text-lime-dark shrink-0">
            <FileCheck className="w-4 h-4" />
          </div>
          <div>
            <div className="font-sans text-xs font-bold text-ink">
              Section 63 BSA Ready
            </div>
            <div className="font-sans text-2xs text-ink-secondary">
              Immutable chain-of-custody
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
