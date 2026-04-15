"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { formatMoney } from "@/lib/format";

interface X402StatsProps {
  agentId: string;
  refreshKey?: number;
}

interface X402StatsData {
  total_transactions: number;
  total_volume_usd: string;
  settled_count: number;
  top_domains: { domain: string; count: number; volume_usd: string }[];
}

export function X402Stats({ agentId, refreshKey }: X402StatsProps) {
  const [stats, setStats] = useState<X402StatsData | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.getX402Stats(agentId);
      setStats(data);
    } catch {
      // No x402 transactions yet — that's fine
    }
  }, [agentId]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  if (!stats || stats.total_transactions === 0) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-medium">x402 Payments</h3>
        <Badge variant="outline" className="text-xs font-mono">USDC</Badge>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="py-3 text-center">
            <div className="text-lg font-semibold">{stats.total_transactions}</div>
            <div className="text-xs text-muted-foreground">Transactions</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3 text-center">
            <div className="text-lg font-semibold">
              {formatMoney(parseFloat(stats.total_volume_usd), "USD")}
            </div>
            <div className="text-xs text-muted-foreground">Volume</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-3 text-center">
            <div className="text-lg font-semibold">{stats.settled_count}</div>
            <div className="text-xs text-muted-foreground">On-chain settled</div>
          </CardContent>
        </Card>
      </div>
      {stats.top_domains.length > 0 && (
        <div className="text-xs text-muted-foreground space-y-1">
          <div className="font-medium">Top domains:</div>
          {stats.top_domains.map((d) => (
            <div key={d.domain} className="flex justify-between">
              <span className="font-mono truncate">{d.domain}</span>
              <span>{d.count} tx &middot; {formatMoney(parseFloat(d.volume_usd), "USD")}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
