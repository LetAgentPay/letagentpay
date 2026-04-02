"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { RequestCard } from "@/components/request-card";
import { api } from "@/lib/api";
import type { PurchaseRequestItem } from "@/lib/types";

interface RequestListProps {
  agentId: string;
  currency: string;
  refreshKey?: number;
}

const STATUSES = ["all", "pending", "approved", "auto_approved", "completed", "rejected", "expired"] as const;
const PAGE_SIZE = 10;

export function RequestList({ agentId, currency, refreshKey }: RequestListProps) {
  const [status, setStatus] = useState<string>("all");
  const [items, setItems] = useState<PurchaseRequestItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listRequests(agentId, {
        status: status === "all" ? undefined : status,
        limit: PAGE_SIZE,
        offset,
      });
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }, [agentId, status, offset]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  useEffect(() => {
    setOffset(0);
  }, [status]);

  const hasMore = offset + PAGE_SIZE < total;

  return (
    <div className="space-y-3">
      <div className="flex gap-1 overflow-x-auto pb-1 -mb-1">
        {STATUSES.map((s) => (
          <Button
            key={s}
            variant={status === s ? "default" : "outline"}
            size="sm"
            className="shrink-0"
            onClick={() => setStatus(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </Button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <p className="text-center text-sm text-muted-foreground py-8">
          No requests found
        </p>
      ) : (
        <>
          <div className="space-y-2">
            {items.map((item) => (
              <RequestCard key={item.id} request={item} currency={currency} onUpdate={load} />
            ))}
          </div>
          <div className="flex justify-between items-center">
            <Button
              variant="outline"
              size="sm"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Previous
            </Button>
            <span className="text-sm text-muted-foreground">
              {offset + 1}-{Math.min(offset + PAGE_SIZE, total)} of {total}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={!hasMore}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
