"use client";

import { formatMoney } from "@/lib/format";

interface BudgetBarProps {
  spent: number;
  budget: number;
  held?: number;
  currency: string;
}

export function BudgetBar({ spent, budget, held = 0, currency }: BudgetBarProps) {
  const remaining = Math.max(budget - spent - held, 0);
  const total = remaining + held;
  const remainingPct = total > 0 ? (remaining / total) * 100 : 0;
  const heldPct = total > 0 ? (held / total) * 100 : 0;

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="font-medium">{formatMoney(remaining, currency)} available</span>
        {held > 0 && (
          <span className="text-muted-foreground text-xs">
            {formatMoney(held, currency)} held
          </span>
        )}
      </div>
      <div className="h-2 rounded-full overflow-hidden flex">
        {remainingPct > 0 && (
          <div
            className="h-full bg-green-500 transition-all"
            style={{ width: `${remainingPct}%` }}
          />
        )}
        {heldPct > 0 && (
          <div
            className="h-full bg-yellow-500 transition-all"
            style={{ width: `${heldPct}%` }}
          />
        )}
        {total === 0 && (
          <div className="h-full w-full bg-muted" />
        )}
      </div>
    </div>
  );
}
