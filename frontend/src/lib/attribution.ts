export type Attribution = {
  landing?: string;
  source?: string;
  medium?: string;
  campaign?: string;
  content?: string;
};

const COOKIE = "lap_attribution";

export function readAttribution(): Attribution | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|; )lap_attribution=([^;]+)/);
  if (!match) return null;
  try {
    const decoded = decodeURIComponent(match[1]);
    const parsed = JSON.parse(decoded);
    if (parsed && typeof parsed === "object") return parsed as Attribution;
  } catch {
    // ignore
  }
  return null;
}

export const ATTRIBUTION_COOKIE = COOKIE;
