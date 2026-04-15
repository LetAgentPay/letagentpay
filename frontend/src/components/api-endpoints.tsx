"use client";

import { useState } from "react";
import { ChevronRight } from "lucide-react";

interface Param {
  name: string;
  type: string;
  required?: boolean;
  desc: string;
}

interface EndpointInfo {
  method: string;
  path: string;
  desc: string;
  request?: Param[];
  response?: Param[];
  note?: string;
}

const endpoints: EndpointInfo[] = [
  {
    method: "POST",
    path: "/requests",
    desc: "Create a purchase request",
    request: [
      { name: "amount", type: "number", required: true, desc: "Purchase amount (> 0)" },
      { name: "currency", type: "string", desc: "ISO 4217 code (e.g. USD). Defaults to account currency" },
      { name: "category", type: "string", required: true, desc: "Category name — auto-resolved via aliases + AI" },
      { name: "merchant_name", type: "string", desc: "Merchant or store name" },
      { name: "description", type: "string", desc: "What is being purchased" },
      { name: "agent_comment", type: "string", desc: "Agent's reasoning for this purchase (shown to owner)" },
    ],
    response: [
      { name: "request_id", type: "string", desc: "Unique request ID" },
      { name: "status", type: "string", desc: "auto_approved | pending | rejected" },
      { name: "currency", type: "string", desc: "Currency used" },
      { name: "category", type: "string", desc: "Resolved category" },
      { name: "original_category", type: "string", desc: "Category as sent by agent (before resolution)" },
      { name: "policy_check", type: "object", desc: "Detailed results of each policy check" },
      { name: "auto_approved", type: "boolean", desc: "Whether it was auto-approved" },
      { name: "budget_remaining", type: "number", desc: "Remaining budget (only if auto_approved)" },
      { name: "expires_at", type: "string", desc: "Expiry time for pending requests (ISO 8601)" },
    ],
  },
  {
    method: "GET",
    path: "/requests/{id}",
    desc: "Check request status",
    response: [
      { name: "request_id", type: "string", desc: "Unique request ID" },
      { name: "status", type: "string", desc: "Current status: pending | approved | auto_approved | rejected | completed | failed | expired" },
      { name: "amount", type: "number", desc: "Request amount" },
      { name: "category", type: "string", desc: "Resolved category" },
      { name: "created_at", type: "string", desc: "Creation time (ISO 8601)" },
      { name: "reviewed_at", type: "string", desc: "Review time, if reviewed" },
    ],
    note: "Expired pending requests are automatically marked as expired when polled.",
  },
  {
    method: "POST",
    path: "/requests/{id}/confirm",
    desc: "Confirm purchase result",
    request: [
      { name: "success", type: "boolean", required: true, desc: "Whether the purchase succeeded" },
      { name: "actual_amount", type: "number", desc: "Actual amount charged (if different from requested — budget is adjusted)" },
      { name: "receipt_url", type: "string", desc: "URL to receipt or proof of purchase" },
    ],
    response: [
      { name: "request_id", type: "string", desc: "Unique request ID" },
      { name: "status", type: "string", desc: "completed | failed" },
      { name: "actual_amount", type: "string", desc: "Actual amount, if provided" },
    ],
    note: "Only approved or auto_approved requests can be confirmed. If success=false, the spent amount is refunded.",
  },
  {
    method: "GET",
    path: "/budget",
    desc: "Check remaining budget",
    response: [
      { name: "budget", type: "number", desc: "Total budget" },
      { name: "spent", type: "number", desc: "Amount spent" },
      { name: "held", type: "number", desc: "Amount held (reserved by pending requests)" },
      { name: "remaining", type: "number", desc: "Available budget (budget - spent - held)" },
      { name: "currency", type: "string", desc: "Account currency" },
    ],
  },
  {
    method: "GET",
    path: "/policy",
    desc: "View current policy",
    response: [
      { name: "policy", type: "object", desc: "Full policy JSON (per_request_limit, daily_limit, allowed_categories, schedule, auto_approve, etc.)" },
    ],
  },
  {
    method: "GET",
    path: "/categories",
    desc: "List valid categories",
    response: [
      { name: "categories", type: "string[]", desc: "Sorted list of all valid category names" },
    ],
  },
];

function EndpointRow({ ep }: { ep: EndpointInfo }) {
  const [open, setOpen] = useState(false);
  const methodColor =
    ep.method === "POST"
      ? "text-green-700 dark:text-green-300 bg-green-100 dark:bg-green-900"
      : "text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900";

  return (
    <div className="border-b last:border-b-0">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm hover:bg-muted/50 transition-colors"
      >
        <ChevronRight
          className={`h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform ${open ? "rotate-90" : ""}`}
        />
        <code className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${methodColor}`}>
          {ep.method}
        </code>
        <code className="font-medium">{ep.path}</code>
        <span className="text-muted-foreground ml-auto hidden sm:inline">
          {ep.desc}
        </span>
      </button>

      {open && (
        <div className="px-3 pb-3 pt-1 space-y-3 text-sm">
          <p className="text-muted-foreground sm:hidden">{ep.desc}</p>

          {ep.request && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1.5">Request body</p>
              <div className="rounded border bg-muted/30 divide-y">
                {ep.request.map((p) => (
                  <div key={p.name} className="flex flex-col sm:flex-row sm:items-baseline gap-1 px-3 py-1.5">
                    <div className="flex items-baseline gap-1.5">
                      <code className="text-xs font-medium">{p.name}</code>
                      <span className="text-[10px] text-muted-foreground">{p.type}</span>
                      {p.required && (
                        <span className="text-[10px] text-red-500 font-medium">required</span>
                      )}
                    </div>
                    <span className="text-xs text-muted-foreground sm:ml-auto">{p.desc}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {ep.response && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1.5">Response</p>
              <div className="rounded border bg-muted/30 divide-y">
                {ep.response.map((p) => (
                  <div key={p.name} className="flex flex-col sm:flex-row sm:items-baseline gap-1 px-3 py-1.5">
                    <div className="flex items-baseline gap-1.5">
                      <code className="text-xs font-medium">{p.name}</code>
                      <span className="text-[10px] text-muted-foreground">{p.type}</span>
                    </div>
                    <span className="text-xs text-muted-foreground sm:ml-auto">{p.desc}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {ep.note && (
            <p className="text-xs text-muted-foreground italic">{ep.note}</p>
          )}
        </div>
      )}
    </div>
  );
}

const x402Endpoints: EndpointInfo[] = [
  {
    method: "POST",
    path: "/x402/authorize",
    desc: "Authorize an x402 payment",
    request: [
      { name: "payment_requirements", type: "object", required: true, desc: "x402 payment details (scheme, network, amount, asset, pay_to)" },
      { name: "max_amount_usd", type: "number", required: true, desc: "Maximum amount in USD" },
      { name: "category", type: "string", desc: "Purchase category (default: api)" },
    ],
    response: [
      { name: "authorized", type: "boolean", desc: "Whether the payment is authorized" },
      { name: "authorization_id", type: "string", desc: "Authorization ID (use in report)" },
      { name: "reason", type: "string", desc: "Decline reason (if not authorized)" },
      { name: "expires_at", type: "string", desc: "Authorization expiry (ISO 8601)" },
    ],
    note: "Decline reasons: CHAIN_NOT_ALLOWED, DOMAIN_BLOCKED, AMOUNT_EXCEEDS_PER_REQUEST_LIMIT, DAILY_BUDGET_EXCEEDED, BUDGET_EXCEEDED, STABLECOIN_DEPEG",
  },
  {
    method: "POST",
    path: "/x402/report",
    desc: "Report completed x402 transaction",
    request: [
      { name: "authorization_id", type: "string", required: true, desc: "ID from authorize response" },
      { name: "tx_hash", type: "string", required: true, desc: "On-chain transaction hash" },
      { name: "actual_amount_usd", type: "number", desc: "Actual amount paid in USD" },
    ],
  },
  {
    method: "GET",
    path: "/x402/budget",
    desc: "x402 budget, wallets, and policy",
    response: [
      { name: "budget", type: "string", desc: "Total budget" },
      { name: "x402_policy", type: "object", desc: "Allowed chains, domains, per-request limit" },
      { name: "wallets", type: "array", desc: "Registered wallet addresses" },
    ],
  },
  {
    method: "POST",
    path: "/x402/wallets",
    desc: "Register a wallet address",
    request: [
      { name: "wallet_address", type: "string", required: true, desc: "Wallet address" },
      { name: "chain", type: "string", required: true, desc: "base, base-sepolia, ethereum, solana" },
    ],
  },
];

export function ApiEndpoints() {
  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-sm font-medium text-muted-foreground mb-1">Agent API</h4>
        <div className="rounded-lg border divide-y-0">
          {endpoints.map((ep) => (
            <EndpointRow key={`${ep.method}-${ep.path}`} ep={ep} />
          ))}
        </div>
      </div>
      <div>
        <h4 className="text-sm font-medium text-muted-foreground mb-1">x402 API</h4>
        <div className="rounded-lg border divide-y-0">
          {x402Endpoints.map((ep) => (
            <EndpointRow key={`${ep.method}-${ep.path}`} ep={ep} />
          ))}
        </div>
      </div>
    </div>
  );
}