import React from 'react';
import { ShieldCheck, Compass, CheckCircle2, AlertTriangle } from 'lucide-react';
import { Tier } from '../../types';

interface TierBadgeProps {
  tier: Tier | 'TAMPERED' | string;
  className?: string;
  size?: 'sm' | 'md';
}

export const TierBadge: React.FC<TierBadgeProps> = ({ tier, className = '', size = 'md' }) => {
  const normTier = (tier || '').toUpperCase();

  // Default: LEAD
  let colorClasses = 'text-ochre-dark bg-ochre-light border-ochre/40';
  let Icon = Compass;
  let label = 'LEAD';

  if (normTier.includes('VERIFIED')) {
    colorClasses = 'text-lime-dark bg-lime-light border-lime-dark/30';
    Icon = CheckCircle2;
    label = 'VERIFIED BY CODE';
  } else if (normTier.includes('APPROVED')) {
    colorClasses = 'text-[#2E7D32] bg-[#E8F5E9] border-[#A5D6A7]';
    Icon = ShieldCheck;
    label = 'APPROVED';
  } else if (normTier.includes('TAMPER') || normTier.includes('FAIL') || normTier.includes('BREACH')) {
    colorClasses = 'text-tomato bg-tomato-light border-tomato/40';
    Icon = AlertTriangle;
    label = 'INTEGRITY BREACH';
  }

  const sizeClasses =
    size === 'sm'
      ? 'px-1.5 py-0.5 text-2xs tracking-wide'
      : 'px-2.5 py-1 text-2xs tracking-wide';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono uppercase rounded-sm border select-none transition-colors ${sizeClasses} ${colorClasses} ${className}`}
    >
      <Icon className={size === 'sm' ? 'w-3 h-3 shrink-0' : 'w-3.5 h-3.5 shrink-0'} />
      <span className="font-semibold">{label}</span>
    </span>
  );
};
