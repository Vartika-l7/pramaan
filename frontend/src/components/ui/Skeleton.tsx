import React from 'react';
import { AlertTriangle } from 'lucide-react';

export const SkeletonBlock: React.FC<{ className?: string }> = ({ className = 'h-24 w-full' }) => (
  <div className={`animate-pulse bg-paper-subtle border border-border rounded ${className}`} />
);

export const EmptyState: React.FC<{
  title: string;
  description: string;
  action?: React.ReactNode;
}> = ({ title, description, action }) => (
  <div className="bg-panel border border-border rounded p-8 text-center space-y-2">
    <p className="font-serif text-lg font-semibold text-ink">{title}</p>
    <p className="text-sm text-muted max-w-md mx-auto">{description}</p>
    {action && <div className="pt-2">{action}</div>}
  </div>
);

export const ErrorState: React.FC<{ message: string; onRetry?: () => void }> = ({ message, onRetry }) => (
  <div className="bg-vermilion-light border border-vermilion rounded p-4 flex items-center justify-between gap-4 text-sm text-ink">
    <div className="flex items-center gap-2">
      <AlertTriangle className="w-4 h-4 text-vermilion shrink-0" aria-hidden="true" />
      <span>{message}</span>
    </div>
    {onRetry && (
      <button
        type="button"
        onClick={onRetry}
        className="px-3 py-1 rounded border border-vermilion text-vermilion font-medium text-xs hover:bg-panel transition-colors duration-150 cursor-pointer"
      >
        Retry
      </button>
    )}
  </div>
);
