import Link from "next/link";
import { VersionLink } from "@/components/version-link";
import { SupportLink } from "@/components/support-link";

export function PublicFooter() {
  return (
    <footer className="border-t py-8">
      <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 px-4 text-sm text-muted-foreground sm:flex-row sm:gap-0">
        <span>
          LetAgentPay &copy; {new Date().getFullYear()}
          <VersionLink className="ml-2 text-xs opacity-40" />
        </span>
        <div className="flex gap-4">
          <Link href="/about" className="hover:text-foreground">
            About
          </Link>
          <Link href="/developers" className="hover:text-foreground">
            Developers
          </Link>
          <Link href="/asps" className="hover:text-foreground">
            ASPS
          </Link>
          <SupportLink className="hover:text-foreground" />
        </div>
      </div>
    </footer>
  );
}