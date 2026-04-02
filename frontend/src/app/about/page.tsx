import Link from "next/link";
import type { Metadata } from "next";
import { PublicNav } from "@/components/public-nav";
import { SupportLink } from "@/components/support-link";

export const metadata: Metadata = {
  title: "About",
  description:
    "LetAgentPay is a policy middleware for AI agents — set budgets, define spending rules, and approve purchases before they happen.",
};

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-background">
      <PublicNav />

      <article className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-3xl font-bold">About LetAgentPay</h1>

        {/* What it is */}
        <section className="mt-10">
          <h2 className="text-xl font-bold">What is LetAgentPay?</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            LetAgentPay is a <strong className="text-foreground">policy middleware for AI agents</strong>.
            It sits between your AI agent and any financial transaction, acting as
            a checkpoint that enforces the spending rules you define. Every time
            an agent wants to spend money — whether calling a paid API,
            provisioning cloud resources, or purchasing a product — it must first
            request approval from LetAgentPay. Only if the request passes your
            policy checks does the agent proceed to pay.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            We are <strong className="text-foreground">not a payment processor</strong>.
            We don&apos;t store credit card numbers, handle transactions, or move
            money. We are the control layer that decides whether a payment
            <em> should</em> happen — based on rules you set.
          </p>
        </section>

        {/* Problem */}
        <section className="mt-10">
          <h2 className="text-xl font-bold">The problem</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            AI agents are becoming autonomous. They browse the web, call APIs,
            manage infrastructure, and make purchasing decisions. But the tools
            that give agents these capabilities don&apos;t come with spending
            controls built in.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            Today, if you want to limit what your agent spends, you have two
            options: write it into the prompt (&quot;don&apos;t spend more than
            $50&quot;) or hardcode limits in your application. Prompt instructions
            are unreliable — agents can misinterpret or ignore them. Custom code
            works but is fragile, hard to maintain, and doesn&apos;t generalize
            across agents or teams.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            The result: unexpected charges, budget overruns, and no clear audit
            trail of what was spent, when, and why.
          </p>
        </section>

        {/* How it works */}
        <section className="mt-10">
          <h2 className="text-xl font-bold">How it works</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            You create an agent in LetAgentPay and define its spending policy.
            Policies can be written in plain English — for example,
            &quot;maximum $200/month on cloud services, no spending on
            weekends, individual purchases under $50 are auto-approved&quot; —
            and our AI converts them into structured, enforceable rules. Or you
            can write them directly as JSON.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            Each agent gets a unique Bearer token. When your AI agent wants to
            make a purchase, it calls our API (or uses the SDK or MCP server)
            with the amount, category, merchant, and a short description. The
            request goes through <strong className="text-foreground">8 policy checks</strong>:
          </p>
          <ol className="mt-4 list-inside list-decimal space-y-2 text-base text-muted-foreground">
            <li><strong className="text-foreground">Agent status</strong> — is the agent active?</li>
            <li><strong className="text-foreground">Category</strong> — is this spending category allowed?</li>
            <li><strong className="text-foreground">Per-request limit</strong> — does this single purchase exceed the cap?</li>
            <li><strong className="text-foreground">Schedule</strong> — is spending allowed right now (day, time)?</li>
            <li><strong className="text-foreground">Daily limit</strong> — would this push today&apos;s spending over the daily cap?</li>
            <li><strong className="text-foreground">Weekly limit</strong> — same check for the current week</li>
            <li><strong className="text-foreground">Monthly limit</strong> — same check for the current month</li>
            <li><strong className="text-foreground">Total budget</strong> — would this exceed the agent&apos;s overall budget?</li>
          </ol>
          <p className="mt-4 leading-relaxed text-muted-foreground">
            If all checks pass and the request meets your auto-approve criteria,
            it&apos;s approved instantly — the agent can proceed with the purchase.
            If it passes but doesn&apos;t qualify for auto-approval, it enters a
            &quot;pending&quot; state and you receive a notification to review it
            manually. If any check fails, the request is rejected immediately with
            a detailed explanation of which rule was violated.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            After a purchase is completed, the agent sends a confirmation back
            with the actual amount spent. Spending counters update in real time,
            so subsequent requests are checked against accurate, up-to-date
            numbers.
          </p>
        </section>

        {/* Payment lifecycle */}
        <section className="mt-10">
          <h2 className="text-xl font-bold">Where it fits in the payment lifecycle</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            A typical AI agent payment flow looks like this:
          </p>
          <div className="mt-4 overflow-x-auto rounded-lg border p-6 text-sm">
            <div className="flex flex-col items-start gap-3">
              <div className="flex items-center gap-3">
                <span className="rounded bg-muted px-3 py-1.5 font-medium">1. Agent decides to spend</span>
                <span className="text-muted-foreground">&mdash; &quot;I need to call this paid API&quot;</span>
              </div>
              <div className="ml-4 text-muted-foreground">&darr;</div>
              <div className="flex items-center gap-3">
                <span className="rounded border-2 border-primary bg-primary/5 px-3 py-1.5 font-medium">2. LetAgentPay policy check</span>
                <span className="text-muted-foreground">&mdash; approve, reject, or escalate</span>
              </div>
              <div className="ml-4 text-muted-foreground">&darr;</div>
              <div className="flex items-center gap-3">
                <span className="rounded bg-muted px-3 py-1.5 font-medium">3. Payment happens</span>
                <span className="text-muted-foreground">&mdash; only if approved</span>
              </div>
              <div className="ml-4 text-muted-foreground">&darr;</div>
              <div className="flex items-center gap-3">
                <span className="rounded border-2 border-primary bg-primary/5 px-3 py-1.5 font-medium">4. Agent confirms result</span>
                <span className="text-muted-foreground">&mdash; counters update, audit trail recorded</span>
              </div>
            </div>
          </div>
          <p className="mt-4 leading-relaxed text-muted-foreground">
            LetAgentPay operates at steps 2 and 4 — the <strong className="text-foreground">
            pre-payment authorization</strong> and <strong className="text-foreground">
            post-payment confirmation</strong>. We don&apos;t touch the actual
            payment infrastructure. Your agent uses whatever payment method it
            already has (API keys, corporate cards, cloud billing). We add the
            policy layer on top.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            This design means there&apos;s no vendor lock-in and no need to change
            how your agent pays for things. You just add one checkpoint before and
            one confirmation after.
          </p>
        </section>

        {/* What you can control */}
        <section className="mt-10">
          <h2 className="text-xl font-bold">What you can control</h2>
          <ul className="mt-4 space-y-3 text-base text-muted-foreground">
            <li>
              <strong className="text-foreground">Budgets</strong> — total budget per agent,
              plus daily, weekly, and monthly spending limits. When a limit is reached,
              new requests are automatically rejected.
            </li>
            <li>
              <strong className="text-foreground">Categories</strong> — define which spending
              categories an agent can use (e.g., &quot;cloud&quot;, &quot;groceries&quot;,
              &quot;saas&quot;). Requests outside allowed categories are rejected.
            </li>
            <li>
              <strong className="text-foreground">Per-request caps</strong> — maximum amount
              for a single purchase. Prevents large unexpected charges.
            </li>
            <li>
              <strong className="text-foreground">Time schedules</strong> — restrict spending
              to specific days and hours. Block weekends, nights, or define custom windows.
            </li>
            <li>
              <strong className="text-foreground">Auto-approval rules</strong> — define
              conditions under which purchases are approved without your manual review
              (e.g., &quot;auto-approve if under $20 in allowed categories&quot;).
            </li>
            <li>
              <strong className="text-foreground">Natural language policies</strong> — write
              rules in plain English. Our AI converts them to structured JSON policies
              that the engine can enforce deterministically.
            </li>
          </ul>
        </section>

        {/* Who it's for */}
        <section className="mt-10">
          <h2 className="text-xl font-bold">Who is it for?</h2>
          <div className="mt-4 space-y-6">
            <div>
              <h3 className="font-semibold">AI agent developers</h3>
              <p className="mt-1 text-base text-muted-foreground">
                If you&apos;re building an agent that spends money on behalf of
                users, LetAgentPay gives you a ready-made spending control layer.
                Instead of building custom budget logic, integrate our SDK and
                let users define their own policies through our dashboard. It
                makes your agent safer and more trustworthy.
              </p>
            </div>
            <div>
              <h3 className="font-semibold">Teams deploying AI automation</h3>
              <p className="mt-1 text-base text-muted-foreground">
                If your team uses AI agents for procurement, infrastructure
                provisioning, or SaaS management, LetAgentPay adds the financial
                controls you need. Set team-wide budgets, review unusual
                purchases, and maintain a complete audit trail — without slowing
                down routine operations.
              </p>
            </div>
            <div>
              <h3 className="font-semibold">Individuals with AI assistants</h3>
              <p className="mt-1 text-base text-muted-foreground">
                If you give your personal AI assistant access to paid services —
                booking, shopping, subscriptions — LetAgentPay ensures it stays
                within the boundaries you set. You see and approve every
                purchase before the money leaves your account.
              </p>
            </div>
          </div>
        </section>

        {/* Integration */}
        <section className="mt-10">
          <h2 className="text-xl font-bold">How to integrate</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            LetAgentPay offers three integration methods:
          </p>
          <ul className="mt-4 space-y-3 text-base text-muted-foreground">
            <li>
              <strong className="text-foreground">Python SDK</strong> — install{" "}
              <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">letagentpay</code>{" "}
              and add a few lines of code. Supports both direct calls and a decorator pattern.
            </li>
            <li>
              <strong className="text-foreground">MCP Server</strong> — works with Claude Desktop,
              Cursor, and any MCP-compatible tool. One configuration block and your agent gets
              spending tools automatically. Best for non-technical users.
            </li>
            <li>
              <strong className="text-foreground">REST API</strong> — simple HTTP endpoints with
              Bearer token authentication. Works with any language or framework.
            </li>
          </ul>
          <p className="mt-4 text-base text-muted-foreground">
            See the{" "}
            <Link href="/developers" className="text-primary underline hover:no-underline">
              developer documentation
            </Link>{" "}
            for code examples, API reference, and the full request lifecycle.
          </p>
        </section>

        {/* Design principles */}
        <section className="mt-10">
          <h2 className="text-xl font-bold">Design principles</h2>
          <ul className="mt-4 space-y-3 text-base text-muted-foreground">
            <li>
              <strong className="text-foreground">Pre-payment, not post-payment.</strong>{" "}
              Approval happens before the money moves. You don&apos;t find out after the fact.
            </li>
            <li>
              <strong className="text-foreground">Deterministic enforcement.</strong>{" "}
              Policies are converted to structured rules and checked programmatically.
              No prompt-based &quot;hoping the agent listens.&quot;
            </li>
            <li>
              <strong className="text-foreground">Human in the loop.</strong>{" "}
              Routine purchases flow through automatically. Unusual ones surface
              to you for review. You choose the threshold.
            </li>
            <li>
              <strong className="text-foreground">Full transparency.</strong>{" "}
              Every request, every check result, every decision is logged.
              Complete audit trail from day one.
            </li>
            <li>
              <strong className="text-foreground">No lock-in.</strong>{" "}
              We don&apos;t touch your payment methods. Add one API call before
              payment and one after — that&apos;s the entire integration surface.
            </li>
          </ul>
        </section>

        {/* Contact */}
        <section className="mt-10">
          <h2 className="text-xl font-bold">Contact us</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            Found a bug? Have a feature request? Something doesn&apos;t work as
            expected? We want to hear from you — your feedback helps us build a
            better product.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            Drop us a line at{" "}
            <SupportLink className="text-primary underline hover:no-underline">
              support@letagentpay.com
            </SupportLink>
            . We read every message and typically respond within a day.
          </p>
        </section>

        {/* CTA */}
        <section className="mt-12 rounded-lg border bg-muted/50 p-8 text-center">
          <h2 className="text-xl font-bold">Get started</h2>
          <p className="mt-2 text-base text-muted-foreground">
            LetAgentPay is free during early access. Create an account, set up
            your first agent, and start controlling spending in under 5 minutes.
          </p>
          <div className="mt-6 flex items-center justify-center gap-4">
            <Link
              href="/auth/signin"
              className="rounded-md bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Create Free Account
            </Link>
            <Link
              href="/developers"
              className="rounded-md border px-6 py-2.5 text-sm font-medium hover:bg-muted"
            >
              Read the Docs
            </Link>
          </div>
        </section>
      </article>

      <footer className="border-t py-8">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 text-sm text-muted-foreground">
          <span>
            LetAgentPay &copy; {new Date().getFullYear()}
            <span className="ml-2 text-xs opacity-40">v{process.env.NEXT_PUBLIC_APP_VERSION}</span>
          </span>
          <div className="flex gap-4">
            <Link href="/about" className="hover:text-foreground">
              About
            </Link>
            <Link href="/developers" className="hover:text-foreground">
              Developers
            </Link>
            <SupportLink className="hover:text-foreground" />
          </div>
        </div>
      </footer>
    </div>
  );
}
