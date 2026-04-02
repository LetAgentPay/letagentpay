"use client";

import Link from "next/link";
import { ReactNode } from "react";
import { usePublicConfig } from "@/lib/hooks/use-public-config";

export function PlaygroundLink({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const { playground_enabled } = usePublicConfig();
  if (!playground_enabled) return null;
  return (
    <Link href="/playground" className={className}>
      {children}
    </Link>
  );
}

export function PlaygroundSection() {
  const { playground_enabled } = usePublicConfig();
  if (!playground_enabled) return null;
  return (
    <p className="mt-4 text-sm text-muted-foreground">
      Want to try it first?{" "}
      <Link href="/playground" className="text-primary underline">
        Open the Playground
      </Link>{" "}
      — no signup required.
    </p>
  );
}