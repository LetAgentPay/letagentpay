import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.INTERNAL_API_URL ||
  (process.env.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL.replace(/\/api\/v1$/, "")
    : "http://localhost:8000");

/**
 * Server-side Route Handler for OTP code verification.
 *
 * The frontend calls this (POST /auth/verify-otp) instead of the backend
 * directly, because the Next.js rewrite proxy doesn't forward Set-Cookie
 * headers. This route calls the backend, forwards Set-Cookie, and returns
 * a JSON response the client can act on.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const backendResp = await fetch(`${BACKEND_URL}/api/v1/auth/verify-otp`, {
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
    console.error("[verify-otp] route handler error:", err);
    return NextResponse.json(
      { detail: "Server error" },
      { status: 500 },
    );
  }
}
