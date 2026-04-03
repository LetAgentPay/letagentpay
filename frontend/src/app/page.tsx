import Link from "next/link";
import { PublicNav } from "@/components/public-nav";
import { PlaygroundLink } from "@/components/playground-link";
import { PublicFooter } from "@/components/public-footer";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <PublicNav />

      {/* Hero */}
      <section className="mx-auto max-w-4xl px-4 py-20 text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          Control every dollar your AI agent spends
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          Set budgets, define spending policies in plain English, and approve or
          reject AI agent purchases in real time — before the money leaves your
          account.
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link
            href="/auth/signin"
            className="rounded-md bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Get Started — Free
          </Link>
          <PlaygroundLink
            className="rounded-md border px-6 py-3 text-sm font-medium hover:bg-muted"
          >
            Try Live Demo
          </PlaygroundLink>
          <Link
            href="/developers"
            className="rounded-md border px-6 py-3 text-sm font-medium hover:bg-muted"
          >
            View Docs
          </Link>
        </div>
      </section>

      {/* Problem */}
      <section className="border-t bg-muted/50">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            AI agents are spending money on your behalf.
            <br />
            <span className="text-muted-foreground">Do you know where it goes?</span>
          </h2>
          <div className="mt-12 grid gap-8 sm:grid-cols-3">
            <div className="space-y-2">
              <div className="text-3xl">$</div>
              <h3 className="font-semibold">Uncontrolled spending</h3>
              <p className="text-base text-muted-foreground">
                Agents call APIs, provision cloud resources, and subscribe to
                SaaS tools — often without explicit limits.
              </p>
            </div>
            <div className="space-y-2">
              <div className="text-3xl">?</div>
              <h3 className="font-semibold">No visibility</h3>
              <p className="text-base text-muted-foreground">
                You find out about costs after the fact — when the invoice
                arrives. By then it&apos;s too late.
              </p>
            </div>
            <div className="space-y-2">
              <div className="text-3xl">!</div>
              <h3 className="font-semibold">No policy enforcement</h3>
              <p className="text-base text-muted-foreground">
                Prompt instructions like &quot;don&apos;t spend more than $50&quot; are
                suggestions, not guarantees. Agents can ignore them.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="border-t">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            How it works
          </h2>
          <p className="mt-3 text-center text-muted-foreground">
            LetAgentPay sits between your AI agent and the payment — a policy
            checkpoint that enforces your rules.
          </p>
          <div className="mt-12 grid gap-6 sm:grid-cols-4">
            {[
              {
                step: "1",
                title: "Define policies",
                desc: "Set budgets, category limits, schedules, and per-request caps — in plain English or JSON.",
              },
              {
                step: "2",
                title: "Agent requests",
                desc: "Before spending, your agent calls LetAgentPay with the amount, category, and description.",
              },
              {
                step: "3",
                title: "Policy check",
                desc: "8 checks run instantly: budget, category, limits, schedule, spending history. Auto-approve or escalate.",
              },
              {
                step: "4",
                title: "You decide",
                desc: "Approved requests proceed. Flagged ones wait for your review. Rejected ones stop the agent.",
              },
            ].map((item) => (
              <div key={item.step} className="space-y-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
                  {item.step}
                </div>
                <h3 className="font-semibold">{item.title}</h3>
                <p className="text-base text-muted-foreground">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Where It Fits */}
      <section className="border-t bg-muted/50">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            Where LetAgentPay fits in the payment lifecycle
          </h2>
          <p className="mt-3 text-center text-muted-foreground">
            We&apos;re not a payment processor. We&apos;re the policy layer that
            decides whether a payment should happen.
          </p>
          <div className="mt-12 flex flex-col items-center gap-0">
            {/* Pipeline diagram */}
            <div className="flex w-full max-w-2xl flex-col gap-3 sm:flex-row sm:items-center sm:gap-0">
              {[
                { label: "AI Agent", sub: "wants to spend", active: false },
                { label: "LetAgentPay", sub: "policy check", active: true },
                { label: "Payment", sub: "approved spend", active: false },
              ].map((node, i) => (
                <div key={node.label} className="flex flex-1 items-center">
                  <div
                    className={`flex-1 rounded-lg border-2 p-4 text-center ${
                      node.active
                        ? "border-primary bg-primary/5"
                        : "border-border"
                    }`}
                  >
                    <div className="font-semibold">{node.label}</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {node.sub}
                    </div>
                  </div>
                  {i < 2 && (
                    <div className="hidden px-2 text-muted-foreground sm:block">
                      &rarr;
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="mt-8 grid gap-6 text-base sm:grid-cols-3">
              <div>
                <h4 className="font-semibold">Before payment</h4>
                <p className="mt-1 text-muted-foreground">
                  The agent asks LetAgentPay for approval before initiating any
                  transaction. No approval — no payment.
                </p>
              </div>
              <div>
                <h4 className="font-semibold">Real-time decisions</h4>
                <p className="mt-1 text-muted-foreground">
                  Policies are checked instantly. Auto-approve for routine
                  purchases, escalate unusual ones to you.
                </p>
              </div>
              <div>
                <h4 className="font-semibold">After payment</h4>
                <p className="mt-1 text-muted-foreground">
                  The agent confirms the result. Spending counters update. Full
                  audit trail preserved.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-t">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            Capabilities
          </h2>
          <div className="mt-12 grid gap-8 sm:grid-cols-2">
            {[
              {
                title: "Natural language policies",
                desc: "Write rules like \"max $100/day on cloud services, no weekend spending\". AI converts them to enforceable JSON policies.",
              },
              {
                title: "Multi-level budgets",
                desc: "Set per-request, daily, weekly, monthly limits and an overall budget. All checked in real time against actual spending.",
              },
              {
                title: "Category controls",
                desc: "Restrict agents to specific spending categories — groceries, cloud, SaaS, travel — and set different limits per category.",
              },
              {
                title: "Schedule-based rules",
                desc: "Allow spending only during business hours, block weekends, or define custom time windows.",
              },
              {
                title: "Auto-approve & escalation",
                desc: "Routine purchases within policy get approved instantly. Unusual or high-value requests require your manual review.",
              },
              {
                title: "Real-time dashboard",
                desc: "See every request as it happens. Approve, reject, or review with full context — amount, category, merchant, policy check results.",
              },
              {
                title: "Spending analytics",
                desc: "Track daily, weekly, and monthly spending by agent. See budget utilization and remaining balances at a glance.",
              },
              {
                title: "Full audit trail",
                desc: "Every request, every policy check, every decision — logged and searchable. Know exactly what was spent, when, and why.",
              },
            ].map((feature) => (
              <div key={feature.title} className="space-y-2">
                <h3 className="font-semibold">{feature.title}</h3>
                <p className="text-base text-muted-foreground">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Integration */}
      <section className="border-t bg-muted/50">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            Integrate in minutes
          </h2>
          <p className="mt-3 text-center text-muted-foreground">
            Three ways to connect your agent — pick what fits your stack.
          </p>
          <div className="mt-12 grid gap-8 sm:grid-cols-3">
            <div className="rounded-lg border bg-background p-6">
              <h3 className="font-semibold">Python SDK</h3>
              <pre className="mt-3 overflow-x-auto rounded bg-muted p-3 text-xs">
                <code>{`pip install letagentpay

client = LetAgentPay(
    token="agt_..."
)
client.purchase(
    amount=49.99,
    category="cloud"
)`}</code>
              </pre>
            </div>
            <div className="rounded-lg border bg-background p-6">
              <h3 className="font-semibold">MCP Server</h3>
              <p className="mt-3 text-base text-muted-foreground">
                Works with Claude Desktop, Cursor, and any MCP-compatible AI
                tool. One config line — your agent gets spending tools
                automatically.
              </p>
            </div>
            <div className="rounded-lg border bg-background p-6">
              <h3 className="font-semibold">REST API</h3>
              <p className="mt-3 text-base text-muted-foreground">
                Simple HTTP endpoints with Bearer token auth. Works with any
                language or framework. Full OpenAPI spec available.
              </p>
            </div>
          </div>
          <div className="mt-8 text-center">
            <Link
              href="/developers"
              className="text-sm font-medium text-primary underline hover:no-underline"
            >
              Read the full developer documentation &rarr;
            </Link>
          </div>
        </div>
      </section>

      {/* Use Cases */}
      <section className="border-t">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            Built for
          </h2>
          <div className="mt-12 grid gap-8 sm:grid-cols-3">
            <div className="space-y-2">
              <h3 className="font-semibold">AI agent developers</h3>
              <p className="text-base text-muted-foreground">
                Give your users confidence that their agent won&apos;t overspend.
                Add spending controls as a feature, not a liability.
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold">Teams using AI tools</h3>
              <p className="text-base text-muted-foreground">
                Let agents handle procurement, cloud provisioning, and SaaS
                subscriptions — with guardrails you define.
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold">Individuals with AI assistants</h3>
              <p className="text-base text-muted-foreground">
                Trust your personal AI to book, shop, and subscribe — knowing
                every purchase gets checked against your rules first.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t bg-muted/50">
        <div className="mx-auto max-w-4xl px-4 py-20 text-center">
          <h2 className="text-2xl font-bold sm:text-3xl">
            Start controlling AI spending today
          </h2>
          <p className="mt-3 text-muted-foreground">
            Free while in early access. Set up in under 5 minutes.
          </p>
          <div className="mt-8">
            <Link
              href="/auth/signin"
              className="rounded-md bg-primary px-8 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Create Free Account
            </Link>
          </div>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}