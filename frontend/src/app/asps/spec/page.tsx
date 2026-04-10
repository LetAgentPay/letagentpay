import { readFile } from "fs/promises";
import { join } from "path";
import Link from "next/link";
import type { Metadata } from "next";
import { PublicNav } from "@/components/public-nav";
import { PublicFooter } from "@/components/public-footer";
import { MarkdownRenderer } from "@/components/markdown-renderer";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://letagentpay.com";

export const metadata: Metadata = {
  title: "ASPS v1 Specification",
  description:
    "ASPS v1 — single-agent spending policies. Budgets, limits, categories, schedules, auto-approval, conformance requirements.",
};

async function getSpecContent(): Promise<string> {
  const specPath = join(process.cwd(), "public", "asps", "v1-spec.md");
  return readFile(specPath, "utf-8");
}

export default async function AspsSpecPage() {
  const content = await getSpecContent();

  return (
    <div className="min-h-screen bg-background">
      <PublicNav />

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "TechArticle",
            headline: "ASPS v1 — Agent Spending Policy Specification",
            description:
              "ASPS v1 — single-agent spending policies. Budgets, limits, categories, schedules, auto-approval, conformance requirements.",
            url: `${siteUrl}/asps/spec`,
            publisher: {
              "@type": "Organization",
              name: "LetAgentPay",
              url: siteUrl,
            },
          }),
        }}
      />

      <article className="mx-auto max-w-3xl px-4 py-12">
        <div className="flex items-center gap-3">
          <Link
            href="/asps"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            &larr; ASPS
          </Link>
        </div>

        <div className="mt-6">
          <MarkdownRenderer content={content} />
        </div>
      </article>

      <PublicFooter />
    </div>
  );
}