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

  let colorClasses = 'text-[#C97B1A] bg-[#FCF4E8] border-[#E8C99B]';
  let Icon = Compass;
  let label = 'LEAD';

  if (normTier.includes('VERIFIED')) {
    colorClasses = 'text-[#2E5E6E] bg-[#EDF4F6] border-[#B8D0D8]';
    Icon = CheckCircle2;
    label = 'VERIFIED BY CODE';
  } else if (normTier.includes('APPROVED')) {
    colorClasses = 'text-[#3F7D58] bg-[#EEF6F1] border-[#B4D4C0]';
    Icon = ShieldCheck;
    label = 'APPROVED';
  } else if (normTier.includes('TAMPER') || normTier.includes('FAIL') || normTier.includes('BREACH')) {
    colorClasses = 'text-[#DB4A2B] bg-[#FDF0EC] border-[#DB4A2B]';
    Icon = AlertTriangle;
    label = 'INTEGRITY BREACH';
  }

  const sizeClasses =
    size === 'sm' ? 'px-1.5 py-0.5 text-[11px] tracking-wide' : 'px-2.5 py-1 text-[11px] tracking-wide';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono uppercase rounded border select-none transition-colors duration-150 whitespace-nowrap ${sizeClasses} ${colorClasses} ${className}`}
    >
      <Icon className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
      <span className="font-semibold">{label}</span>
    </span>
  );
};
