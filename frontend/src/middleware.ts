import { NextResponse, type NextRequest } from "next/server";

const ATTR_COOKIE = "lap_attribution";
const ATTR_MAX_AGE = 60 * 60 * 24 * 30; // 30 days

const LANDING_PATHS: Record<string, string> = {
  "/": "home",
  "/middleware": "middleware",
  "/x402": "x402",
};

const truncate = (v: string, max: number) => v.slice(0, max);

export function middleware(req: NextRequest) {
  const url = req.nextUrl;
  const params = url.searchParams;

  const utmSource = params.get("utm_source");
  const utmMedium = params.get("utm_medium");
  const utmCampaign = params.get("utm_campaign");
  const utmContent = params.get("utm_content");
  const landing = LANDING_PATHS[url.pathname];

  const hasUtm = !!(utmSource || utmMedium || utmCampaign || utmContent);
  const existing = req.cookies.get(ATTR_COOKIE);

  // Set when we have a fresh UTM signal, OR when landing on a positioned
  // page for the first time (no cookie yet).
  const shouldSet = hasUtm || (!!landing && !existing);
  if (!shouldSet) return NextResponse.next();

  let merged: Record<string, string> = {};
  if (existing) {
    try {
      const parsed = JSON.parse(existing.value);
      if (parsed && typeof parsed === "object") merged = parsed;
    } catch {
      // ignore malformed cookie
    }
  }

  if (landing && !merged.landing) merged.landing = truncate(landing, 64);
  if (utmSource) merged.source = truncate(utmSource, 64);
  if (utmMedium) merged.medium = truncate(utmMedium, 64);
  if (utmCampaign) merged.campaign = truncate(utmCampaign, 128);
  if (utmContent) merged.content = truncate(utmContent, 128);

  const res = NextResponse.next();
  res.cookies.set(ATTR_COOKIE, JSON.stringify(merged), {
    maxAge: ATTR_MAX_AGE,
    path: "/",
    sameSite: "lax",
    httpOnly: false,
  });
  return res;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon|icons|api/).*)"],
};
