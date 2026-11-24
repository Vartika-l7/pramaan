import React from 'react';
import { AlertTriangle } from 'lucide-react';

export const SkeletonBlock: React.FC<{ className?: string }> = ({ className = 'h-24 w-full' }) => (
  <div className={`animate-pulse bg-paper-subtle border border-border rounded-xl ${className}`} />
);

export const EmptyState: React.FC<{
  title: string;
  description: string;
  action?: React.ReactNode;
}> = ({ title, description, action }) => (
  <div className="bg-panel/80 border border-dashed border-border-strong rounded-xl p-10 text-center space-y-2.5">
    <p className="font-serif text-2xl text-ink tracking-tight">{title}</p>
    <p className="text-[13px] text-muted max-w-md mx-auto leading-relaxed">{description}</p>
    {action && <div className="pt-3">{action}</div>}
  </div>
);

export const ErrorState: React.FC<{ message: string; onRetry?: () => void }> = ({ message, onRetry }) => (
  <div className="bg-vermilion-light border border-vermilion/50 rounded-xl p-4 flex items-center justify-between gap-4 text-sm text-ink shadow-card">
    <div className="flex items-center gap-2.5">
      <AlertTriangle className="w-4 h-4 text-vermilion shrink-0" aria-hidden="true" />
      <span className="font-medium">{message}</span>
    </div>
    {onRetry && (
      <button
        type="button"
        onClick={onRetry}
        className="px-3.5 py-1.5 rounded-full border border-vermilion text-vermilion font-semibold text-xs hover:bg-vermilion hover:text-white transition-colors duration-150 cursor-pointer"
      >
        Retry
      </button>
    )}
  </div>
);
