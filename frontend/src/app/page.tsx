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
          Give your AI agent a wallet — with rules
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          Let your agent pay for APIs, services, and tasks autonomously —
          within budgets and policies you define. Open-source, works with
          fiat and crypto rails.
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link
            href="/auth/signin"
            className="rounded-md bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Create Free Account
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
        <p className="mt-6 text-xs text-muted-foreground">
          9 framework integrations · Python &amp; TypeScript SDKs · MCP server · x402 live on Base
        </p>
      </section>

      {/* What it enables */}
      <section className="border-t bg-muted/50">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            What your agent can do once it has a wallet
          </h2>
          <div className="mt-12 grid gap-8 sm:grid-cols-3">
            <div className="space-y-2">
              <h3 className="font-semibold">Pay for APIs autonomously</h3>
              <p className="text-base text-muted-foreground">
                Your agent buys API credits, premium model access, or per-call
                services without you in the loop — but only within rules you set.
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold">Provision cloud &amp; SaaS</h3>
              <p className="text-base text-muted-foreground">
                Spin up resources, subscribe to tools, top up data plans —
                each purchase checked against budget and category limits in real time.
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold">Settle on-chain micropayments</h3>
              <p className="text-base text-muted-foreground">
                Same policy engine for fiat and crypto. USDC on Base via x402
                works today, with one unified budget across rails.
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
            One policy engine sits between your agent and any payment rail —
            checks rules, decides, logs.
          </p>
          <div className="mt-12 grid gap-6 sm:grid-cols-4">
            {[
              {
                step: "1",
                title: "Set rules",
                desc: "Budgets, category limits, schedules, per-request caps. Plain English or JSON — both work.",
              },
              {
                step: "2",
                title: "Agent requests",
                desc: "Before spending, the agent asks for approval with the amount, category, and description.",
              },
              {
                step: "3",
                title: "Engine decides",
                desc: "8 instant checks: budget, category, schedule, history. Auto-approve routine, escalate unusual.",
              },
              {
                step: "4",
                title: "Agent pays",
                desc: "Approved purchases proceed on the chosen rail. Every action logged with full audit trail.",
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

      {/* Features */}
      <section className="border-t bg-muted/50">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            Capabilities
          </h2>
          <div className="mt-12 grid gap-8 sm:grid-cols-2">
            {[
              {
                title: "Natural language policies",
                desc: 'Write rules like "max $100/day on cloud APIs, no weekend spending". Claude converts them to enforceable JSON.',
              },
              {
                title: "Multi-level budgets",
                desc: "Per-request, daily, weekly, monthly limits and overall budget — all checked in real time against actual spend.",
              },
              {
                title: "Category controls",
                desc: "Custom per-account categories. Different limits per category, with AI alias matching for free-form descriptions.",
              },
              {
                title: "Schedule-based rules",
                desc: "Allow spending only during business hours, block weekends, or define custom time windows per category.",
              },
              {
                title: "Auto-approve and escalation",
                desc: "Routine purchases within policy auto-approve. High-value or unusual ones wait for manual review.",
              },
              {
                title: "Real-time dashboard",
                desc: "See every request as it happens. Approve, reject, or review with full context and policy results.",
              },
              {
                title: "Multi-rail under one engine",
                desc: "Fiat (Stripe-style integrations) and x402 USDC settlements share the same policy and unified budget.",
              },
              {
                title: "Self-hosted and open-source",
                desc: "Run on your own infra, full source access. Or use the hosted SaaS — same engine, same APIs.",
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
      <section className="border-t">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            Integrate in minutes
          </h2>
          <p className="mt-3 text-center text-muted-foreground">
            Pick what fits your stack — SDKs, MCP, REST, or any of 9 framework guides.
          </p>
          <div className="mt-12 grid gap-8 sm:grid-cols-3">
            <div className="rounded-lg border bg-background p-6">
              <h3 className="font-semibold">Python SDK</h3>
              <pre className="mt-3 overflow-x-auto rounded bg-muted p-3 text-xs">
                <code>{`pip install letagentpay

client = LetAgentPay(token="agt_...")

result = client.request_purchase(
    amount=49.99,
    category="cloud",
)
# result.status: "auto_approved",
# "pending", or "rejected"`}</code>
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
                Bearer token auth, simple HTTP endpoints. Works with any
                language. Full OpenAPI spec available.
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
      <section className="border-t bg-muted/50">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            Built for
          </h2>
          <div className="mt-12 grid gap-8 sm:grid-cols-3">
            <div className="space-y-2">
              <h3 className="font-semibold">Agent developers</h3>
              <p className="text-base text-muted-foreground">
                Ship agents that pay for things — and ship them with
                guardrails users actually trust.
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold">Teams running AI in production</h3>
              <p className="text-base text-muted-foreground">
                Let agents handle procurement, cloud, and SaaS with budgets
                and category limits per agent.
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold">Builders on x402 / AP2</h3>
              <p className="text-base text-muted-foreground">
                Already gave your agent a wallet? Add the policy layer that
                decides when it opens.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t">
        <div className="mx-auto max-w-4xl px-4 py-20 text-center">
          <h2 className="text-2xl font-bold sm:text-3xl">
            Give your agent a wallet today
          </h2>
          <p className="mt-3 text-muted-foreground">
            Free during early access. Setup takes under 5 minutes.
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
