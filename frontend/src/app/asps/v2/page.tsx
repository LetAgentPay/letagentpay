import { readFile } from "fs/promises";
import { existsSync } from "fs";
import { join } from "path";
import Link from "next/link";
import type { Metadata } from "next";
import { PublicNav } from "@/components/public-nav";
import { PublicFooter } from "@/components/public-footer";
import { MarkdownRenderer } from "@/components/markdown-renderer";

export const metadata: Metadata = {
  title: "ASPS v2: Mission Policy Specification",
  description:
    "Multi-agent coordination — shared budgets, phases, dependencies, dynamic allocation, risk scoring.",
};

async function getSpecContent(): Promise<string> {
  const candidates = [
    join(process.cwd(), "public", "asps", "v2-spec.md"),
    join(process.cwd(), "..", "docs", "core", "docs", "mission_policy_spec.md"),
    join(process.cwd(), "..", "docs", "mission_policy_spec.md"),
  ];
  for (const p of candidates) {
    if (existsSync(p)) return readFile(p, "utf-8");
  }
  return "# Specification not available\n\nMarkdown source not found.";
}

export default async function AspsV2Page() {
  const content = await getSpecContent();

  return (
    <div className="min-h-screen bg-background">
      <PublicNav />

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
