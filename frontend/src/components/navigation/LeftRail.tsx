import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderArchive,
  Scale,
  Network,
  Compass,
  MessageSquare,
  Shield,
} from 'lucide-react';

const EVIDENCE_NAV = [
  { to: '/evidence', label: 'Evidence', icon: FolderArchive },
  { to: '/review', label: 'Review and Report', icon: Scale },
];

const INVESTIGATION_NAV = [
  { to: '/graph', label: 'Knowledge Graph', icon: Network },
  { to: '/reconstruction', label: 'Reconstruction', icon: Compass },
  { to: '/assistant', label: 'Assistant', icon: MessageSquare },
];

export const LeftRail: React.FC = () => {
  return (
    <aside className="w-60 bg-panel border-r border-border flex flex-col justify-between shrink-0 select-none">
      <div className="p-5 space-y-6">
        {/* Brand Identity */}
        <div className="pb-4 border-b border-border flex items-center gap-2.5">
          <div className="w-8 h-8 rounded bg-ink flex items-center justify-center text-paper shrink-0">
            <Shield className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <span className="font-serif font-bold text-xl tracking-tight text-ink block leading-none">
              PRAMAAN
            </span>
            <span className="font-sans text-[10px] text-muted mt-1 block tracking-[0.08em] uppercase">
              Digital Forensics
            </span>
          </div>
        </div>

        {/* Top: Overview (above both groups) */}
        <nav aria-label="Primary Navigation" className="space-y-6">
          <div>
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded text-sm font-sans transition-colors duration-150 ${
                  isActive
                    ? 'bg-paper-subtle text-ink font-semibold border border-border-strong'
                    : 'text-muted hover:text-ink hover:bg-paper font-medium'
                }`
              }
            >
              <LayoutDashboard className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>Overview</span>
            </NavLink>
          </div>

          {/* Group 1: Evidence and Court Package (Slate Teal #2E5E6E) */}
          <div className="space-y-1.5">
            <div className="px-3 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-teal shrink-0" aria-hidden="true" />
              <span className="font-sans text-[10px] font-bold uppercase tracking-[0.08em] text-teal">
                Evidence and Court Package
              </span>
            </div>
            <div className="space-y-1">
              {EVIDENCE_NAV.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `flex items-center gap-2.5 px-3 py-2 rounded text-sm font-sans transition-colors duration-150 ${
                        isActive
                          ? 'bg-teal text-white font-semibold'
                          : 'text-muted hover:text-ink hover:bg-teal-light/60 font-medium'
                      }`
                    }
                  >
                    <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                    <span className="truncate">{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
          </div>

          {/* Group 2: Investigation (Lead Amber #C97B1A) */}
          <div className="space-y-1.5">
            <div className="px-3 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-amber shrink-0" aria-hidden="true" />
              <span className="font-sans text-[10px] font-bold uppercase tracking-[0.08em] text-amber">
                Investigation
              </span>
            </div>
            <div className="space-y-1">
              {INVESTIGATION_NAV.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `flex items-center gap-2.5 px-3 py-2 rounded text-sm font-sans transition-colors duration-150 ${
                        isActive
                          ? 'bg-amber text-white font-semibold'
                          : 'text-muted hover:text-ink hover:bg-amber-light/70 font-medium'
                      }`
                    }
                  >
                    <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                    <span className="truncate">{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
          </div>
        </nav>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-border bg-paper text-xs font-sans text-muted space-y-1">
        <div className="flex items-center justify-between font-mono text-[11px] font-semibold">
          <span>MODE: OFFLINE</span>
          <span className="text-teal">LOCAL ONLY</span>
        </div>
        <p className="text-[11px] leading-relaxed text-muted">
          Section 63 BSA / 65B IEA digital custody &amp; human-gated court reporting.
        </p>
      </div>
    </aside>
  );
};
