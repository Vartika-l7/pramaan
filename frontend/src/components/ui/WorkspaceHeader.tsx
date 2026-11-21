import React from 'react';
import { ShieldCheck, Compass, Layers } from 'lucide-react';

interface WorkspaceHeaderProps {
  workspace: 'overview' | 'evidence' | 'investigation';
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export const WorkspaceHeader: React.FC<WorkspaceHeaderProps> = ({
  workspace,
  title,
  subtitle,
  actions,
}) => {
  const isEvidence = workspace === 'evidence';
  const isInvestigation = workspace === 'investigation';

  const barColor = isEvidence
    ? 'border-t-2 border-t-[#2E5E6E] text-[#2E5E6E]'
    : isInvestigation
    ? 'border-t-2 border-t-[#C97B1A] text-[#C97B1A]'
    : 'border-t-2 border-t-[#E8D9CC] text-[#7A5C52]';

  const label = isEvidence
    ? 'Workspace 1 · Evidence and Court Package (Provable & Human-Approved)'
    : isInvestigation
    ? 'Workspace 2 · Investigation (Leads Until Human-Approved)'
    : 'Case Dossier Overview';

  const Icon = isEvidence ? ShieldCheck : isInvestigation ? Compass : Layers;

  return (
    <header className={`pt-2 pb-4 border-b border-border flex flex-col sm:flex-row sm:items-end justify-between gap-3 ${barColor}`}>
      <div className="space-y-1">
        <div className="flex items-center gap-1.5 font-sans text-[11px] font-bold uppercase tracking-[0.08em]">
          <Icon className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
          <span>{label}</span>
        </div>
        <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink leading-tight">
          {title}
        </h1>
        {subtitle && <p className="text-sm text-muted max-w-3xl">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </header>
  );
};
