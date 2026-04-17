"use client";

import Link from "next/link";
import { VersionLink } from "@/components/version-link";
import { SupportLink } from "@/components/support-link";
import { usePublicConfig } from "@/lib/hooks/use-public-config";
import { getEEPublicLinks } from "@/lib/ee-hooks";

const BASE_FOOTER_LINKS = [
  { href: "/about", label: "About" },
  { href: "/developers", label: "Developers" },
  { href: "/asps", label: "ASPS" },
];

const LEGAL_LINKS = [
  { href: "/privacy", label: "Privacy" },
  { href: "/terms", label: "Terms" },
];

export function PublicFooter() {
  const { playground_enabled } = usePublicConfig();

  const eeLinks = getEEPublicLinks();
  const links = [
    BASE_FOOTER_LINKS[0],
    ...eeLinks,
    ...BASE_FOOTER_LINKS.slice(1),
    ...(playground_enabled
      ? [{ href: "/playground", label: "Playground" }]
      : []),
  ];

  return (
    <footer className="border-t py-8">
      <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 px-4 text-sm text-muted-foreground sm:flex-row sm:gap-0">
        <span>
          LetAgentPay &copy; {new Date().getFullYear()}
          <VersionLink className="ml-2 text-xs opacity-40" />
        </span>
        <div className="flex flex-wrap justify-center gap-4">
          {links.map(({ href, label }) => (
            <Link key={href} href={href} className="hover:text-foreground">
              {label}
            </Link>
          ))}
          <SupportLink className="hover:text-foreground" />
          <span className="text-muted-foreground/40">|</span>
          {LEGAL_LINKS.map(({ href, label }) => (
            <Link key={href} href={href} className="hover:text-foreground">
              {label}
            </Link>
          ))}
        </div>
      </div>
    </footer>
  );
}
