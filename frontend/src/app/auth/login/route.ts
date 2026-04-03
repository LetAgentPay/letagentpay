import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.INTERNAL_API_URL ||
  (process.env.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL.replace(/\/api\/v1$/, "")
    : "http://localhost:8000");

/**
 * Server-side Route Handler for password login (self-hosted mode).
 *
 * Same pattern as /auth/verify-otp: the Next.js rewrite proxy doesn't
 * forward Set-Cookie headers, so we proxy the request server-side and
 * forward the cookie to the browser.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const backendResp = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Forwarded-For":
          request.headers.get("x-forwarded-for") ??
          request.headers.get("x-real-ip") ??
          "unknown",
      },
      body: JSON.stringify(body),
    });

    const data = await backendResp.json();

    const resp = NextResponse.json(data, { status: backendResp.status });

    // Forward Set-Cookie headers from backend
    for (const cookie of backendResp.headers.getSetCookie()) {
      resp.headers.append("set-cookie", cookie);
    }

    return resp;
  } catch (err) {
    console.error("[login] route handler error:", err);
    return NextResponse.json(
      { detail: "Server error" },
      { status: 500 },
    );
  }
}