import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.INTERNAL_API_URL ||
  (process.env.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL.replace(/\/api\/v1$/, "")
    : "http://localhost:8000");

/**
 * Server-side Route Handler for magic link verification.
 *
 * The magic link sends the user here (GET /auth/verify?token=...).
 * We call the backend verify endpoint server-side, forward Set-Cookie,
 * and redirect to dashboard. This avoids the Next.js rewrite proxy
 * which doesn't forward Set-Cookie headers.
 */
export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("token");
  if (!token) {
    return NextResponse.redirect(new URL("/auth/signin", request.url));
  }

  const backendUrl = `${BACKEND_URL}/api/v1/auth/verify?token=${encodeURIComponent(token)}`;

  try {
    const backendResp = await fetch(backendUrl, { redirect: "manual" });

    if (backendResp.status === 302) {
      // Success — backend returns 302 + Set-Cookie
      const resp = NextResponse.redirect(new URL("/dashboard", request.url));

      // Forward Set-Cookie headers from backend
      for (const cookie of backendResp.headers.getSetCookie()) {
        resp.headers.append("set-cookie", cookie);
      }
      return resp;
    }

    // Error from backend (invalid/expired token)
    return NextResponse.redirect(
      new URL("/auth/signin?error=invalid_token", request.url),
    );
  } catch {
    return NextResponse.redirect(
      new URL("/auth/signin?error=server_error", request.url),
    );
  }
}