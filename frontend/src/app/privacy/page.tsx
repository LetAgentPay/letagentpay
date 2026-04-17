import Link from "next/link";
import type { Metadata } from "next";
import { PublicNav } from "@/components/public-nav";
import { PublicFooter } from "@/components/public-footer";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description:
    "LetAgentPay Privacy Policy — how we collect, use, and protect your data.",
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background">
      <PublicNav />

      <article className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-3xl font-bold">Privacy Policy</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Last updated: April 17, 2026
        </p>

        <div className="mt-6 rounded-lg border bg-muted/50 p-4 text-sm leading-relaxed text-muted-foreground">
          <strong className="text-foreground">Short version:</strong> we collect
          your email, one cookie keeps you logged in, we don&apos;t track you,
          we don&apos;t sell your data. If you use x402, we also store your
          wallet address and transaction hashes. The long version is below.
        </div>

        <section className="mt-10">
          <h2 className="text-xl font-bold">1. Who we are</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            LetAgentPay (&quot;we&quot;, &quot;us&quot;, &quot;our&quot;) operates
            the website{" "}
            <Link href="/" className="text-primary underline hover:no-underline">
              letagentpay.com
            </Link>{" "}
            and provides a policy middleware service for AI agents. This Privacy
            Policy explains how we collect, use, store, and protect your personal
            data when you use our website and services.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            For questions about this policy, contact us at{" "}
            <a
              href="mailto:support@letagentpay.com"
              className="text-primary underline hover:no-underline"
            >
              support@letagentpay.com
            </a>
            .
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">2. Data we collect</h2>

          <h3 className="mt-6 font-semibold">Account data</h3>
          <p className="mt-2 leading-relaxed text-muted-foreground">
            When you create an account, we collect your <strong className="text-foreground">email address</strong>.
            This is the only personal information required to use LetAgentPay. We
            use passwordless authentication via magic links sent to your email.
            You may optionally provide a display name, preferred currency, and
            timezone.
          </p>

          <h3 className="mt-6 font-semibold">Agent and transaction data</h3>
          <p className="mt-2 leading-relaxed text-muted-foreground">
            When you create agents and they submit purchase requests, we store:
            agent names and configurations, spending policies, purchase request
            details (amount, category, merchant, description), and approval/rejection
            decisions. This data is necessary to operate the service and provide
            audit trails.
          </p>

          <h3 className="mt-6 font-semibold">Notification data</h3>
          <p className="mt-2 leading-relaxed text-muted-foreground">
            If you enable notifications, we store the configuration needed to
            deliver them: Web Push subscription endpoints and Telegram usernames.
          </p>

          <h3 className="mt-6 font-semibold">Blockchain data (x402)</h3>
          <p className="mt-2 leading-relaxed text-muted-foreground">
            If you use the x402 protocol for on-chain payments, we additionally
            store: wallet addresses, blockchain network identifiers, and
            transaction hashes. Wallet addresses may be publicly linkable to
            on-chain activity.
          </p>

          <h3 className="mt-6 font-semibold">Technical data</h3>
          <p className="mt-2 leading-relaxed text-muted-foreground">
            Our servers automatically collect standard technical information when
            you access the website: IP address, browser type, and request
            timestamps. This data is used solely for security monitoring and
            service operation. We do not use third-party analytics or tracking
            services.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">3. How we use your data</h2>
          <ul className="mt-4 list-inside list-disc space-y-2 text-muted-foreground">
            <li>
              <strong className="text-foreground">Provide the service</strong> —
              authenticate your account, enforce spending policies, process purchase
              requests, and maintain audit logs.
            </li>
            <li>
              <strong className="text-foreground">Send transactional emails</strong> —
              magic link authentication, purchase notifications, and critical
              service alerts. We do not send marketing emails.
            </li>
            <li>
              <strong className="text-foreground">Improve and secure the service</strong> —
              monitor for abuse, debug issues, and improve performance.
            </li>
          </ul>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">4. Legal basis for processing (GDPR)</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            If you are in the European Economic Area (EEA), UK, or Switzerland,
            we process your data under the following legal bases:
          </p>
          <ul className="mt-4 list-inside list-disc space-y-2 text-muted-foreground">
            <li>
              <strong className="text-foreground">Contract performance</strong> —
              processing necessary to provide the service you signed up for
              (account management, policy enforcement, purchase processing).
            </li>
            <li>
              <strong className="text-foreground">Legitimate interest</strong> —
              security monitoring, fraud prevention, and service improvement.
            </li>
          </ul>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">5. Cookies</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            We use a single, strictly necessary cookie:
          </p>
          <div className="mt-4 overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-4 py-2 text-left font-medium">Cookie</th>
                  <th className="px-4 py-2 text-left font-medium">Purpose</th>
                  <th className="px-4 py-2 text-left font-medium">Duration</th>
                  <th className="px-4 py-2 text-left font-medium">Type</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="px-4 py-2 font-mono text-xs">access_token</td>
                  <td className="px-4 py-2 text-muted-foreground">
                    Keeps you signed in (JWT authentication)
                  </td>
                  <td className="px-4 py-2 text-muted-foreground">7 days</td>
                  <td className="px-4 py-2 text-muted-foreground">
                    Strictly necessary
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="mt-4 leading-relaxed text-muted-foreground">
            This cookie is HTTP-only and secure. It cannot be read by JavaScript
            and is only sent over HTTPS in production. We do not use any
            analytics, advertising, or third-party tracking cookies.
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            Because this cookie is strictly necessary for the service to function,
            no consent banner is required under the EU ePrivacy Directive.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">6. Data sharing</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            We do not sell your personal data. We share data only with the
            following categories of service providers, solely to operate the
            service:
          </p>
          <ul className="mt-4 list-inside list-disc space-y-2 text-muted-foreground">
            <li>
              <strong className="text-foreground">Email delivery</strong> —
              Resend (for sending magic links and notifications).
            </li>
            <li>
              <strong className="text-foreground">AI processing</strong> —
              Anthropic (for converting natural language policies to structured
              rules). Policy text and conversation context are sent; account
              identifiers are not included.
            </li>
            <li>
              <strong className="text-foreground">Infrastructure</strong> —
              hosting providers that store and process data on our behalf.
            </li>
          </ul>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            We may also disclose data if required by law or to protect our legal
            rights.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">7. Data retention</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            We retain your account data and transaction history for as long as
            your account is active. If you request account deletion, we will
            remove your personal data within 30 days, except where retention is
            required by law or for legitimate business purposes (e.g., fraud
            prevention).
          </p>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            Server logs containing IP addresses are retained for up to 90 days.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">8. Data security</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            We implement appropriate technical and organizational measures to
            protect your data, including: encrypted connections (TLS/HTTPS),
            HTTP-only secure authentication cookies, hashed tokens, and access
            controls on production systems. We do not store passwords — authentication
            is passwordless via magic links.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">9. Your rights</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            Depending on your location, you may have the following rights
            regarding your personal data:
          </p>

          <h3 className="mt-6 font-semibold">For all users</h3>
          <ul className="mt-2 list-inside list-disc space-y-2 text-muted-foreground">
            <li>Access your personal data</li>
            <li>Request correction of inaccurate data</li>
            <li>Request deletion of your account and data</li>
            <li>Request a copy of your data in a portable format</li>
          </ul>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            To exercise any of these rights, contact us at{" "}
            <a
              href="mailto:support@letagentpay.com"
              className="text-primary underline hover:no-underline"
            >
              support@letagentpay.com
            </a>
            . We will process your request within 30 days.
          </p>

          <h3 className="mt-6 font-semibold">
            Additional rights for EEA/UK residents (GDPR)
          </h3>
          <ul className="mt-2 list-inside list-disc space-y-2 text-muted-foreground">
            <li>Object to processing based on legitimate interest</li>
            <li>Request restriction of processing</li>
            <li>
              Lodge a complaint with your local data protection authority
            </li>
          </ul>

          <h3 className="mt-6 font-semibold">
            Additional rights for California residents (CCPA)
          </h3>
          <ul className="mt-2 list-inside list-disc space-y-2 text-muted-foreground">
            <li>
              Know what personal information is collected and how it is used
            </li>
            <li>Request deletion of personal information</li>
            <li>
              Non-discrimination for exercising your privacy rights
            </li>
            <li>
              We do not sell personal information, so the right to opt-out of
              sale does not apply
            </li>
          </ul>

        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">10. International data transfers</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            Your data may be processed in countries outside your country of
            residence. When we transfer data internationally, we ensure
            appropriate safeguards are in place, including standard contractual
            clauses where required.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">11. Children</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            LetAgentPay is not intended for use by individuals under the age of
            16. We do not knowingly collect personal data from children. If you
            believe a child has provided us with personal data, please contact us
            and we will delete it.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">12. Self-hosted deployments</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            If you self-host LetAgentPay, you are the data controller for all
            data processed by your instance. This Privacy Policy applies only to
            the hosted version at letagentpay.com. Self-hosted operators are
            responsible for their own data handling practices and compliance.
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">13. Governing law</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            This Privacy Policy is governed by the laws of Germany and the
            European Union, including the General Data Protection Regulation
            (GDPR).
          </p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-bold">14. Changes to this policy</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            We may update this Privacy Policy from time to time. We will notify
            you of material changes by posting the updated policy on this page
            with a revised &quot;Last updated&quot; date. Your continued use of
            the service after changes constitutes acceptance of the updated policy.
          </p>
        </section>
      </article>

      <PublicFooter />
    </div>
  );
}