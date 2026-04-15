"use client";

import { memo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { PurchaseRequestItem } from "@/lib/types";
import { api, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { track } from "@/lib/ee-hooks";
import { toast } from "sonner";
import { Check, ExternalLink, Link2, X } from "lucide-react";

function getTxExplorerUrl(txHash: string): string {
  // Default to Base (Basescan); can be extended with chain info later
  if (txHash.startsWith("0x")) {
    return `https://basescan.org/tx/${txHash}`;
  }
  // Solana-style hashes
  return `https://explorer.solana.com/tx/${txHash}`;
}

interface RequestCardProps {
  request: PurchaseRequestItem;
  currency: string;
  onUpdate: () => void;
}

const statusVariant: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  approved: "default",
  auto_approved: "default",
  completed: "default",
  pending: "outline",
  rejected: "destructive",
  failed: "destructive",
  expired: "secondary",
};

export const RequestCard = memo(function RequestCard({ request: req, currency, onUpdate }: RequestCardProps) {
  const reqCurrency = req.currency || currency;
  const [loading, setLoading] = useState(false);

  async function handleAction(action: "approve" | "reject") {
    setLoading(true);
    try {
      if (action === "approve") {
        await api.approveRequest(req.id);
      } else {
        await api.rejectRequest(req.id);
      }
      track("request_reviewed", { action, category: req.category });
      const count = parseInt(localStorage.getItem("review_count") || "0", 10);
      localStorage.setItem("review_count", String(count + 1));
      onUpdate();
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.detail : "Action failed",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardContent className="flex items-start gap-3 py-3 sm:items-center sm:gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
            <span className="font-medium">
              {formatMoney(parseFloat(req.amount), reqCurrency)}
            </span>
            <Badge variant="outline" className="text-xs">
              {req.category}
            </Badge>
            {req.original_category && (
              <span className="text-xs text-muted-foreground">
                ({req.original_category})
              </span>
            )}
            <Badge variant={statusVariant[req.status] ?? "secondary"} className="text-xs">
              {req.status}
            </Badge>
            {req.settlement_method && (
              <Badge variant="outline" className="text-xs font-mono">
                {req.settlement_method === "x402" ? `x402 · ${req.settlement_currency || "USDC"}` : req.settlement_method}
              </Badge>
            )}
          </div>
          <div className="mt-0.5 text-base text-muted-foreground truncate">
            {req.merchant && <span>{req.merchant}</span>}
            {req.merchant && req.description && <span> — </span>}
            {req.description && <span>{req.description}</span>}
          </div>
          {req.agent_comment && (
            <div className="mt-1 text-base text-muted-foreground italic truncate">
              &ldquo;{req.agent_comment}&rdquo;
            </div>
          )}
          {(req.status === "completed" || req.status === "failed") && (
            <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
              <span>
                {req.status === "completed" ? (
                  <Check className="inline h-3 w-3 mr-0.5 text-green-600 dark:text-green-400" />
                ) : (
                  <X className="inline h-3 w-3 mr-0.5 text-destructive" />
                )}
                {req.status === "completed" ? "Confirmed by agent" : "Purchase failed"}
                {req.completed_at && (
                  <> — {new Date(req.completed_at).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" })}</>
                )}
              </span>
              {req.actual_amount && req.actual_amount !== req.amount && (
                <span>Actual: {formatMoney(parseFloat(req.actual_amount), reqCurrency)}</span>
              )}
              {req.receipt_url && (
                <a
                  href={req.receipt_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                >
                  <ExternalLink className="h-3 w-3" />
                  Receipt
                </a>
              )}
              {req.tx_hash && (
                <a
                  href={getTxExplorerUrl(req.tx_hash)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 font-mono text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                >
                  <Link2 className="h-3 w-3" />
                  {req.tx_hash.slice(0, 6)}...{req.tx_hash.slice(-4)}
                </a>
              )}
            </div>
          )}
          {req.rejection_reason && (
            <div className="mt-1 text-xs text-destructive truncate">
              {req.rejection_reason}
            </div>
          )}
          <div className="text-xs text-muted-foreground">
            {new Date(req.created_at).toLocaleString(undefined, { timeZoneName: "short" })}
          </div>
        </div>

        {req.status === "pending" && (
          <div className="flex gap-1 shrink-0">
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8 text-green-600"
              onClick={() => handleAction("approve")}
              disabled={loading}
            >
              <Check className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8 text-destructive"
              onClick={() => handleAction("reject")}
              disabled={loading}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
});
