"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatMoney } from "@/lib/format";

interface SpendingSummaryProps {
  agentId: string;
  currency: string;
  refreshKey?: number;
}

export function SpendingSummary({ agentId, currency, refreshKey }: SpendingSummaryProps) {
  const [stats, setStats] = useState<{
    spent_today: string;
    spent_week: string;
    spent_month: string;
  } | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.getSpendingStats(agentId);
      setStats(data);
    } catch {
      // ignore
    }
  }, [agentId]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  if (!stats) return null;

  const items = [
    { label: "Today", value: stats.spent_today },
    { label: "This week", value: stats.spent_week },
    { label: "This month", value: stats.spent_month },
  ];

  return (
    <div className="grid grid-cols-3 gap-3">
      {items.map((item) => (
        <Card key={item.label}>
          <CardContent className="py-3 text-center">
            <div className="text-lg font-semibold">
              {formatMoney(parseFloat(item.value), currency)}
            </div>
            <div className="text-xs text-muted-foreground">{item.label}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
