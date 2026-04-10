import Link from "next/link";
import type { Metadata } from "next";
import { PublicNav } from "@/components/public-nav";
import { PublicFooter } from "@/components/public-footer";

export const metadata: Metadata = {
  title: "ASPS — Agent Spending Policy Specification",
  description:
    "An open, vendor-neutral specification for AI agent spending control. v1: single-agent policies. v2: multi-agent missions with shared budgets, phases, and risk scoring.",
};

const POLICY_EXAMPLE = `{
  "version": "1.0",
  "daily_limit": 500,
  "weekly_limit": 2000,
  "per_request_limit": 200,
  "allowed_categories": ["groceries", "food_delivery", "subscriptions"],
  "schedule": {
    "timezone": "America/New_York",
    "default": { "allow": "08:00-22:00" },
    "overrides": [
      { "days": ["sat", "sun"], "allow": "10:00-18:00", "daily_limit": 100 },
      { "days": ["wed"], "deny": true }
    ]
  },
  "auto_approve": {
    "enabled": true,
    "max_amount": 50,
    "categories": ["groceries", "food_delivery"]
  }
}`;

const MISSION_EXAMPLE = `{
  "version": "2.0",
  "name": "Barcelona trip, May 15-22",
  "budget": 5000,
  "currency": "USD",
  "agents": {
    "flights": { "policy": { "allowed_categories": ["flights"] } },
    "hotel":   { "policy": { "allowed_categories": ["accommodation"] } },
    "fun":     { "policy": { "allowed_categories": ["entertainment"] } }
  },
  "phases": [
    { "name": "booking", "agents": ["flights", "hotel"],
      "allocation": { "type": "share", "percent": 70 } },
    { "name": "activities", "agents": ["fun"],
      "allocation": { "type": "remaining" } }
  ],
  "constraints": [
    { "type": "dependency", "agent": "hotel",
      "requires": "flights", "condition": "confirmed" }
  ]
}`;

const CHECKS = [
  { name: "Agent status", desc: "Is the agent active?" },
  { name: "Category", desc: "Is this spending category allowed?" },
  { name: "Per-request limit", desc: "Does this single purchase exceed the cap?" },
  { name: "Schedule", desc: "Is spending allowed right now?" },
  { name: "Daily limit", desc: "Would this push today's total over the daily cap?" },
  { name: "Weekly limit", desc: "Same check for the current week" },
  { name: "Monthly limit", desc: "Same check for the current month" },
  { name: "Total budget", desc: "Would this exceed the agent's overall budget?" },
  { name: "Account rules", desc: "Cross-agent budget rules at the account level" },
];

const V2_FEATURES = [
  {
    title: "Mission coordination",
    desc: "Multiple agents work toward a common goal with a shared budget. Phases, dependencies, and dynamic allocation.",
  },
  {
    title: "5 allocation strategies",
    desc: "Fixed, percentage share, remaining, per-agent, and competitive. Budget flows dynamically based on actual spending.",
  },
  {
    title: "Phase transitions",
    desc: "Gates, escalation, timeouts. Agents unlock as phases complete. Rollback on failure.",
  },
  {
    title: "Cross-agent constraints",
    desc: "Dependencies, combined limits, conditional rules, exclusions, priority ordering between agents.",
  },
  {
    title: "Risk scoring",
    desc: "Anomaly detection based on agent behavior history. Flag unusual amounts, categories, timing, or frequency.",
  },
  {
    title: "Escalation model",
    desc: "Same agent, increasing authority. L1 can offer 5% discount, L2 can refund $100, L3 can compensate $500.",
  },
];

export default function AspsPage() {
  return (
    <div className="min-h-screen bg-background">
      <PublicNav />

      {/* Hero */}
      <section className="mx-auto max-w-4xl px-4 py-20 text-center">
        <p className="text-sm font-medium tracking-widest text-muted-foreground uppercase">
          Open Specification
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">
          Agent Spending Policy Specification
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          A vendor-neutral format for AI agent spending control.
          From single-agent budgets to multi-agent mission coordination.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/asps/spec"
            className="rounded-md border px-6 py-2.5 text-sm font-medium hover:bg-muted"
          >
            v1 Spec (Stable)
          </Link>
          <Link
            href="/asps/v2"
            className="rounded-md border px-6 py-2.5 text-sm font-medium hover:bg-muted"
          >
            v2 Spec (Draft)
          </Link>
          <a
            href="/schemas/asps/v0.1/policy.json"
            className="rounded-md border px-6 py-2.5 text-sm font-medium hover:bg-muted"
          >
            v1 JSON Schema
          </a>
        </div>
      </section>

      {/* Two versions */}
      <section className="border-t bg-muted/50">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <div className="grid gap-8 lg:grid-cols-2">
            {/* v1 */}
            <div className="rounded-lg border bg-background p-6">
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold">ASPS v1</h2>
                <span className="rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700 dark:bg-green-950 dark:text-green-400">
                  Stable
                </span>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">
                Single-agent spending policies. Budgets, limits, categories,
                schedules, auto-approval. Implemented in LetAgentPay.
              </p>
              <ul className="mt-4 space-y-1.5 text-sm text-muted-foreground">
                <li>9 deterministic checks</li>
                <li>Account-level budget rules</li>
                <li>Fund holding for pending requests</li>
                <li>JSON Schema validation</li>
              </ul>
              <Link
                href="/asps/spec"
                className="mt-4 inline-block text-sm font-medium text-primary underline hover:no-underline"
              >
                Read v1 spec
              </Link>
            </div>

            {/* v2 */}
            <div className="rounded-lg border bg-background p-6">
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold">ASPS v2</h2>
                <span className="rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-700 dark:bg-yellow-950 dark:text-yellow-400">
                  Draft
                </span>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">
                Multi-agent mission coordination. Shared budgets, phases,
                dependencies, dynamic allocation, risk scoring.
              </p>
              <ul className="mt-4 space-y-1.5 text-sm text-muted-foreground">
                <li>Mission-level budget orchestration</li>
                <li>5 allocation strategies (incl. competitive)</li>
                <li>Phase transitions and constraints</li>
                <li>Anomaly detection via risk scoring</li>
              </ul>
              <div className="mt-4 flex gap-4">
                <Link
                  href="/asps/v2"
                  className="text-sm font-medium text-primary underline hover:no-underline"
                >
                  Read v2 spec
                </Link>
                <Link
                  href="/asps/use-cases"
                  className="text-sm font-medium text-primary underline hover:no-underline"
                >
                  Use cases
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* v1: Example */}
      <section className="border-t">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold">v1: Single-agent policy</h2>
            <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-950 dark:text-green-400">
              Stable
            </span>
          </div>
          <div className="mt-8 grid gap-8 lg:grid-cols-2">
            <pre className="overflow-x-auto rounded-lg bg-muted p-5 text-sm leading-relaxed">
              <code>{POLICY_EXAMPLE}</code>
            </pre>
            <div>
              <h3 className="font-semibold">This policy says:</h3>
              <ul className="mt-3 space-y-2">
                {[
                  "Up to $500/day, $2,000/week, $200 per purchase",
                  "Only groceries, food delivery, and subscriptions",
                  "Weekdays 08:00\u201322:00, weekends 10:00\u201318:00, no Wednesdays",
                  "Weekend daily limit reduced to $100",
                  "Groceries and food delivery under $50 \u2014 auto-approved",
                ].map((line, i) => (
                  <li key={i} className="flex items-start gap-2 text-muted-foreground">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                    {line}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* v1: 9 Checks */}
      <section className="border-t bg-muted/50">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-2xl font-bold">9 standard checks</h2>
          <p className="mt-3 text-muted-foreground">
            Every spending request is evaluated against these checks, in order.
            All checks run (no short-circuit) to provide a complete report.
          </p>
          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {CHECKS.map((check, i) => (
              <div key={i} className="rounded-lg border bg-background p-4">
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                    {i + 1}
                  </span>
                  <span className="font-semibold text-sm">{check.name}</span>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{check.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* v2: Mission example */}
      <section className="border-t">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold">v2: Mission coordination</h2>
            <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700 dark:bg-yellow-950 dark:text-yellow-400">
              Draft
            </span>
          </div>
          <p className="mt-3 text-muted-foreground">
            Multiple agents, one goal, shared budget. Phases unlock as work progresses.
            Budget flows dynamically based on actual spending.
          </p>
          <div className="mt-8 grid gap-8 lg:grid-cols-2">
            <pre className="overflow-x-auto rounded-lg bg-muted p-5 text-sm leading-relaxed">
              <code>{MISSION_EXAMPLE}</code>
            </pre>
            <div>
              <h3 className="font-semibold">This mission says:</h3>
              <ul className="mt-3 space-y-2">
                {[
                  "$5,000 total budget for a Barcelona trip",
                  "3 agents: flights, hotel, entertainment",
                  "Booking phase gets 70% ($3,500), dynamic reallocation",
                  "Hotel can\u2019t book until flights are confirmed",
                  "Activities phase gets whatever remains",
                  "Cheap flights = more budget for hotel and fun",
                ].map((line, i) => (
                  <li key={i} className="flex items-start gap-2 text-muted-foreground">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                    {line}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* v2: Features grid */}
      <section className="border-t bg-muted/50">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-2xl font-bold">What v2 adds</h2>
          <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {V2_FEATURES.map((f) => (
              <div key={f.title}>
                <h3 className="font-semibold">{f.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
              </div>
            ))}
          </div>
          <div className="mt-6 text-center">
            <Link
              href="/asps/use-cases"
              className="text-sm font-medium text-primary underline hover:no-underline"
            >
              See all use cases with visual diagrams &rarr;
            </Link>
          </div>
        </div>
      </section>

      {/* Architecture */}
      <section className="border-t">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-2xl font-bold">Architecture</h2>
          <div className="mt-8 overflow-x-auto rounded-lg bg-muted p-6 font-mono text-sm leading-loose">
            <div>ASPS v2 (missions, phases, allocation, risk scoring)</div>
            <div className="ml-4">&darr;</div>
            <div className="ml-4">ASPS v1 (per-agent policy: limits, categories, schedule)</div>
            <div className="ml-8">&darr;</div>
            <div className="ml-8">9 standard checks &rarr; pass/fail</div>
          </div>
          <p className="mt-4 text-sm text-muted-foreground">
            v2 is a layer above v1, not a replacement. Every agent in a mission still
            uses a v1 policy. Agents can operate independently (v1 only) or as part
            of a mission (v2).
          </p>
        </div>
      </section>

      {/* Resources */}
      <section className="border-t bg-muted/50">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-2xl font-bold">Resources</h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <Link
              href="/asps/spec"
              className="rounded-lg border bg-background p-5 transition-colors hover:border-primary"
            >
              <div className="flex items-center gap-2">
                <h3 className="font-semibold">v1 Specification</h3>
                <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-950 dark:text-green-400">
                  Stable
                </span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Single-agent policies. All objects, fields, evaluation rules,
                conformance requirements.
              </p>
            </Link>
            <Link
              href="/asps/v2"
              className="rounded-lg border bg-background p-5 transition-colors hover:border-primary"
            >
              <div className="flex items-center gap-2">
                <h3 className="font-semibold">v2 Specification</h3>
                <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700 dark:bg-yellow-950 dark:text-yellow-400">
                  Draft
                </span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Mission coordination, phases, constraints, risk scoring.
                Full examples for travel, incident response, competitive search.
              </p>
            </Link>
            <a
              href="/schemas/asps/v0.1/policy.json"
              className="rounded-lg border bg-background p-5 transition-colors hover:border-primary"
            >
              <h3 className="font-semibold">JSON Schema (v1)</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Machine-readable schema for Policy, Schedule, AutoApprove, Request,
                CheckResult, and BudgetRule objects.
              </p>
            </a>
            <Link
              href="/developers"
              className="rounded-lg border bg-background p-5 transition-colors hover:border-primary"
            >
              <h3 className="font-semibold">Reference Implementation</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                LetAgentPay implements the full ASPS v1 spec. Python SDK,
                MCP server, REST API.
              </p>
            </Link>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t">
        <div className="mx-auto max-w-4xl px-4 py-20 text-center">
          <h2 className="text-2xl font-bold">
            We don&apos;t move money. We decide if it should move.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
            ASPS is an open specification. Use it with any payment provider and any
            AI framework.
          </p>
          <div className="mt-8 flex items-center justify-center gap-4">
            <Link
              href="/asps/spec"
              className="rounded-md bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Read the Spec
            </Link>
            <Link
              href="/auth/signin"
              className="rounded-md border px-6 py-2.5 text-sm font-medium hover:bg-muted"
            >
              Try LetAgentPay Free
            </Link>
          </div>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}
