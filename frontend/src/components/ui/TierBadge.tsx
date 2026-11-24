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

  let colorClasses = 'text-[#8F6018] bg-[#FCF5E7] border-[#E8CFA0]';
  let Icon = Compass;
  let label = 'LEAD';

  if (normTier.includes('VERIFIED')) {
    colorClasses = 'text-[#24525D] bg-[#EAF2F4] border-[#B2CDD4]';
    Icon = CheckCircle2;
    label = 'VERIFIED BY CODE';
  } else if (normTier.includes('APPROVED')) {
    colorClasses = 'text-[#246B4F] bg-[#ECF6F1] border-[#B2D9C7]';
    Icon = ShieldCheck;
    label = 'APPROVED';
  } else if (normTier.includes('TAMPER') || normTier.includes('FAIL') || normTier.includes('BREACH')) {
    colorClasses = 'text-[#A63327] bg-[#FDF0EE] border-[#D95749]';
    Icon = AlertTriangle;
    label = 'INTEGRITY BREACH';
  }

  const sizeClasses =
    size === 'sm' ? 'px-2 py-0.5 text-[10px] tracking-[0.06em]' : 'px-2.5 py-1 text-[10.5px] tracking-[0.06em]';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono uppercase rounded border select-none transition-colors duration-150 whitespace-nowrap ${sizeClasses} ${colorClasses} ${className}`}
    >
      <Icon className="w-3 h-3 shrink-0" aria-hidden="true" />
      <span className="font-semibold">{label}</span>
    </span>
  );
};
