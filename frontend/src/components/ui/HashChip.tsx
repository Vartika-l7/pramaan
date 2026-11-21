import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface HashChipProps {
  hash?: string | null;
  className?: string;
}

export const HashChip: React.FC<HashChipProps> = ({ hash, className = '' }) => {
  const [copied, setCopied] = useState(false);

  if (!hash) {
    return <span className="font-mono text-xs text-muted">—</span>;
  }

  const short = hash.length > 14 ? `${hash.slice(0, 8)}…${hash.slice(-4)}` : hash;

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={`SHA-256: ${hash} (click to copy)`}
      className={`inline-flex items-center gap-1.5 font-mono text-xs px-2 py-0.5 rounded border border-border bg-paper text-ink hover:border-teal transition-colors duration-150 cursor-pointer whitespace-nowrap ${className}`}
    >
      <span>{short}</span>
      {copied ? (
        <Check className="w-3 h-3 text-approved shrink-0" aria-hidden="true" />
      ) : (
        <Copy className="w-3 h-3 text-muted shrink-0" aria-hidden="true" />
      )}
    </button>
  );
};
