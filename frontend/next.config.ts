import type { NextConfig } from "next";
import { readFileSync, existsSync } from "fs";
import { resolve } from "path";

// App version: prefer env var (Docker build arg), fallback to version.py, then "dev"
let APP_VERSION = process.env.APP_VERSION || "dev";
if (APP_VERSION === "dev") {
  const versionPath = resolve(__dirname, "../version.py");
  if (existsSync(versionPath)) {
    const match = readFileSync(versionPath, "utf-8").match(
      /__version__\s*=\s*"(.+?)"/,
    );
    if (match) APP_VERSION = match[1];
  }
}

// INTERNAL_API_URL — server-side only (Docker: http://backend:8000)
// NEXT_PUBLIC_API_URL — visible to browser (external URL)
// Falls back to localhost for local dev
const BACKEND_URL =
  process.env.INTERNAL_API_URL ||
  (process.env.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL.replace(/\/api\/v1$/, "")
    : "http://localhost:8000");

const nextConfig: NextConfig = {
  typescript: {
    // Type-checking runs in CI (lint + test stages); skip during docker build
    // to avoid OOM on memory-constrained VPS.
    ignoreBuildErrors: true,
  },
  env: {
    NEXT_PUBLIC_APP_VERSION: APP_VERSION,
  },
  output:
    process.env.NEXT_PUBLIC_SELF_HOSTED === "true" ||
    process.env.INTERNAL_API_URL
      ? "standalone"
      : undefined,
  headers: async () => [
    {
      source: "/sw.js",
      headers: [
        {
          key: "Cache-Control",
          value: "no-cache, no-store, must-revalidate",
        },
        {
          key: "Service-Worker-Allowed",
          value: "/",
        },
      ],
    },
  ],
  rewrites: async () => [
    {
      // Proxy all /api/v1/* requests to backend — same origin, no CORS issues
      source: "/api/v1/:path*",
      destination: `${BACKEND_URL}/api/v1/:path*`,
    },
  ],
};

export default nextConfig;
