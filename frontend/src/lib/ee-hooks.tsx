/**
 * Extension points for enterprise features.
 *
 * Core (self-hosted) version: all functions are no-ops.
 * Enterprise overlay replaces this file with real implementations
 * (PostHog analytics, billing section, admin navigation, etc.)
 */
import type { ReactNode } from "react";
import type { AccountResponse } from "@/lib/types";

/* eslint-disable @typescript-eslint/no-unused-vars */

// Analytics — no-op in core
export function track(
  _event: string,
  _props?: Record<string, unknown>,
): void {}
export function identify(
  _userId: string,
  _props?: Record<string, unknown>,
): void {}
export function resetAnalytics(): void {}

// Providers — no additional providers in core
export function EEProvider({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

// Settings — no billing section in core
export function EESettingsSection(_props: {
  account: AccountResponse | null;
  refresh: () => Promise<void>;
}) {
  return null;
}

// Dashboard nav — no admin nav in core
export function getEENavItems(
  _isAdmin: boolean,
): { href: string; label: string; icon: React.ComponentType<{ className?: string }> }[] {
  return [];
}
