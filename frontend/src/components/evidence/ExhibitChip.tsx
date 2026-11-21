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
      disabled={!isClickable}
      title={eventId ? `Open Source Evidence: ${exhibitId} [Event: ${eventId}]` : `Exhibit ${exhibitId}`}
      className={`exhibit-id ${isClickable ? 'cursor-pointer' : 'cursor-default'} ${className}`}
    >
      <Tag className="w-3 h-3 shrink-0 text-teal" aria-hidden="true" />
      <span className="text-ink">{exhibitId}</span>
      {subRef && <span className="text-muted text-[11px]">· {subRef}</span>}
      {isClickable && <ArrowUpRight className="w-3 h-3 text-teal shrink-0" aria-hidden="true" />}
    </button>
  );
};
