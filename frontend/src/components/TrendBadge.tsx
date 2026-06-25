import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface TrendBadgeProps {
  trend: string;
}

export function TrendBadge({ trend }: TrendBadgeProps) {
  const isUp = /hausse|increasing/i.test(trend);
  const isDown = /baisse|decreasing/i.test(trend);
  const isStable = /stable/i.test(trend);

  const Icon = isUp ? TrendingUp : isDown ? TrendingDown : Minus;
  const color = isUp
    ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
    : isDown
    ? 'text-red-700 bg-red-50 border-red-200'
    : 'text-blue-700 bg-blue-50 border-blue-200';

  return (
    <div className={`flex items-start gap-3 p-4 rounded-xl border ${color}`}>
      <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
      <p className="text-sm leading-relaxed">{trend}</p>
    </div>
  );
}
