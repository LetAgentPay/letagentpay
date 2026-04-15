"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { ChevronRight } from "lucide-react";

const categories = [
  "accommodation",
  "clothing",
  "education",
  "electronics",
  "entertainment",
  "flights",
  "food_delivery",
  "gas",
  "groceries",
  "health",
  "household",
  "other",
  "restaurants",
  "subscriptions",
  "taxi",
  "transport",
];

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

const x402Endpoints: EndpointInfo[] = [
  {
    method: "POST",
    path: "/x402/authorize",
    desc: "Request authorization for an x402 payment",
    request: [
      { name: "payment_requirements", type: "object", required: true, desc: "x402 payment details (scheme, network, amount, asset, pay_to, resource)" },
      { name: "max_amount_usd", type: "number", required: true, desc: "Maximum amount in USD" },
      { name: "category", type: "string", desc: "Purchase category (default: api)" },
    ],
    response: [
      { name: "authorized", type: "boolean", desc: "Whether the payment is authorized" },
      { name: "authorization_id", type: "string", desc: "Authorization ID (use in report)" },
      { name: "reason", type: "string", desc: "Decline reason (if not authorized)" },
      { name: "expires_at", type: "string", desc: "Authorization expiry (ISO 8601)" },
      { name: "remaining_daily_budget", type: "number", desc: "Remaining daily budget" },
    ],
    note: "Decline reasons: CHAIN_NOT_ALLOWED, DOMAIN_BLOCKED, AMOUNT_EXCEEDS_PER_REQUEST_LIMIT, DAILY_BUDGET_EXCEEDED, MONTHLY_BUDGET_EXCEEDED, BUDGET_EXCEEDED, STABLECOIN_DEPEG, CATEGORY_NOT_ALLOWED",
  },
  {
    method: "POST",
    path: "/x402/report",
    desc: "Report a completed x402 transaction",
    request: [
      { name: "authorization_id", type: "string", required: true, desc: "ID from authorize response" },
      { name: "tx_hash", type: "string", required: true, desc: "On-chain transaction hash" },
      { name: "actual_amount_usd", type: "number", desc: "Actual amount paid in USD" },
    ],
    response: [
      { name: "recorded", type: "boolean", desc: "Whether the report was recorded" },
      { name: "transaction_id", type: "string", desc: "Transaction record ID" },
    ],
    note: "Duplicate reports (same authorization_id) return 409 Conflict.",
  },
  {
    method: "GET",
    path: "/x402/budget",
    desc: "Check x402 budget and wallets",
    response: [
      { name: "budget", type: "string", desc: "Total budget" },
      { name: "spent", type: "string", desc: "Amount spent" },
      { name: "remaining", type: "string", desc: "Available budget" },
      { name: "x402_policy", type: "object", desc: "x402-specific policy (chains, domains, limits)" },
      { name: "wallets", type: "array", desc: "Registered wallet addresses" },
    ],
  },
  {
    method: "POST",
    path: "/x402/wallets",
    desc: "Register a wallet address",
    request: [
      { name: "wallet_address", type: "string", required: true, desc: "Wallet address" },
      { name: "chain", type: "string", required: true, desc: "Chain: base, base-sepolia, ethereum, solana" },
      { name: "wallet_provider", type: "string", desc: "Provider name (coinbase, crossmint, privy)" },
    ],
  },
];

const endpoints: EndpointInfo[] = [
  {
    method: "POST",
    path: "/agent-api/requests",
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
    path: "/agent-api/requests/{id}",
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
    path: "/agent-api/requests/{id}/confirm",
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
    path: "/agent-api/budget",
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
    path: "/agent-api/policy",
    desc: "View current policy",
    response: [
      { name: "policy", type: "object", desc: "Full policy JSON (per_request_limit, daily_limit, allowed_categories, schedule, auto_approve, etc.)" },
    ],
  },
  {
    method: "GET",
    path: "/agent-api/categories",
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
      ? "text-yellow-700 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-950"
      : "text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-950";

  return (
    <div className="border-b last:border-b-0">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm hover:bg-muted/50 transition-colors"
      >
        <ChevronRight
          className={`h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform ${open ? "rotate-90" : ""}`}
        />
        <span className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-mono font-medium ${methodColor}`}>
          {ep.method}
        </span>
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

function ApiEndpoints() {
  return (
    <>
      <Card>
        <CardContent className="py-4">
          <div className="flex items-baseline justify-between gap-4 mb-2">
            <h4 className="font-medium">API Endpoints</h4>
            <a
              href="/openapi.yaml"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary underline hover:no-underline"
            >
              OpenAPI spec
            </a>
          </div>
          <div className="rounded border divide-y-0 overflow-hidden">
            {endpoints.map((ep) => (
              <EndpointRow key={`${ep.method} ${ep.path}`} ep={ep} />
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="py-4">
          <h4 className="font-medium mb-2">x402 Endpoints</h4>
          <div className="rounded border divide-y-0 overflow-hidden">
            {x402Endpoints.map((ep) => (
              <EndpointRow key={`${ep.method} ${ep.path}`} ep={ep} />
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

export default function GuidePage() {
  return (
    <div className="space-y-8">
      <h2 className="text-xl font-bold">Guide</h2>

      {/* How It Works */}
      <section className="space-y-3">
        <h3 className="text-lg font-semibold">How It Works</h3>
        <p className="text-base text-muted-foreground">
          LetAgentPay is a policy middleware between your AI agents and money.
          It does not process payments — it decides whether a purchase is
          allowed.
        </p>
        <div className="rounded-md border bg-muted/50 p-4 text-sm space-y-2 font-mono">
          <p>
            1. Agent sends a purchase request →{" "}
            <span className="text-muted-foreground">POST /agent-api/requests</span>
          </p>
          <p>
            2. Policy engine runs 8 checks →{" "}
            <span className="text-muted-foreground">
              status, category, per-request limit, schedule, daily/weekly/monthly
              limits, budget
            </span>
          </p>
          <p>3. Result:</p>
          <ul className="ml-4 space-y-1">
            <li>
              <span className="text-green-600 dark:text-green-400">auto_approved</span>{" "}
              — all checks passed + within auto-approve threshold
            </li>
            <li>
              <span className="text-yellow-600 dark:text-yellow-400">pending</span>{" "}
              — checks passed, awaiting your manual review
            </li>
            <li>
              <span className="text-red-600 dark:text-red-400">rejected</span>{" "}
              — a policy check failed
            </li>
          </ul>
          <p>
            4. Budget is charged on approval (spent += amount). Agent then
            reports the result →{" "}
            <span className="text-muted-foreground">
              POST /agent-api/requests/&#123;id&#125;/confirm
            </span>
          </p>
          <ul className="ml-4 space-y-1 text-muted-foreground">
            <li>
              If the actual amount differs — spent is adjusted automatically
            </li>
            <li>
              Agent can attach a receipt URL for record-keeping
            </li>
          </ul>
        </div>

        <h4 className="text-sm font-semibold mt-4">x402 Crypto-Micropayments</h4>
        <p className="text-base text-muted-foreground">
          For on-chain payments (USDC on Base), agents use the x402 API instead.
          Same policy engine, different payment rail.
        </p>
        <div className="rounded-md border bg-muted/50 p-4 text-sm space-y-2 font-mono">
          <p>
            1. Agent gets HTTP 402 from a resource server
          </p>
          <p>
            2. Agent asks LAP for authorization →{" "}
            <span className="text-muted-foreground">POST /x402/authorize</span>
          </p>
          <p>
            3. Policy engine checks: chain, domain, category, limits, budget →{" "}
            <span className="text-green-600 dark:text-green-400">authorized</span> or{" "}
            <span className="text-red-600 dark:text-red-400">declined</span>
          </p>
          <p>
            4. Agent signs transaction with its own wallet → pays on-chain
          </p>
          <p>
            5. Agent reports tx_hash →{" "}
            <span className="text-muted-foreground">POST /x402/report</span>
          </p>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          LetAgentPay never holds keys or funds. The agent pays from its own wallet.
          LAP only authorizes and logs.
        </p>
      </section>

      {/* Sandbox */}
      <section className="space-y-3">
        <h3 className="text-lg font-semibold">Try It — Sandbox</h3>
        <p className="text-base text-muted-foreground">
          The{" "}
          <Link href="/dashboard/sandbox" className="underline font-medium text-foreground">
            Sandbox
          </Link>{" "}
          lets you test the entire system without affecting your real agents.
          Sandbox agents are completely isolated — they have their own budgets,
          policies, and request history.
        </p>
        <div className="rounded-md border bg-muted/50 p-4 text-sm space-y-2 font-mono">
          <p>1. Go to{" "}
            <Link href="/dashboard/sandbox" className="underline text-foreground">
              Sandbox
            </Link>{" "}
            → click <strong>Create Sandbox Agent</strong>
          </p>
          <p>2. Agent is created with $100 budget and auto-approve under $50</p>
          <p>3. Click <strong>Edit Policy</strong> to customize rules (limits, categories, schedule)</p>
          <p>4. Use <strong>Quick Send</strong> buttons to fire test requests instantly</p>
          <p>5. Watch the budget bar update and see policy checks for each request</p>
          <p>6. Try <strong>Custom Request</strong> to test specific amounts and categories</p>
          <p>7. Approve or reject <strong>pending</strong> requests in the list below</p>
        </div>
        <p className="text-sm text-muted-foreground">
          Sandbox agents don&apos;t appear on the Home page and vice versa. You can
          create multiple sandbox agents with different policies to compare
          behavior. Archive or delete sandbox agents when done.
        </p>
      </section>

      {/* Quick Start */}
      <section className="space-y-3">
        <h3 className="text-lg font-semibold">Quick Start</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                1. Create an Agent
              </CardTitle>
            </CardHeader>
            <CardContent className="text-base text-muted-foreground">
              Go to{" "}
              <Link href="/dashboard" className="underline font-medium text-foreground">
                Home
              </Link>{" "}
              and click <strong>New Agent</strong>. Give it a name and
              an optional description.
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                2. Set Up a Policy
              </CardTitle>
            </CardHeader>
            <CardContent className="text-base text-muted-foreground">
              Describe spending rules in plain language — AI will convert them
              to a structured policy. You can set limits, categories, schedules,
              and auto-approve rules.
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                3. Top Up Agent Budget
              </CardTitle>
            </CardHeader>
            <CardContent className="text-base text-muted-foreground">
              Click the budget bar on the agent card to top it up. Without a
              budget, all requests will be rejected. You can also configure
              auto top-up to replenish the budget automatically.
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                4. Connect Your Agent
              </CardTitle>
            </CardHeader>
            <CardContent className="text-base text-muted-foreground">
              Click <strong>Connect</strong> on the agent card to get the
              token and code examples. See the{" "}
              <a href="#integration" className="underline font-medium text-foreground">
                Integration
              </a>{" "}
              section below.
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Three Levels of Spending Control */}
      <section className="space-y-3">
        <h3 className="text-lg font-semibold">
          Three Levels of Spending Control
        </h3>
        <p className="text-base text-muted-foreground">
          Every purchase request goes through checks at multiple levels. All
          three must pass for the request to be approved.
        </p>

        <div className="space-y-3">
          <Card className="border-l-4 border-l-blue-500">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Level 1 — Agent Policy
              </CardTitle>
            </CardHeader>
            <CardContent className="text-base text-muted-foreground space-y-2">
              <p>
                Fine-grained rules for a specific agent. Configured via the{" "}
                <strong>Setup Policy</strong> chat.
              </p>
              <ul className="list-disc ml-4 space-y-1">
                <li>Per-request limit (e.g. max $50 per purchase)</li>
                <li>Daily, weekly, monthly spending limits</li>
                <li>Allowed or blocked categories</li>
                <li>Schedule (e.g. only weekdays 9am-6pm)</li>
                <li>
                  Auto-approve rules (e.g. auto-approve up to $20 for
                  groceries)
                </li>
              </ul>
              <p>
                <Link
                  href="/dashboard"
                  className="underline font-medium text-foreground"
                >
                  Home
                </Link>{" "}
                → select agent → <strong>Setup Policy</strong> /{" "}
                <strong>Edit Policy</strong>
              </p>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-green-500">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Level 2 — Agent Budget
              </CardTitle>
            </CardHeader>
            <CardContent className="text-base text-muted-foreground space-y-2">
              <p>
                The total spending cap for this agent. Even if all policy
                checks pass, a request is rejected if the remaining budget is
                insufficient.
              </p>
              <p>
                Budget works like a <strong>balance</strong> — you top it up,
                and spending reduces the remaining amount. You can also
                withdraw unused funds.
              </p>
              <p>
                <strong>Auto top-up</strong> — set a threshold so the budget
                is automatically replenished when the balance drops below a
                certain amount. Configure it on the agent card.
              </p>
              <p>
                When a request is <strong>pending</strong>, the amount is{" "}
                <strong>held</strong> (reserved) so that multiple pending
                requests don&apos;t exceed the budget.
              </p>
              <p>
                <Link
                  href="/dashboard"
                  className="underline font-medium text-foreground"
                >
                  Home
                </Link>{" "}
                → click the budget bar on the agent card to top up
              </p>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-purple-500">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                Level 3 — Account Budget Rules
              </CardTitle>
            </CardHeader>
            <CardContent className="text-base text-muted-foreground space-y-2">
              <p>
                Account-wide spending limits that apply across{" "}
                <strong>all agents</strong>. Even if an agent&apos;s own policy
                and budget allow a purchase, account rules can still reject it.
              </p>
              <ul className="list-disc ml-4 space-y-1">
                <li>Daily, weekly, monthly, or total limits</li>
                <li>
                  Day-of-week conditions (e.g. different limits on weekdays
                  vs. weekends)
                </li>
                <li>
                  Time-bound rules (e.g. $100 limit during a specific flight)
                </li>
                <li>Priority-based conflict resolution</li>
              </ul>
              <p>
                <Link
                  href="/dashboard/settings"
                  className="underline font-medium text-foreground"
                >
                  Settings
                </Link>{" "}
                → Account Budget Rules
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="rounded-md border bg-muted/50 p-4 text-sm font-mono">
          <p className="font-semibold mb-1">Check order:</p>
          <p>
            Agent Policy (8 checks) → Agent Budget → Account Budget Rules
          </p>
          <p className="text-muted-foreground mt-1">
            If agent policy rejects — account rules are not checked.
          </p>
        </div>
      </section>

      {/* Auto-Approve */}
      <section className="space-y-3">
        <h3 className="text-lg font-semibold">Auto-Approve</h3>
        <p className="text-base text-muted-foreground">
          By default, every request that passes policy checks goes to{" "}
          <strong>pending</strong> — you review and approve it manually. Auto-approve
          lets certain requests skip that step and get approved instantly.
        </p>

        <Card>
          <CardContent className="py-4 space-y-3 text-base">
            <p className="font-medium">How to enable</p>
            <p className="text-muted-foreground">
              Go to{" "}
              <Link href="/dashboard" className="underline font-medium text-foreground">
                Home
              </Link>{" "}
              → select agent → <strong>Setup Policy</strong>. Describe auto-approve
              rules in plain language, for example:
            </p>
            <pre className="overflow-x-auto rounded bg-muted p-3 text-xs">
{`"Auto-approve purchases up to $20 in groceries and food_delivery"
"Auto-approve everything under $5"
"No auto-approve, I want to review all requests manually"`}
            </pre>
            <p className="text-muted-foreground">
              AI will convert this into a structured policy. The result will have three
              parameters:
            </p>
            <div className="rounded-md border bg-muted/50 p-3 text-xs font-mono space-y-1">
              <p>
                <span className="text-foreground font-medium">enabled</span>{" "}
                — on/off (default: off)
              </p>
              <p>
                <span className="text-foreground font-medium">max_amount</span>{" "}
                — max amount to auto-approve (optional, no limit if not set)
              </p>
              <p>
                <span className="text-foreground font-medium">categories</span>{" "}
                — list of categories for auto-approve (optional, all categories if not set)
              </p>
            </div>

            <p className="font-medium mt-2">Decision flow</p>
            <div className="rounded-md border bg-muted/50 p-3 text-xs font-mono space-y-1">
              <p>1. All 8 policy checks pass? → No → <span className="text-red-600 dark:text-red-400">rejected</span></p>
              <p>2. Account budget rules pass? → No → <span className="text-red-600 dark:text-red-400">rejected</span></p>
              <p>3. Auto-approve enabled? → No → <span className="text-yellow-600 dark:text-yellow-400">pending</span> (manual review)</p>
              <p>4. Amount ≤ max_amount? → No → <span className="text-yellow-600 dark:text-yellow-400">pending</span></p>
              <p>5. Category in auto-approve list? → No → <span className="text-yellow-600 dark:text-yellow-400">pending</span></p>
              <p>6. All conditions met → <span className="text-green-600 dark:text-green-400">auto_approved</span></p>
            </div>

            <p className="font-medium mt-2">Example policy JSON</p>
            <pre className="overflow-x-auto rounded bg-muted p-3 text-xs">
{`{
  "per_request_limit": 100,
  "daily_limit": 200,
  "allowed_categories": ["groceries", "food_delivery"],
  "auto_approve": {
    "enabled": true,
    "max_amount": 20,
    "categories": ["groceries", "food_delivery"]
  }
}`}
            </pre>
            <p className="text-muted-foreground text-xs">
              With this policy: a $15 groceries request → auto-approved. A $50 groceries
              request → pending (exceeds auto-approve max). A $15 electronics request →
              rejected (category not allowed).
            </p>
          </CardContent>
        </Card>
      </section>

      {/* Notifications */}
      <section className="space-y-3">
        <h3 className="text-lg font-semibold">Notifications</h3>
        <p className="text-base text-muted-foreground">
          Get notified when agents request purchases, and approve or reject
          directly from any channel.
        </p>

        <div className="space-y-3">
          <Card>
            <CardContent className="py-4 space-y-3 text-base">
              <p className="font-medium">Available Channels</p>
              <div className="rounded-md border bg-muted/50 p-3 text-sm space-y-2">
                <p>
                  <span className="font-medium text-foreground">Email</span>{" "}
                  <span className="text-muted-foreground">
                    — receive notifications with one-click Approve / Reject
                    action links directly in the email
                  </span>
                </p>
                <p>
                  <span className="font-medium text-foreground">Telegram</span>{" "}
                  <span className="text-muted-foreground">
                    — connect a Telegram bot and approve or reject with inline
                    buttons in the chat
                  </span>
                </p>
                <p>
                  <span className="font-medium text-foreground">Browser Push</span>{" "}
                  <span className="text-muted-foreground">
                    — native browser push notifications for real-time alerts
                  </span>
                </p>
              </div>

              <p className="font-medium mt-2">How to set up</p>
              <p className="text-muted-foreground">
                Go to{" "}
                <Link
                  href="/dashboard/settings"
                  className="underline font-medium text-foreground"
                >
                  Settings
                </Link>{" "}
                → <strong>Notifications</strong> to enable and connect your
                preferred channels. For Telegram, follow the deep-link to
                connect your account to the bot.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Integration */}
      <section id="integration" className="space-y-3">
        <h3 className="text-lg font-semibold">Integrate Your Agent</h3>
        <p className="text-base text-muted-foreground">
          Use the agent token to authenticate API requests. Get your token on
          the{" "}
          <Link href="/dashboard" className="underline font-medium text-foreground">
            agent card
          </Link>{" "}
          or the <strong>Connect</strong> page.
        </p>

        <Tabs defaultValue="curl">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="curl">curl</TabsTrigger>
            <TabsTrigger value="python">Python</TabsTrigger>
            <TabsTrigger value="js">JavaScript</TabsTrigger>
            <TabsTrigger value="mcp">MCP</TabsTrigger>
            <TabsTrigger value="x402">x402</TabsTrigger>
          </TabsList>

          <TabsContent value="curl">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  Quick Test with curl
                </CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="overflow-x-auto rounded bg-muted p-4 text-xs">
{`curl -X POST YOUR_API_URL/agent-api/requests \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "amount": 25.00,
    "category": "groceries",
    "merchant_name": "SuperMart",
    "description": "Weekly groceries"
  }'`}
                </pre>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="python">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Python</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="overflow-x-auto rounded bg-muted p-4 text-xs">
{`import requests

TOKEN = "YOUR_TOKEN"
API = "YOUR_API_URL/agent-api"

# Create a purchase request
resp = requests.post(
    f"{API}/requests",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={
        "amount": 25.00,
        "category": "groceries",
        "merchant_name": "SuperMart",
        "description": "Weekly groceries",
    },
)
result = resp.json()
print(result["status"])  # auto_approved / pending / rejected

# Check remaining budget
budget = requests.get(
    f"{API}/budget",
    headers={"Authorization": f"Bearer {TOKEN}"},
)
print(budget.json())`}
                </pre>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="js">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">JavaScript / Node.js</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="overflow-x-auto rounded bg-muted p-4 text-xs">
{`const TOKEN = "YOUR_TOKEN";
const API = "YOUR_API_URL/agent-api";

const resp = await fetch(\`\${API}/requests\`, {
  method: "POST",
  headers: {
    Authorization: \`Bearer \${TOKEN}\`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    amount: 25.0,
    category: "groceries",
    merchant_name: "SuperMart",
    description: "Weekly groceries",
  }),
});
const result = await resp.json();
console.log(result.status); // auto_approved / pending / rejected`}
                </pre>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="mcp">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  MCP (Model Context Protocol)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-base text-muted-foreground">
                  Add to your Claude Desktop or compatible MCP client config:
                </p>
                <pre className="overflow-x-auto rounded bg-muted p-4 text-xs">
{`{
  "mcpServers": {
    "letagentpay": {
      "command": "npx",
      "args": ["-y", "letagentpay-mcp"],
      "env": {
        "LETAGENTPAY_TOKEN": "YOUR_TOKEN"
      }
    }
  }
}`}
                </pre>
                <p className="text-base text-muted-foreground">
                  Available tools: <code>request_purchase</code>,{" "}
                  <code>check_budget</code>, <code>list_categories</code>,{" "}
                  <code>my_requests</code>,{" "}
                  <code>x402_authorize</code>, <code>x402_report</code>,{" "}
                  <code>x402_budget</code>
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="x402">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  x402 Crypto-Micropayments (Python SDK)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="overflow-x-auto rounded bg-muted p-4 text-xs">
{`from letagentpay import LetAgentPay

client = LetAgentPay(token="YOUR_TOKEN")

# Agent gets HTTP 402 from a resource — ask LAP for authorization
auth = client.x402.authorize(
    amount_usd=0.05,
    asset="USDC",
    network="eip155:8453",       # Base mainnet
    pay_to="0xMerchant...",
    resource_url="https://api.example.com/data",
    category="api",
)

if auth.authorized:
    # Agent signs tx with its OWN wallet (not LAP's)
    # ... your wallet signing code here ...

    # Report tx_hash for audit
    client.x402.report(
        authorization_id=auth.authorization_id,
        tx_hash="0xabc123...",
    )
else:
    print(f"Declined: {auth.reason}")
    # DAILY_BUDGET_EXCEEDED, DOMAIN_BLOCKED, etc.`}
                </pre>
                <p className="text-xs text-muted-foreground mt-3">
                  x402 policy is configured in the agent&apos;s policy JSON under the{" "}
                  <code>x402</code> key: <code>allowed_chains</code>,{" "}
                  <code>blocked_domains</code>, <code>max_per_request</code>.
                  General limits (daily, monthly, budget) apply to both fiat and x402 payments.
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* API Endpoints */}
        <ApiEndpoints />

        {/* Categories */}
        <Card>
          <CardContent className="py-4">
            <h4 className="font-medium mb-2">Categories</h4>
            <div className="flex flex-wrap gap-1.5">
              {categories.map((cat) => (
                <span
                  key={cat}
                  className="rounded-md bg-muted px-2 py-0.5 text-xs font-mono"
                >
                  {cat}
                </span>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Categories are resolved automatically. Your agent can send any
              category name — the system will try to match it: first by exact
              name, then via a built-in alias table (e.g.{" "}
              <code>uber</code> → <code>taxi</code>,{" "}
              <code>coffee</code> → <code>restaurants</code>), and finally
              via AI classification. If no match is found, it falls back to{" "}
              <code>other</code>. The original category sent by the agent is
              preserved in the request details.
            </p>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
