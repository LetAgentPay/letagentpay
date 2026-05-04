import Link from "next/link";
import type { Metadata } from "next";
import { PublicNav } from "@/components/public-nav";
import { PublicFooter } from "@/components/public-footer";

export const metadata: Metadata = {
  title: "Spending policies for x402 agent wallets — LetAgentPay",
  description:
    "Your agent has a wallet on x402. Decide when it opens. Per-domain limits, chain allowlists, depeg protection — all under one budget shared with fiat.",
};

export default function X402Page() {
  return (
    <div className="min-h-screen bg-background">
      <PublicNav />

      {/* Hero */}
      <section className="mx-auto max-w-4xl px-4 py-20 text-center">
        <p className="text-sm font-medium uppercase tracking-wider text-primary">
          x402 · USDC on Base · Live today
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">
          Your agent has a wallet on x402.
          <br />
          <span className="text-muted-foreground">Who decides when it opens?</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          x402 gives agents the ability to pay servers directly with USDC.
          LetAgentPay is the policy layer in front of that wallet — chain
          allowlists, per-domain caps, category budgets, depeg protection.
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link
            href="/auth/signin"
            className="rounded-md bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Create Free Account
          </Link>
          <Link
            href="/developers"
            className="rounded-md border px-6 py-3 text-sm font-medium hover:bg-muted"
          >
            See x402 API
          </Link>
        </div>
        <p className="mt-6 text-xs text-muted-foreground">
          Coinbase CDP wallets · Basescan tx links · Same engine for fiat and crypto
        </p>
      </section>

      {/* Flow */}
      <section className="border-t bg-muted/50">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            How a governed x402 payment flows
          </h2>
          <div className="mt-12 grid gap-6 sm:grid-cols-4">
            {[
              {
                step: "1",
                title: "Server returns 402",
                desc: "Resource server replies with 402 Payment Required and a price quote in USDC.",
              },
              {
                step: "2",
                title: "Authorize via LAP",
                desc: "Agent calls /x402/authorize with chain, domain, amount. Engine checks budget, allowlists, depeg.",
              },
              {
                step: "3",
                title: "Settle on-chain",
                desc: "On approval, the agent settles USDC on Base. Server verifies tx and returns the resource.",
              },
              {
                step: "4",
                title: "Report and reconcile",
                desc: "Agent reports tx_hash. LAP corrects budget if actual differs from authorized. Full audit.",
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

      {/* Code */}
      <section className="border-t">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            Two API calls, one policy
          </h2>
          <div className="mt-12 grid gap-6 lg:grid-cols-2">
            <div className="rounded-lg border bg-background p-6">
              <h3 className="font-semibold">Authorize before paying</h3>
              <pre className="mt-3 overflow-x-auto rounded bg-muted p-4 text-xs">
                <code>{`from letagentpay import LetAgentPay

client = LetAgentPay(token="agt_...")

auth = client.x402.authorize(
    chain="base",
    domain="api.example.com",
    amount_usdc="0.50",
    category="api",
    description="Premium endpoint, 1 call",
)

if auth.status == "approved":
    # settle on-chain
    tx_hash = wallet.send_usdc(
        to=auth.recipient,
        amount=auth.authorized_amount,
    )
    client.x402.report(
        request_id=auth.request_id,
        tx_hash=tx_hash,
    )`}</code>
              </pre>
            </div>
            <div className="rounded-lg border bg-background p-6">
              <h3 className="font-semibold">Policy in plain English</h3>
              <pre className="mt-3 overflow-x-auto rounded bg-muted p-4 text-xs">
                <code>{`Allow x402 settlements on Base only.
Block .onion domains and any domain
not in (api.openai.com, api.replicate.com,
api.example.com).

Max $0.10 per request, $5/day total
for the "api" category.

Reject any stablecoin trading more than
1% off peg at the time of authorization.`}</code>
              </pre>
              <p className="mt-3 text-xs text-muted-foreground">
                Claude converts this to enforceable JSON policy with
                preview and confirmation before save.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Why this and not just a wallet limit */}
      <section className="border-t bg-muted/50">
        <div className="mx-auto max-w-4xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            What you get on top of raw x402
          </h2>
          <div className="mt-12 grid gap-8 sm:grid-cols-2">
            {[
              {
                title: "Chain and domain allowlists",
                desc: "Restrict settlements to chains you trust and merchants you've approved. Wildcard or exact match.",
              },
              {
                title: "Per-category budgets",
                desc: "Same budget engine as fiat. APIs, data, infra — different limits per category, all under one cap.",
              },
              {
                title: "Depeg detection",
                desc: "Live exchange rate (Coinbase + CoinGecko). Stablecoin off peg by >1% blocks the authorization.",
              },
              {
                title: "Settlement reconciliation",
                desc: "If actual_amount differs from authorized, the engine corrects budget and prevents tx_hash reuse.",
              },
              {
                title: "CDP wallet provisioning",
                desc: "Optional — let LAP provision Coinbase CDP wallets per agent, so the wallet itself is governed.",
              },
              {
                title: "Unified with fiat",
                desc: "Switch a flow from x402 to Stripe (or vice versa) without touching governance. One source of truth.",
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

      {/* CTA */}
      <section className="border-t">
        <div className="mx-auto max-w-4xl px-4 py-20 text-center">
          <h2 className="text-2xl font-bold sm:text-3xl">
            Ready to govern your x402 agent?
          </h2>
          <p className="mt-3 text-muted-foreground">
            Free during early access. Magic-link signup, no credit card. Test
            on Base Sepolia before mainnet.
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
              x402 API Reference
            </Link>
          </div>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}
