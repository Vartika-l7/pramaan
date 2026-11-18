import React from 'react';
import { Tag, ArrowUpRight } from 'lucide-react';
import { useAppStore } from '../../lib/store';

interface ExhibitChipProps {
  exhibitId: string;
  subRef?: string;
  eventId?: string;
  onClick?: () => void;
  className?: string;
}

export const ExhibitChip: React.FC<ExhibitChipProps> = ({
  exhibitId,
  subRef,
  eventId,
  onClick,
  className = '',
}) => {
  const openSourceViewer = useAppStore((state) => state.openSourceViewer);

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onClick) {
      onClick();
    } else if (eventId) {
      openSourceViewer(eventId);
    }
  };

  const isClickable = !!(eventId || onClick);

  return (
    <button
      type="button"
      onClick={handleClick}
      title={eventId ? `Open Source Evidence: ${exhibitId} [Event: ${eventId}]` : `Exhibit ${exhibitId}`}
      className={`exhibit-id transition-all group ${isClickable ? 'cursor-pointer hover:border-cobalt hover:bg-cobalt/5' : 'cursor-default'} ${className}`}
    >
      <Tag className={`w-3 h-3 shrink-0 ${isClickable ? 'text-cobalt' : 'text-ink-tertiary'} group-hover:text-cobalt transition-colors`} />
      <span className={isClickable ? 'text-cobalt' : 'text-ink'}>{exhibitId}</span>
      {subRef && <span className="text-ink-tertiary text-[10px]">· {subRef}</span>}
      {isClickable && (
        <ArrowUpRight className="w-2.5 h-2.5 text-cobalt ml-0.5 opacity-70 group-hover:opacity-100 transition-opacity" />
      )}
    </button>
  );
};
