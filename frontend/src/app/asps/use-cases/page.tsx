import Link from "next/link";
import type { Metadata } from "next";
import { PublicNav } from "@/components/public-nav";
import { PublicFooter } from "@/components/public-footer";

export const metadata: Metadata = {
  title: "ASPS v2 Use Cases — Mission Policy in Action",
  description:
    "Real-world scenarios for multi-agent spending coordination: travel planning, incident response, marketing campaigns, procurement, customer service.",
};

/* ── Reusable visual components ── */

function PhaseArrow() {
  return (
    <div className="flex items-center justify-center py-2 text-muted-foreground">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 5v14M5 12l7 7 7-7" />
      </svg>
    </div>
  );
}

function PhaseBox({
  name,
  budget,
  agents,
  highlight,
}: {
  name: string;
  budget: string;
  agents: string[];
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border-2 p-4 text-center ${
        highlight
          ? "border-primary bg-primary/5"
          : "border-border bg-background"
      }`}
    >
      <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {name}
      </div>
      <div className="mt-1 text-lg font-bold">{budget}</div>
      <div className="mt-2 flex flex-wrap justify-center gap-1">
        {agents.map((a) => (
          <span
            key={a}
            className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium"
          >
            {a}
          </span>
        ))}
      </div>
    </div>
  );
}

function BudgetBar({
  segments,
}: {
  segments: { label: string; percent: number; color: string }[];
}) {
  return (
    <div className="mt-4">
      <div className="flex h-8 overflow-hidden rounded-lg border">
        {segments.map((s) => (
          <div
            key={s.label}
            className={`flex items-center justify-center text-xs font-medium ${s.color}`}
            style={{ width: `${s.percent}%` }}
          >
            {s.percent >= 10 && s.label}
          </div>
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
        {segments.map((s) => (
          <span key={s.label} className="flex items-center gap-1">
            <span className={`inline-block h-2.5 w-2.5 rounded-sm ${s.color}`} />
            {s.label} ({s.percent}%)
          </span>
        ))}
      </div>
    </div>
  );
}

function ConstraintLine({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2 rounded border border-dashed px-3 py-1.5 text-xs text-muted-foreground">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </svg>
      {text}
    </div>
  );
}

function ResultBox({ text }: { text: string }) {
  return (
    <div className="rounded-lg border-l-4 border-green-400 bg-green-50 p-4 dark:border-green-600 dark:bg-green-950/30">
      <div className="text-xs font-semibold uppercase tracking-wider text-green-700 dark:text-green-400">
        Result
      </div>
      <p className="mt-1 text-sm text-green-900 dark:text-green-200">{text}</p>
    </div>
  );
}

function EscalationLevel({
  level,
  budget,
  can,
  active,
}: {
  level: string;
  budget: string;
  can: string;
  active?: boolean;
}) {
  return (
    <div
      className={`flex items-center gap-4 rounded-lg border-2 p-4 ${
        active ? "border-primary bg-primary/5" : "border-border"
      }`}
    >
      <div
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
          active
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-muted-foreground"
        }`}
      >
        {level}
      </div>
      <div>
        <div className="font-semibold">{budget}</div>
        <div className="text-xs text-muted-foreground">{can}</div>
      </div>
    </div>
  );
}

function CompetitorCard({
  name,
  result,
  winner,
}: {
  name: string;
  result: string;
  winner?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border-2 p-4 text-center ${
        winner
          ? "border-green-400 bg-green-50 dark:border-green-600 dark:bg-green-950/30"
          : "border-border opacity-60"
      }`}
    >
      <div className="font-semibold">{name}</div>
      <div className="mt-1 text-sm text-muted-foreground">{result}</div>
      {winner && (
        <div className="mt-2 text-xs font-bold text-green-700 dark:text-green-400">
          WINNER
        </div>
      )}
    </div>
  );
}

/* ── Page ── */

export default function UseCasesPage() {
  return (
    <div className="min-h-screen bg-background">
      <PublicNav />

      <div className="mx-auto max-w-4xl px-4 py-12">
        <div className="flex items-center gap-3">
          <Link
            href="/asps"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            &larr; ASPS
          </Link>
        </div>

        <h1 className="mt-4 text-3xl font-bold">ASPS v2 Use Cases</h1>
        <p className="mt-2 text-muted-foreground">
          How Mission Policy coordinates multiple AI agents with shared budgets,
          phases, and constraints.
        </p>

        {/* Quick nav */}
        <nav className="mt-8 flex flex-wrap gap-2">
          {["Travel planning", "Incident response", "Marketing campaign", "Procurement", "Customer service"].map(
            (title) => (
              <a
                key={title}
                href={`#${title.toLowerCase().replace(/ /g, "-")}`}
                className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
              >
                {title}
              </a>
            ),
          )}
        </nav>

        {/* ─── 1. Travel Planning ─── */}
        <section id="travel-planning" className="mt-16">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold">Travel planning</h2>
            <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
              Dynamic allocation
            </span>
          </div>
          <p className="mt-3 text-muted-foreground">
            4 agents plan a $5,000 trip to Barcelona. Budget flows dynamically —
            cheap flights mean a nicer hotel.
          </p>

          {/* Flow diagram */}
          <div className="mt-8 rounded-lg border p-6">
            <div className="text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Total budget: $5,000
            </div>
            <div className="mt-4 space-y-1">
              <PhaseBox
                name="Phase 1: Research"
                budget="$0"
                agents={["Research", "Flights", "Hotel"]}
              />
              <PhaseArrow />
              <PhaseBox
                name="Phase 2: Booking"
                budget="70% → $3,500"
                agents={["Flights", "Hotel"]}
                highlight
              />
              <div className="flex justify-center gap-2 py-2">
                <ConstraintLine text="Hotel waits for Flights" />
                <ConstraintLine text="Combined max 75%" />
              </div>
              <PhaseArrow />
              <PhaseBox
                name="Phase 3: Activities"
                budget="Remaining"
                agents={["Entertainment"]}
              />
            </div>
          </div>

          {/* Budget reallocation illustration */}
          <h3 className="mt-8 font-semibold">Dynamic reallocation in action</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Flights found a deal at $800. Hotel now has access to $2,700 instead of a fixed $1,750.
          </p>
          <BudgetBar
            segments={[
              { label: "Flights $800", percent: 16, color: "bg-blue-400 text-white dark:bg-blue-600" },
              { label: "Hotel $1,900", percent: 38, color: "bg-indigo-400 text-white dark:bg-indigo-600" },
              { label: "Activities $2,300", percent: 46, color: "bg-violet-400 text-white dark:bg-violet-600" },
            ]}
          />

          <div className="mt-6">
            <ResultBox text="Flights: $800. Hotel: $1,900. Activities: $2,300. Total: $5,000. Entertainment budget doubled because the flight agent found a deal." />
          </div>
        </section>

        {/* ─── 2. Incident Response ─── */}
        <section id="incident-response" className="mt-16 border-t pt-16">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold">Incident response</h2>
            <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
              Escalation
            </span>
          </div>
          <p className="mt-3 text-muted-foreground">
            Production is down. AI agents diagnose and fix — with increasing
            authority and budget at each escalation level.
          </p>

          {/* Escalation diagram */}
          <div className="mt-8 space-y-3">
            <EscalationLevel
              level="L0"
              budget="$0 — Detection"
              can="Monitor alerts, no spending"
            />
            <EscalationLevel
              level="L1"
              budget="$500 — Diagnosis"
              can="Spin up test instances, run diagnostics (2h timeout)"
              active
            />
            <EscalationLevel
              level="L2"
              budget="$5,000 — Remediation"
              can="Scale infrastructure, deploy hotfixes (4h timeout)"
            />
            <EscalationLevel
              level="L3"
              budget="Remaining — Full escalation"
              can="Any action needed. Human notified."
            />
          </div>

          <BudgetBar
            segments={[
              { label: "Diagnosis $120", percent: 1, color: "bg-yellow-400 text-black dark:bg-yellow-600" },
              { label: "Remediation $2,100", percent: 21, color: "bg-orange-400 text-white dark:bg-orange-600" },
              { label: "Unused $7,780", percent: 78, color: "bg-muted text-muted-foreground" },
            ]}
          />

          <div className="mt-6">
            <ResultBox text="Diagnosed in 40 min ($120). Fixed by scaling up ($2,100). Total: $2,220 of $10,000 budget. Escalation L3 never activated." />
          </div>
        </section>

        {/* ─── 3. Marketing Campaign ─── */}
        <section id="marketing-campaign" className="mt-16 border-t pt-16">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold">Marketing campaign</h2>
            <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
              Competitive allocation
            </span>
          </div>
          <p className="mt-3 text-muted-foreground">
            3 agents test different ad channels. Small seed budget each.
            The best performer wins the full campaign budget.
          </p>

          {/* Competition diagram */}
          <div className="mt-8 rounded-lg border p-6">
            <div className="text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Test phase: $200 seed each — 48h
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <CompetitorCard name="Google Ads" result="CPA: $12" />
              <CompetitorCard name="Facebook" result="CPA: $8" winner />
              <CompetitorCard name="Twitter/X" result="CPA: $22" />
            </div>
            <div className="mt-4 text-center">
              <PhaseArrow />
              <div className="rounded-lg border-2 border-green-400 bg-green-50 p-4 dark:border-green-600 dark:bg-green-950/30">
                <div className="text-xs font-semibold uppercase tracking-wider text-green-700 dark:text-green-400">
                  Winner: Facebook
                </div>
                <div className="mt-1 text-lg font-bold text-green-900 dark:text-green-200">
                  $5,000 prize budget
                </div>
                <div className="mt-1 text-sm text-green-800 dark:text-green-300">
                  Other agents paused automatically
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6">
            <ResultBox text="Facebook won at $8 CPA. Scaled to $5,000 → 625 conversions. Google and Twitter stopped automatically. Total spent: $5,600." />
          </div>
        </section>

        {/* ─── 4. Procurement ─── */}
        <section id="procurement" className="mt-16 border-t pt-16">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold">Procurement</h2>
            <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
              Pipeline with gates
            </span>
          </div>
          <p className="mt-3 text-muted-foreground">
            Buy 50 laptops. Agents search suppliers, compliance checks the winner,
            only then purchase is authorized.
          </p>

          {/* Pipeline diagram */}
          <div className="mt-8 rounded-lg border p-6">
            <div className="space-y-1">
              <PhaseBox
                name="Search"
                budget="$0 (research only)"
                agents={["Supplier A", "Supplier B"]}
              />
              <div className="flex justify-center py-2">
                <ConstraintLine text="Gate: best price wins" />
              </div>
              <PhaseArrow />
              <PhaseBox
                name="Compliance"
                budget="$0"
                agents={["Compliance"]}
                highlight
              />
              <div className="flex justify-center py-2">
                <ConstraintLine text="Gate: must pass verification" />
              </div>
              <PhaseArrow />
              <PhaseBox
                name="Purchase"
                budget="$75,000"
                agents={["Winning supplier agent"]}
              />
            </div>
            <p className="mt-4 text-center text-xs text-muted-foreground">
              If compliance fails → rollback to search, exclude failed vendor
            </p>
          </div>

          <div className="mt-6">
            <ResultBox text="Supplier B: 50 Lenovo ThinkPads at $1,350 ($67,500). Compliance passed. Purchased. $7,500 under budget." />
          </div>
        </section>

        {/* ─── 5. Customer Service ─── */}
        <section id="customer-service" className="mt-16 border-t pt-16">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold">Customer service</h2>
            <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
              Escalation
            </span>
          </div>
          <p className="mt-3 text-muted-foreground">
            One support agent, three authority levels. Starts with discount codes,
            escalates to full refunds if needed.
          </p>

          {/* Escalation diagram */}
          <div className="mt-8 space-y-3">
            <EscalationLevel
              level="L1"
              budget="$50"
              can="Discount codes, free shipping"
              active
            />
            <EscalationLevel
              level="L2"
              budget="$200"
              can="Partial refunds, replacements"
            />
            <EscalationLevel
              level="L3"
              budget="$500"
              can="Full refunds, compensation"
            />
          </div>

          <div className="mt-6 rounded-lg border p-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-medium">L1</span>
              <span>Offered 15% discount ($30)</span>
              <span className="text-xs text-red-500">Customer refused</span>
            </div>
            <PhaseArrow />
            <div className="flex items-center gap-2">
              <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-medium">L2</span>
              <span>Offered replacement + express shipping ($85)</span>
              <span className="text-xs text-green-600 dark:text-green-400">Accepted</span>
            </div>
          </div>

          <div className="mt-6">
            <ResultBox text="Resolved at L2 for $85 of $500 max budget. L3 never reached. Customer satisfied." />
          </div>
        </section>

        {/* CTA */}
        <section className="mt-16 rounded-lg border bg-muted/50 p-8 text-center">
          <h2 className="text-xl font-bold">Ready to dive deeper?</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Read the full specification with all objects, fields, and evaluation rules.
          </p>
          <div className="mt-6 flex items-center justify-center gap-4">
            <Link
              href="/asps/v2"
              className="rounded-md bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              v2 Specification
            </Link>
            <Link
              href="/asps/spec"
              className="rounded-md border px-6 py-2.5 text-sm font-medium hover:bg-muted"
            >
              v1 Specification
            </Link>
          </div>
        </section>
      </div>

      <PublicFooter />
    </div>
  );
}
