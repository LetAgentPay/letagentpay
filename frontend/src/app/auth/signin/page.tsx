"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { VersionLink } from "@/components/version-link";

type AuthMode = "magic_link" | "password" | null;

function authError(err: unknown): string {
  if (err instanceof ApiError) return err.detail;
  const msg = err instanceof Error ? err.message : String(err);
  console.error("Auth error:", msg, err);
  return `Connection error: ${msg}`;
}

export default function SignInPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [authMode, setAuthMode] = useState<AuthMode>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [otpCode, setOtpCode] = useState("");
  const [verifying, setVerifying] = useState(false);
  const otpRef = useRef<HTMLInputElement>(null);
  const submittingRef = useRef(false);

  useEffect(() => {
    api.authMode().then((res) => setAuthMode(res.mode)).catch((err) => {
      console.error("authMode failed:", err);
      setAuthMode("magic_link");
    });
  }, []);

  async function handleMagicLink(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await api.sendLink(email);
      setSent(true);
    } catch (err) {
      setError(authError(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOtp(e: React.FormEvent) {
    e.preventDefault();
    if (submittingRef.current) return;
    submittingRef.current = true;
    setError("");
    setVerifying(true);

    try {
      await api.verifyOtp(email, otpCode);
      await refresh();
      router.push("/dashboard");
    } catch (err) {
      setError(authError(err));
    } finally {
      setVerifying(false);
      submittingRef.current = false;
    }
  }

  async function handleResend() {
    setError("");
    setOtpCode("");
    setLoading(true);

    try {
      await api.sendLink(email);
    } catch (err) {
      setError(authError(err));
    } finally {
      setLoading(false);
    }
  }

  async function handlePasswordLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await api.passwordLogin(password);
      await refresh();
      router.push("/dashboard");
    } catch (err) {
      setError(authError(err));
    } finally {
      setLoading(false);
    }
  }

  if (!authMode) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-center text-2xl">LetAgentPay</CardTitle>
        </CardHeader>
        <CardContent>
          {authMode === "password" ? (
            <form onSubmit={handlePasswordLogin} className="space-y-4">
              <div className="space-y-2">
                <Input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoFocus
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Signing in..." : "Sign in"}
              </Button>
            </form>
          ) : sent ? (
            <div className="space-y-4">
              <div className="space-y-2 text-center">
                <p className="text-lg font-medium">Check your email</p>
                <p className="text-sm text-muted-foreground">
                  We sent a sign-in code to <strong>{email}</strong>
                </p>
              </div>
              <form onSubmit={handleVerifyOtp} className="space-y-4">
                <Input
                  ref={otpRef}
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  autoComplete="one-time-code"
                  placeholder="000000"
                  value={otpCode}
                  onChange={(e) => {
                    const v = e.target.value.replace(/\D/g, "").slice(0, 6);
                    setOtpCode(v);
                  }}
                  className="text-center text-2xl tracking-[0.3em] font-mono"
                  autoFocus
                />
                {error && <p className="text-sm text-destructive">{error}</p>}
                <Button
                  type="submit"
                  className="w-full"
                  disabled={verifying || otpCode.length !== 6}
                >
                  {verifying ? "Verifying..." : "Verify code"}
                </Button>
              </form>
              <p className="text-center text-sm text-muted-foreground">
                Didn&apos;t receive it?{" "}
                <button
                  type="button"
                  onClick={handleResend}
                  disabled={loading}
                  className="underline hover:text-foreground"
                >
                  {loading ? "Sending..." : "Resend code"}
                </button>
              </p>
            </div>
          ) : (
            <form onSubmit={handleMagicLink} className="space-y-4">
              <div className="space-y-2">
                <Input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Sending..." : "Send magic link"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
      <Link
        href="/"
        className="mt-6 text-sm text-muted-foreground hover:text-foreground"
      >
        &larr; Back to home
      </Link>
      <p className="mt-2 text-xs opacity-30"><VersionLink /></p>
    </div>
  );
}
