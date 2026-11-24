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

  const pillClasses = isEvidence
    ? 'bg-[#EAF2F4] text-[#24525D] border-[#B2CDD4]'
    : isInvestigation
    ? 'bg-[#EEF2F8] text-[#415E87] border-[#C1CFE4]'
    : 'bg-white text-[#455066] border-[#C9C6BC]';

  const label = isEvidence
    ? 'Workspace 1 · Evidence & Court Package'
    : isInvestigation
    ? 'Workspace 2 · Investigation & Correlation'
    : 'Forensic Dossier · PRAMAAN';

  const Icon = isEvidence ? ShieldCheck : isInvestigation ? Compass : Layers;

  return (
    <header className="pb-6 border-b border-border flex flex-col sm:flex-row sm:items-end justify-between gap-4">
      <div className="space-y-2.5">
        <div
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded border font-sans text-[10.5px] font-bold uppercase tracking-[0.09em] ${pillClasses}`}
        >
          <Icon className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
          <span>{label}</span>
        </div>
        <h1 className="font-serif text-[36px] sm:text-[42px] text-[#20283A] leading-[1.08] tracking-[-0.02em]">
          {title}
        </h1>
        {subtitle && (
          <p className="text-[14px] text-[#455066] max-w-2xl leading-relaxed font-sans">
            {subtitle}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2.5 shrink-0">{actions}</div>}
    </header>
  );
};
