"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
  SheetTitle,
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { Home, Settings, BookOpen, LogOut, Menu, FlaskConical, LifeBuoy } from "lucide-react";
import { getEENavItems } from "@/lib/ee-hooks";
import { openSupportEmail } from "@/components/support-link";

const navItems = [
  { href: "/dashboard", label: "Home", icon: Home, exact: true },
  { href: "/dashboard/sandbox", label: "Sandbox", icon: FlaskConical },
  { href: "/dashboard/guide", label: "Guide", icon: BookOpen },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading, account, isAdmin, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.replace("/auth/signin");
    }
  }, [loading, isAuthenticated, router]);

  if (loading || !isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }
  const allNavItems = [...navItems, ...getEENavItems(isAdmin)];

  const isActive = (item: (typeof allNavItems)[number]) =>
    "exact" in item && item.exact
      ? pathname === item.href
      : pathname === item.href || pathname.startsWith(item.href + "/");

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-56 border-r bg-background md:flex md:flex-col">
        <div className="flex h-14 items-center gap-2 border-b px-4">
          <Image src="/icons/icon-logo-dark.png" alt="" width={24} height={24} />
          <span className="text-lg font-bold">LetAgentPay</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {allNavItems.map((item) => (
            <Link key={item.href} href={item.href}>
              <Button
                variant={isActive(item) ? "secondary" : "ghost"}
                className="w-full justify-start"
              >
                <item.icon className="mr-2 h-4 w-4" />
                {item.label}
              </Button>
            </Link>
          ))}
          <Separator className="my-2" />
          <Button
            variant="ghost"
            className="w-full justify-start"
            onClick={openSupportEmail}
          >
            <LifeBuoy className="mr-2 h-4 w-4" />
            Support
          </Button>
          <Button
            variant="ghost"
            className="w-full justify-start text-destructive"
            onClick={logout}
          >
            <LogOut className="mr-2 h-4 w-4" />
            Logout
          </Button>
          <div className="mt-auto pt-3 text-center text-xs opacity-40">
            v{process.env.NEXT_PUBLIC_APP_VERSION}
          </div>
        </nav>
      </aside>

      {/* Main content area */}
      <div className="md:pl-56">
        <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur">
          <div className="flex h-14 items-center px-4">
            {/* Mobile hamburger */}
            <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
              <SheetTrigger className="mr-2 inline-flex shrink-0 items-center justify-center rounded-lg p-2 hover:bg-muted md:hidden">
                <Menu className="h-5 w-5" />
              </SheetTrigger>
              <SheetContent side="left" className="w-64">
                <SheetTitle className="flex items-center gap-2 text-lg font-bold px-2">
                  <Image src="/icons/icon-logo-dark.png" alt="" width={24} height={24} />
                  LetAgentPay
                </SheetTitle>
                <Separator className="my-2" />
                <nav className="flex flex-col gap-1 px-2">
                  {allNavItems.map((item) => (
                    <Link key={item.href} href={item.href} onClick={() => setMobileMenuOpen(false)}>
                      <Button
                        variant={
                          pathname === item.href || pathname.startsWith(item.href + "/") ? "secondary" : "ghost"
                        }
                        className="w-full justify-start"
                      >
                        <item.icon className="mr-2 h-4 w-4" />
                        {item.label}
                      </Button>
                    </Link>
                  ))}
                  <Separator className="my-2" />
                  <Button
                    variant="ghost"
                    className="w-full justify-start"
                    onClick={() => {
                      setMobileMenuOpen(false);
                      openSupportEmail();
                    }}
                  >
                    <LifeBuoy className="mr-2 h-4 w-4" />
                    Support
                  </Button>
                  <Button
                    variant="ghost"
                    className="w-full justify-start text-destructive"
                    onClick={() => { setMobileMenuOpen(false); logout(); }}
                  >
                    <LogOut className="mr-2 h-4 w-4" />
                    Logout
                  </Button>
                  <div className="mt-auto pt-3 text-center text-xs opacity-40">
                    v{process.env.NEXT_PUBLIC_APP_VERSION}
                  </div>
                </nav>
              </SheetContent>
            </Sheet>
            <h1 className="flex items-center gap-2 text-lg font-bold md:hidden">
              <Image src="/icons/icon-logo-dark.png" alt="" width={24} height={24} />
              LetAgentPay
            </h1>
            <div className="ml-auto flex items-center gap-2">
              {isAdmin && (
                <span className="rounded bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary">
                  Admin
                </span>
              )}
              {account?.email && (
                <span className="text-sm text-muted-foreground truncate max-w-[200px]">
                  {account.email}
                </span>
              )}
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-2xl p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
