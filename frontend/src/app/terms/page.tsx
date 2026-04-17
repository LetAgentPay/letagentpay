import Link from "next/link";
import type { Metadata } from "next";
import { PublicNav } from "@/components/public-nav";
import { PublicFooter } from "@/components/public-footer";

export const metadata: Metadata = {
  title: "Terms of Service",
  description:
    "LetAgentPay Terms of Service — rules and conditions for using the platform.",
};

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-background">
      <PublicNav />

      <article className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-3xl font-bold">Terms of Service</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Last updated: April 17, 2026
        </p>

        <div className="mt-6 rounded-lg border bg-muted/50 p-4 text-sm leading-relaxed text-muted-foreground">
          <strong className="text-foreground">Short version:</strong> we provide
          spending controls for AI agents — not payment processing. You&apos;re
          responsible for what your agents do with their approvals. We don&apos;t
          move money, store card numbers, or sign transactions.
        </div>

        <section className="mt-10">
          <h2 className="text-xl font-bold">1. Agreement to terms</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            By accessing or using LetAgentPay (&quot;the Service&quot;), operated
            at{" "}
            <Link href="/" className="text-primary underline hover:no-underline">
              letagentpay.com
            </Link>
            , you agree to be bound by these Terms of Service (&quot;Terms&quot;).
            If you do not agree, do not use the Service.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            &quot;We&quot;, &quot;us&quot;, and &quot;our&quot; refer to
            LetAgentPay. &quot;You&quot; and &quot;your&quot; refer to the person
            or entity using the Service.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">2. Description of the Service</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            LetAgentPay is a policy middleware for AI agents. It provides
            spending controls — budgets, category restrictions, schedules, and
            approval workflows — that are checked before an AI agent proceeds
            with a financial transaction.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            <strong className="text-foreground">
              LetAgentPay is not a payment processor.
            </strong>{" "}
            We do not handle, store, or transmit payment credentials (credit card
            numbers, bank accounts, crypto private keys). We do not move money.
            We provide a pre-payment authorization layer — the decision of
            whether a payment <em>should</em> happen, not the payment itself.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">3. Accounts</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            To use the Service, you must create an account with a valid email
            address. You are responsible for maintaining the security of your
            account and any agent tokens you create. You must notify us
            immediately if you suspect unauthorized access.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            You must be at least 16 years old to create an account. By creating
            an account, you represent that you meet this requirement.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">4. Acceptable use</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            You agree to use the Service only for lawful purposes. You may not:
          </p>
          <ul className="mt-4 list-inside list-disc space-y-2 text-muted-foreground">
            <li>
              Use the Service to facilitate fraud, money laundering, or other
              illegal financial activity.
            </li>
            <li>
              Attempt to circumvent spending policies or approval mechanisms
              through the API or otherwise.
            </li>
            <li>
              Use the Service to process transactions involving prohibited
              goods or services under applicable law.
            </li>
            <li>
              Reverse-engineer, decompile, or attempt to extract source code
              from proprietary components of the Service beyond what is available
              in the open-source repository.
            </li>
            <li>
              Interfere with the operation of the Service, including
              overwhelming the API with excessive requests.
            </li>
            <li>
              Create multiple accounts to circumvent limitations or bans.
            </li>
          </ul>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            We reserve the right to suspend or terminate accounts that violate
            these terms.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">5. Agent tokens and security</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            Each AI agent you create receives a unique Bearer token (prefixed
            with <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">agt_</code>).
            These tokens grant API access to submit and manage purchase requests
            on your behalf. You are solely responsible for:
          </p>
          <ul className="mt-4 list-inside list-disc space-y-2 text-muted-foreground">
            <li>Keeping agent tokens confidential.</li>
            <li>
              All activity that occurs under your agent tokens, whether
              authorized by you or not.
            </li>
            <li>Revoking tokens that may have been compromised.</li>
          </ul>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">6. Blockchain transactions (x402)</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            LetAgentPay supports the x402 protocol for on-chain
            crypto-micropayments. When using x402:
          </p>
          <ul className="mt-4 list-inside list-disc space-y-2 text-muted-foreground">
            <li>
              We provide <strong className="text-foreground">policy authorization only</strong>.
              We do not custody funds, hold private keys, or sign blockchain
              transactions.
            </li>
            <li>
              <strong className="text-foreground">Blockchain transactions are irreversible.</strong>{" "}
              Once your agent executes an on-chain payment, it cannot be undone.
              An approval from LetAgentPay is a policy check, not a guarantee
              that the transaction is safe or advisable.
            </li>
            <li>
              We perform stablecoin depeg checks as a <strong className="text-foreground">
              best-effort safety measure</strong>, not a financial guarantee. You
              are responsible for monitoring the assets your agents transact with.
            </li>
            <li>
              You are solely responsible for the security of your agent&apos;s
              wallet and private keys.
            </li>
          </ul>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">7. Spending policies and approvals</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            You configure spending policies for your agents. The Service enforces
            these policies as a best effort based on the rules you define.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            <strong className="text-foreground">Important:</strong> LetAgentPay
            approving a purchase request means the request passed your policy
            checks — it does not constitute financial advice, an endorsement of
            the transaction, or a guarantee that the underlying payment will
            succeed. You remain fully responsible for all financial transactions
            your agents execute.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            Natural language policies are converted to structured rules using AI.
            While we strive for accuracy, you should review the generated rules
            to confirm they match your intent.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">8. Service availability</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            We aim to keep the Service available and reliable, but we do not
            guarantee uninterrupted or error-free operation. The Service is
            provided on an &quot;as is&quot; and &quot;as available&quot; basis.
            We may perform maintenance, updates, or experience outages that
            temporarily affect availability.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            If the Service is unavailable, your agents will not be able to
            obtain purchase approvals. You are responsible for implementing
            appropriate fallback behavior in your agents for this scenario.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">9. Pricing and payment</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            LetAgentPay is currently free during early access. We reserve the
            right to introduce paid plans in the future. If we do, we will
            provide reasonable notice and you will not be charged without
            explicit consent.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">10. Intellectual property</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            The Service, its design, features, and content (excluding your data)
            are owned by LetAgentPay and protected by applicable intellectual
            property laws. Certain components of the Service are available under
            open-source licenses — see our{" "}
            <a
              href="https://github.com/letagentpay/letagentpay"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline hover:no-underline"
            >
              GitHub repository
            </a>{" "}
            for details.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            You retain all rights to your data. By using the Service, you grant
            us a limited license to process your data solely to operate and
            improve the Service.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">11. Limitation of liability</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            To the maximum extent permitted by applicable law:
          </p>
          <ul className="mt-4 list-inside list-disc space-y-2 text-muted-foreground">
            <li>
              LetAgentPay shall not be liable for any indirect, incidental,
              special, consequential, or punitive damages, including loss of
              profits, data, or business opportunities.
            </li>
            <li>
              LetAgentPay shall not be liable for any financial losses resulting
              from transactions your AI agents execute, whether or not those
              transactions were approved through the Service.
            </li>
            <li>
              LetAgentPay shall not be liable for losses resulting from
              inaccurate AI-generated policy conversions. You are responsible
              for reviewing and confirming your spending policies.
            </li>
            <li>
              Our total aggregate liability shall not exceed the amount you
              paid us in the 12 months preceding the claim, or $100 USD,
              whichever is greater.
            </li>
          </ul>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">12. Indemnification</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            You agree to indemnify and hold harmless LetAgentPay from any claims,
            damages, losses, or expenses (including reasonable legal fees)
            arising from: your use of the Service, your violation of these Terms,
            or transactions executed by your AI agents.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">13. Termination</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            You may stop using the Service at any time. To delete your account
            and associated data, contact us at{" "}
            <a
              href="mailto:support@letagentpay.com"
              className="text-primary underline hover:no-underline"
            >
              support@letagentpay.com
            </a>
            . We may suspend or terminate your access if you violate these Terms
            or if continued access poses a risk to the Service or other users.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            Upon termination, your right to use the Service ceases immediately.
            We will delete your data in accordance with our{" "}
            <Link
              href="/privacy"
              className="text-primary underline hover:no-underline"
            >
              Privacy Policy
            </Link>
            .
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">14. Dispute resolution and governing law</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            We encourage you to contact us first at{" "}
            <a
              href="mailto:support@letagentpay.com"
              className="text-primary underline hover:no-underline"
            >
              support@letagentpay.com
            </a>{" "}
            to resolve any disputes informally.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            These Terms are governed by the laws of Germany and the European
            Union. Any disputes that cannot be resolved informally shall be
            subject to the jurisdiction of the courts of Germany.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">15. Self-hosted deployments</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            LetAgentPay is available as a self-hosted solution under an
            open-source license. If you self-host LetAgentPay, these Terms apply
            only to your use of the hosted version at letagentpay.com.
            Self-hosted deployments are governed by the applicable open-source
            license. You are solely responsible for data handling, security, and
            compliance of your self-hosted instance.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">16. Changes to these terms</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            We may update these Terms from time to time. We will notify you of
            material changes by posting the updated Terms on this page with a
            revised &quot;Last updated&quot; date. Your continued use of the
            Service after changes constitutes acceptance of the updated Terms.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">17. Contact</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            If you have questions about these Terms, contact us at{" "}
            <a
              href="mailto:support@letagentpay.com"
              className="text-primary underline hover:no-underline"
            >
              support@letagentpay.com
            </a>
            .
          </p>
        </section>
      </article>

      <PublicFooter />
    </div>
  );
}