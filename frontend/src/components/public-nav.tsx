"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
  SheetTitle,
} from "@/components/ui/sheet";
import { SupportLink } from "@/components/support-link";
import { usePublicConfig } from "@/lib/hooks/use-public-config";
import { getEEPublicLinks } from "@/lib/ee-hooks";

const BASE_NAV_LINKS = [
  { href: "/about", label: "About" },
  { href: "/developers", label: "Developers" },
  { href: "/asps", label: "ASPS" },
];

export function PublicNav() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { playground_enabled } = usePublicConfig();

  const eeLinks = getEEPublicLinks();
  const NAV_LINKS = [
    BASE_NAV_LINKS[0],
    ...eeLinks,
    ...BASE_NAV_LINKS.slice(1),
    ...(playground_enabled
      ? [{ href: "/playground", label: "Playground" }]
      : []),
  ];

  const linkClass = (href: string) =>
    pathname === href
      ? "text-sm font-medium text-foreground"
      : "text-sm font-medium text-muted-foreground hover:text-foreground";

  return (
    <nav className="border-b">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
        <Link href="/" className="flex items-center gap-2">
          <Image
            src="/icons/icon-logo-dark.png"
            alt="LetAgentPay"
            width={28}
            height={28}
          />
          <span className="text-lg font-bold">LetAgentPay</span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden items-center gap-4 md:flex">
          {NAV_LINKS.map(({ href, label }) => (
            <Link key={href} href={href} className={linkClass(href)}>
              {label}
            </Link>
          ))}
          <SupportLink className="text-sm font-medium text-muted-foreground hover:text-foreground" />
          <Link
            href="/auth/signin"
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Sign In
          </Link>
        </div>

        {/* Mobile hamburger */}
        <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
          <SheetTrigger className="md:hidden" aria-label="Open menu">
            <Menu className="h-6 w-6" />
          </SheetTrigger>
          <SheetContent side="right" className="w-64">
            <SheetTitle className="px-4 pt-2">Menu</SheetTitle>
            <nav className="flex flex-col gap-1 px-4 pt-4">
              {NAV_LINKS.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`rounded-md px-3 py-2 ${
                    pathname === href
                      ? "bg-muted font-medium text-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  {label}
                </Link>
              ))}
              <SupportLink className="rounded-md px-3 py-2 text-left text-muted-foreground hover:bg-muted hover:text-foreground" />
              <div className="my-2 border-t" />
              <Link
                href="/auth/signin"
                onClick={() => setMobileMenuOpen(false)}
                className="rounded-md bg-primary px-3 py-2 text-center text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                Sign In
              </Link>
            </nav>
          </SheetContent>
        </Sheet>
      </div>
    </nav>
  );
}
