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
  Lock,
} from 'lucide-react';

const EVIDENCE_NAV = [
  { to: '/evidence', label: 'Evidence Vault', icon: FolderArchive },
  { to: '/review', label: 'Review and Report', icon: Scale },
];

const INVESTIGATION_NAV = [
  { to: '/graph', label: 'Knowledge Graph', icon: Network },
  { to: '/reconstruction', label: 'Reconstruction', icon: Compass },
  { to: '/assistant', label: 'Assistant', icon: MessageSquare },
];

export const LeftRail: React.FC = () => {
  return (
    <aside className="w-64 bg-[#EEECE6] border-r border-border flex flex-col justify-between shrink-0 select-none">
      <div className="p-5 space-y-7">
        {/* PRAMAAN Brand Identity */}
        <div className="pb-5 border-b border-border-strong/70 flex items-center gap-3">
          <div className="relative w-10 h-10 rounded-lg bg-[#20283A] flex items-center justify-center text-white shrink-0 shadow-card ring-1 ring-[#316A78]/40">
            <Shield className="w-5 h-5 text-[#9AD0DB]" strokeWidth={1.8} aria-hidden="true" />
            <span
              className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-[#316A78] border-2 border-[#EEECE6]"
              aria-hidden="true"
            />
          </div>
          <div className="min-w-0">
            <span className="font-serif text-[26px] tracking-tight text-[#20283A] block leading-none">
              PRAMAAN
            </span>
            <span className="font-mono text-[9.5px] text-[#556077] mt-1 block tracking-[0.14em] uppercase font-medium">
              Forensic Engine
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav aria-label="Primary Navigation" className="space-y-6">
          {/* Overview */}
          <div className="space-y-1">
            <div className="px-3 pb-1">
              <span className="font-sans text-[10px] font-bold uppercase tracking-[0.11em] text-[#556077]">
                Dossier
              </span>
            </div>
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `group relative flex items-center gap-3 px-3 py-2.5 rounded-md text-[13px] font-sans transition-all duration-150 ${
                  isActive
                    ? 'bg-white text-[#20283A] font-semibold shadow-card border border-[#C9C6BC]'
                    : 'text-[#455066] hover:text-[#20283A] hover:bg-white/60 font-medium border border-transparent'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span
                      className="absolute left-0 top-2 bottom-2 w-[3px] rounded-r bg-[#20283A]"
                      aria-hidden="true"
                    />
                  )}
                  <LayoutDashboard
                    className={`w-4 h-4 shrink-0 transition-colors ${
                      isActive ? 'text-[#20283A]' : 'text-[#556077] group-hover:text-[#20283A]'
                    }`}
                    aria-hidden="true"
                  />
                  <span>Overview</span>
                </>
              )}
            </NavLink>
          </div>

          {/* Group 1: Evidence & Court Package (Deep Teal #316A78) */}
          <div className="space-y-1.5">
            <div className="px-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#316A78] shrink-0" aria-hidden="true" />
                <span className="font-sans text-[10px] font-bold uppercase tracking-[0.1em] text-[#24525D]">
                  Evidence &amp; Court
                </span>
              </div>
              <span className="font-mono text-[9.5px] font-semibold text-[#316A78]">W1</span>
            </div>
            <div className="space-y-1">
              {EVIDENCE_NAV.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `group relative flex items-center gap-3 px-3 py-2.5 rounded-md text-[13px] font-sans transition-all duration-150 ${
                        isActive
                          ? 'bg-white text-[#24525D] font-semibold shadow-card border border-[#B2CDD4]'
                          : 'text-[#455066] hover:text-[#20283A] hover:bg-white/65 font-medium border border-transparent'
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && (
                          <span
                            className="absolute left-0 top-2 bottom-2 w-[3px] rounded-r bg-[#316A78]"
                            aria-hidden="true"
                          />
                        )}
                        <Icon
                          className={`w-4 h-4 shrink-0 transition-colors ${
                            isActive ? 'text-[#316A78]' : 'text-[#556077] group-hover:text-[#316A78]'
                          }`}
                          aria-hidden="true"
                        />
                        <span className="truncate">{item.label}</span>
                      </>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>

          {/* Group 2: Investigation (Slate Blue #5576A5) */}
          <div className="space-y-1.5">
            <div className="px-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#5576A5] shrink-0" aria-hidden="true" />
                <span className="font-sans text-[10px] font-bold uppercase tracking-[0.1em] text-[#415E87]">
                  Investigation
                </span>
              </div>
              <span className="font-mono text-[9.5px] font-semibold text-[#5576A5]">W2</span>
            </div>
            <div className="space-y-1">
              {INVESTIGATION_NAV.map((item) => {
                const Icon = item.icon;
                const isAi = item.to === '/assistant';
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `group relative flex items-center gap-3 px-3 py-2.5 rounded-md text-[13px] font-sans transition-all duration-150 ${
                        isActive
                          ? 'bg-white text-[#415E87] font-semibold shadow-card border border-[#C1CFE4]'
                          : 'text-[#455066] hover:text-[#20283A] hover:bg-white/65 font-medium border border-transparent'
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && (
                          <span
                            className="absolute left-0 top-2 bottom-2 w-[3px] rounded-r bg-[#5576A5]"
                            aria-hidden="true"
                          />
                        )}
                        <Icon
                          className={`w-4 h-4 shrink-0 transition-colors ${
                            isActive ? 'text-[#5576A5]' : 'text-[#556077] group-hover:text-[#5576A5]'
                          }`}
                          aria-hidden="true"
                        />
                        <span className="truncate">{item.label}</span>
                        {isAi && (
                          <span className="ml-auto font-mono text-[9.5px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-[#EEF2F8] text-[#415E87] border border-[#C1CFE4]">
                            AI
                          </span>
                        )}
                      </>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>
        </nav>
      </div>

      {/* Offline Custody Footer Card */}
      <div className="p-4">
        <div className="p-3.5 rounded-lg bg-white border border-border shadow-card space-y-2">
          <div className="flex items-center justify-between font-mono text-[10px] font-semibold">
            <span className="inline-flex items-center gap-1.5 text-[#20283A]">
              <Lock className="w-3 h-3 text-[#316A78]" aria-hidden="true" />
              OFFLINE VAULT
            </span>
            <span className="inline-flex items-center gap-1 text-[#24525D] bg-[#EAF2F4] px-2 py-0.5 rounded border border-[#B2CDD4]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#316A78]" />
              LOCAL
            </span>
          </div>
          <p className="text-[11px] leading-relaxed text-[#556077]">
            Sec. 63 BSA / 65B IEA custody &amp; human-gated court reporting.
          </p>
        </div>
      </div>
    </aside>
  );
};
