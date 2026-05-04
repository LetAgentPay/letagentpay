import Link from "next/link";
import type { Metadata } from "next";
import { PublicNav } from "@/components/public-nav";
import { PublicFooter } from "@/components/public-footer";

export const metadata: Metadata = {
  title: "The policy layer for AI agent payments — LetAgentPay",
  description:
    "One open-source engine that decides whether your agent's purchase is allowed — across fiat, x402, and any payment rail. Python and TypeScript SDKs, MCP server, REST.",
};

export default function MiddlewarePage() {
  return (
    <div className="min-h-screen bg-background">
      <PublicNav />

      {/* Hero */}
      <section className="mx-auto max-w-4xl px-4 py-20 text-center">
        <p className="text-sm font-medium uppercase tracking-wider text-primary">
          For developers building agents
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">
          The policy layer between your agent and any payment rail
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          One open-source engine. Budgets, categories, schedules, approvals.
          Plugs in front of Stripe, x402, or your own checkout. Same engine,
          unified budget, every rail.
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link
            href="/auth/signin"
            className="rounded-md bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Get a Token (Free)
          </Link>
          <Link
            href="/developers"
            className="rounded-md border px-6 py-3 text-sm font-medium hover:bg-muted"
          >
            Read API Docs
          </Link>
          <a
            href="https://github.com/LetAgentPay/letagentpay"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-md border px-6 py-3 text-sm font-medium hover:bg-muted"
          >
            Star on GitHub
          </a>
        </div>
        <p className="mt-6 text-xs text-muted-foreground">
          Apache-2.0 · Self-hosted or SaaS · 9 framework guides · MCP-compatible
        </p>
      </section>

      {/* Code first */}
      <section className="border-t bg-muted/50">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            One call before the payment
          </h2>
          <p className="mt-3 text-center text-muted-foreground">
            Wrap any payment rail. The engine returns approve / deny / pending
            with an audit trail. No SDK lock-in — the REST API is two endpoints.
          </p>
          <div className="mt-12 grid gap-6 lg:grid-cols-2">
            <div className="rounded-lg border bg-background p-6">
              <h3 className="font-semibold">Python — Stripe in front</h3>
              <pre className="mt-3 overflow-x-auto rounded bg-muted p-4 text-xs">
                <code>{`from letagentpay import LetAgentPay
import stripe

lap = LetAgentPay(token="agt_...")

result = lap.request_purchase(
    amount=49.99,
    category="cloud",
    description="GPU credits, runpod.io",
)

if result.status == "auto_approved":
    stripe.PaymentIntent.create(
        amount=4999, currency="usd",
        # ...your Stripe call
    )
elif result.status == "pending":
    # human approval flow
    show_pending_to_user(result.id)
else:
    suggest_cheaper_alternative(agent)`}</code>
              </pre>
            </div>
            <div className="rounded-lg border bg-background p-6">
              <h3 className="font-semibold">TypeScript — Vercel AI SDK tools</h3>
              <pre className="mt-3 overflow-x-auto rounded bg-muted p-4 text-xs">
                <code>{`import { generateText } from "ai";
import { createLetAgentPayTools } from "@letagentpay/ai";

const tools = createLetAgentPayTools(process.env.LAP_TOKEN!);

await generateText({
  model: anthropic("claude-sonnet-4-6"),
  tools, // requestPurchase, checkBudget,
         // listCategories, myRequests,
         // confirmPurchase
  prompt: "Top up our GPU credits if budget allows.",
});`}</code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Why a separate layer */}
      <section className="border-t">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            Why this isn&apos;t just <code className="rounded bg-muted px-1.5 py-0.5 text-xl">if amount &gt; limit</code>
          </h2>
          <div className="mt-12 grid gap-8 sm:grid-cols-2">
            {[
              {
                title: "Stateful budgets",
                desc: "Atomic Redis counters with PostgreSQL reconciliation. Per-request, daily, weekly, monthly, total — all checked together, no race conditions.",
              },
              {
                title: "Category resolution",
                desc: "Custom per-account categories with AI alias matching. Free-form descriptions resolve to your taxonomy, orphans flagged for review.",
              },
              {
                title: "Schedule + auto-approve",
                desc: "Cron-like windows per category. Threshold-based auto-approve for routine spend, escalation to human for unusual.",
              },
              {
                title: "Multi-rail under one engine",
                desc: "x402 USDC settlement and fiat purchases share the same budget and policy. Switch rails without rewriting governance.",
              },
              {
                title: "Pending request flow built in",
                desc: "Email/push/Telegram approval channels. Action tokens with TTL, atomic approval, full audit log — not a hack.",
              },
              {
                title: "Open-source and self-hostable",
                desc: "Apache-2.0. Run on your own Postgres + Redis with docker-compose, or use the hosted SaaS. Same code, same APIs.",
              },
            ].map((item) => (
              <div key={item.title} className="space-y-2">
                <h3 className="font-semibold">{item.title}</h3>
                <p className="text-base text-muted-foreground">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Integrations */}
      <section className="border-t bg-muted/50">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            Works with your stack
          </h2>
          <p className="mt-3 text-center text-muted-foreground">
            Native packages and integration guides for the frameworks agent
            builders actually use.
          </p>
          <div className="mt-12 grid gap-3 sm:grid-cols-3">
            {[
              { name: "Python SDK", path: "letagentpay (PyPI)" },
              { name: "TypeScript SDK", path: "letagentpay (npm)" },
              { name: "Vercel AI SDK", path: "@letagentpay/ai" },
              { name: "MCP Server", path: "letagentpay-mcp" },
              { name: "OpenAI Agents SDK", path: "guide + example" },
              { name: "LangChain", path: "guide + example" },
              { name: "CrewAI", path: "guide + example" },
              { name: "Google ADK", path: "guide + example" },
              { name: "Stripe (governance)", path: "guide + example" },
            ].map((it) => (
              <div key={it.name} className="rounded-lg border bg-background p-4">
                <div className="font-semibold">{it.name}</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {it.path}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t">
        <div className="mx-auto max-w-4xl px-4 py-20 text-center">
          <h2 className="text-2xl font-bold sm:text-3xl">
            Get a token, ship in an afternoon
          </h2>
          <p className="mt-3 text-muted-foreground">
            Free during early access. Magic-link signup, no credit card.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              href="/auth/signin"
              className="rounded-md bg-primary px-8 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Create Free Account
            </Link>
            <Link
              href="/developers"
              className="rounded-md border px-8 py-3 text-sm font-medium hover:bg-muted"
            >
              Read the Docs
            </Link>
          </div>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}
