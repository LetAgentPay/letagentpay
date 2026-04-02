"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { BudgetBar } from "@/components/budget-bar";
import Link from "next/link";
import { PublicNav } from "@/components/public-nav";
import { usePublicConfig } from "@/lib/hooks/use-public-config";
import { useRouter } from "next/navigation";
import {
  Send,
  CheckCircle2,
  Clock,
  XCircle,
  ChevronDown,
  ChevronUp,
  Zap,
  Timer,
  ArrowRight,
} from "lucide-react";

const API_URL = "/api/v1";

const SAMPLE_REQUESTS = [
  { amount: "4.99", category: "food_delivery", merchant_name: "Uber Eats", description: "Lunch delivery" },
  { amount: "12.50", category: "taxi", merchant_name: "Uber", description: "Ride to office" },
  { amount: "29.99", category: "subscriptions", merchant_name: "Netflix", description: "Monthly subscription" },
  { amount: "8.75", category: "groceries", merchant_name: "Whole Foods", description: "Snacks" },
  { amount: "45.00", category: "restaurants", merchant_name: "Sushi Place", description: "Team dinner" },
  { amount: "99.00", category: "electronics", merchant_name: "Amazon", description: "USB-C hub" },
  { amount: "5.99", category: "entertainment", merchant_name: "Spotify", description: "Music streaming" },
  { amount: "7.50", category: "education", merchant_name: "Coursera", description: "Course payment" },
];

const CATEGORIES = [
  "groceries", "restaurants", "food_delivery", "taxi", "transport",
  "subscriptions", "entertainment", "education", "health",
  "electronics", "clothing", "gas", "household", "flights",
  "accommodation", "other",
];

interface PolicyCheck {
  rule: string;
  result: string;
  detail: string;
}

interface PlaygroundResult {
  id: string;
  timestamp: Date;
  amount: string;
  category: string;
  merchant: string;
  status: string;
  request_id?: string;
  checks?: PolicyCheck[];
  budget_remaining?: string;
  error?: string;
}

interface PolicyData {
  auto_approve?: { enabled: boolean; max_amount: number };
  daily_limit?: number;
  weekly_limit?: number;
  monthly_limit?: number;
  per_request_limit?: number;
  categories?: {
    allowed?: string[];
    blocked?: string[];
  };
}

interface SessionData {
  session_id: string;
  agent_token: string;
  agent_name: string;
  budget: string;
  currency: string;
  policy: PolicyData;
  policy_text: string;
  expires_in: number;
  max_requests: number;
}

async function agentApiRequest(
  token: string,
  path: string,
  options?: RequestInit,
) {
  const res = await fetch(`${API_URL}/agent-api${path}`, {
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options?.headers,
    },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || `Error ${res.status}`);
  }
  return data;
}

export default function PlaygroundPage() {
  const { playground_enabled, loaded: configLoaded } = usePublicConfig();
  const router = useRouter();

  useEffect(() => {
    if (configLoaded && !playground_enabled) {
      router.replace("/");
    }
  }, [configLoaded, playground_enabled, router]);

  const [session, setSession] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [results, setResults] = useState<PlaygroundResult[]>([]);
  const [expandedResult, setExpandedResult] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState(0);
  const [requestsUsed, setRequestsUsed] = useState(0);
  const [budgetInfo, setBudgetInfo] = useState<{
    budget: number;
    spent: number;
    held: number;
  } | null>(null);

  // Custom request form
  const [customAmount, setCustomAmount] = useState("");
  const [customCategory, setCustomCategory] = useState("");
  const [customMerchant, setCustomMerchant] = useState("");
  const [customDescription, setCustomDescription] = useState("");

  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const STORAGE_KEY = "playground_session";

  // Save session + expiry timestamp to sessionStorage
  const saveSession = useCallback((data: SessionData, expiresIn: number) => {
    const expiresAt = Date.now() + expiresIn * 1000;
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ ...data, expiresAt }));
  }, []);

  const clearSession = useCallback(() => {
    setSession(null);
    sessionStorage.removeItem(STORAGE_KEY);
  }, []);

  // Restore session from sessionStorage on mount
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const stored = JSON.parse(raw);
      const remaining = Math.floor((stored.expiresAt - Date.now()) / 1000);
      if (remaining <= 0) {
        sessionStorage.removeItem(STORAGE_KEY);
        return;
      }
      const { expiresAt: _, ...sessionData } = stored;
      setSession(sessionData as SessionData);
      setTimeLeft(remaining);
    } catch {
      sessionStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  // Fetch budget after session is restored
  useEffect(() => {
    if (!session || budgetInfo) return;
    (async () => {
      try {
        const data = await agentApiRequest(session.agent_token, "/budget");
        setBudgetInfo({
          budget: parseFloat(data.budget),
          spent: parseFloat(data.spent),
          held: parseFloat(data.held),
        });
      } catch {
        // Session expired on server — clear local state
        clearSession();
      }
    })();
  }, [session, budgetInfo, clearSession]);

  // Countdown timer
  const isActive = !!session && timeLeft > 0;
  useEffect(() => {
    if (!isActive) return;
    timerRef.current = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) {
          clearInterval(timerRef.current!);
          clearSession();
          return 0;
        }
        return t - 1;
      });
    }, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isActive, clearSession]);

  const createSession = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_URL}/playground/session`, {
        method: "POST",
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.detail || `Error ${resp.status}`);
      }
      const data: SessionData = await resp.json();
      setSession(data);
      setTimeLeft(data.expires_in);
      setRequestsUsed(0);
      setResults([]);
      setBudgetInfo({
        budget: parseFloat(data.budget),
        spent: 0,
        held: 0,
      });
      saveSession(data, data.expires_in);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create session"
      );
    } finally {
      setLoading(false);
    }
  }, [saveSession]);

  const refreshBudget = useCallback(async () => {
    if (!session) return;
    try {
      const data = await agentApiRequest(session.agent_token, "/budget");
      setBudgetInfo({
        budget: parseFloat(data.budget),
        spent: parseFloat(data.spent),
        held: parseFloat(data.held),
      });
    } catch {
      // silent
    }
  }, [session]);

  const maxReached = !!session && requestsUsed >= session.max_requests;

  async function sendRequest(data: {
    amount: string;
    category: string;
    merchant_name?: string;
    description?: string;
  }) {
    if (!session || maxReached) return;
    setSending(true);

    const resultEntry: PlaygroundResult = {
      id: crypto.randomUUID(),
      timestamp: new Date(),
      amount: data.amount,
      category: data.category,
      merchant: data.merchant_name || "",
      status: "sending",
    };

    setResults((prev) => [resultEntry, ...prev]);

    try {
      const resp = await agentApiRequest(session.agent_token, "/requests", {
        method: "POST",
        body: JSON.stringify({
          amount: data.amount,
          category: data.category,
          merchant_name: data.merchant_name || undefined,
          description: data.description || undefined,
          agent_comment: "Sent from Playground",
        }),
      });

      setResults((prev) =>
        prev.map((r) =>
          r.id === resultEntry.id
            ? {
                ...r,
                status: resp.status,
                request_id: resp.request_id,
                checks: resp.policy_check?.checks,
                budget_remaining: resp.budget_remaining,
              }
            : r,
        ),
      );
      setExpandedResult(resultEntry.id);
      setRequestsUsed((n) => n + 1);
      refreshBudget();
    } catch (err) {
      setResults((prev) =>
        prev.map((r) =>
          r.id === resultEntry.id
            ? {
                ...r,
                status: "error",
                error: err instanceof Error ? err.message : "Unknown error",
              }
            : r,
        ),
      );
    } finally {
      setSending(false);
    }
  }

  function handleCustomSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!customAmount || !customCategory) return;
    sendRequest({
      amount: customAmount,
      category: customCategory,
      merchant_name: customMerchant || undefined,
      description: customDescription || undefined,
    });
  }

  async function sendBurst() {
    if (!session) return;
    const samples = SAMPLE_REQUESTS.slice(0, 5);
    for (const sample of samples) {
      await sendRequest(sample);
      await new Promise((r) => setTimeout(r, 500));
    }
  }

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="min-h-screen bg-background">
      <PublicNav />

      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="mb-6 text-center">
          <h1 className="text-3xl font-bold">Playground</h1>
          <p className="mt-2 text-muted-foreground">
            Try LetAgentPay without signing up. Send purchase requests and see
            the policy engine in action.
          </p>
        </div>

        {/* No session — start button */}
        {!session && (
          <div className="text-center">
            <Card className="mx-auto max-w-md">
              <CardContent className="space-y-4 py-8">
                <p className="text-sm text-muted-foreground">
                  Start a 15-minute demo session with a randomly generated agent
                  and spending policy. See how the policy engine evaluates each
                  purchase in real time.
                </p>
                <Button
                  onClick={createSession}
                  disabled={loading}
                  size="lg"
                >
                  {loading ? "Starting..." : "Start Demo Session"}
                </Button>
                {error && (
                  <p className="text-sm text-destructive">{error}</p>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Active session */}
        {session && (
          <div className="space-y-6">
            {/* Session info bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/50 px-4 py-3">
              <div className="flex items-center gap-4 text-sm">
                <span className="flex items-center gap-1.5">
                  <Timer className="h-4 w-4 text-muted-foreground" />
                  <span className={timeLeft < 120 ? "font-medium text-destructive" : ""}>
                    {formatTime(timeLeft)}
                  </span>
                </span>
                <span className={maxReached ? "font-medium text-destructive" : "text-muted-foreground"}>
                  {requestsUsed}/{session.max_requests} requests
                </span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={sendBurst}
                disabled={sending || maxReached}
              >
                <Zap className="mr-1 h-3.5 w-3.5" />
                Send 5 Random
              </Button>
            </div>

            {/* Agent & Policy */}
            {budgetInfo && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">{session.agent_name} — Budget</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <BudgetBar
                    budget={budgetInfo.budget}
                    spent={budgetInfo.spent}
                    held={budgetInfo.held}
                    currency="USD"
                  />
                  <PolicyDisplay policy={session.policy} budget={session.budget} />
                </CardContent>
              </Card>
            )}

            {/* Quick send */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Quick Send</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {SAMPLE_REQUESTS.map((sample, i) => (
                    <Button
                      key={i}
                      variant="outline"
                      size="sm"
                      disabled={sending || maxReached}
                      onClick={() => sendRequest(sample)}
                      className="text-xs"
                    >
                      <Send className="mr-1 h-3 w-3" />
                      ${sample.amount} {sample.category}
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Custom request */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Custom Request</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCustomSubmit} className="space-y-3">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-1">
                      <Label htmlFor="pg-amount">Amount ($)</Label>
                      <Input
                        id="pg-amount"
                        type="number"
                        step="0.01"
                        min="0.01"
                        placeholder="25.00"
                        value={customAmount}
                        onChange={(e) => setCustomAmount(e.target.value)}
                        required
                      />
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor="pg-category">Category</Label>
                      <select
                        id="pg-category"
                        className="flex h-9 w-full rounded-md border bg-background px-3 py-1 text-sm"
                        value={customCategory}
                        onChange={(e) => setCustomCategory(e.target.value)}
                        required
                      >
                        <option value="">Select...</option>
                        {CATEGORIES.map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor="pg-merchant">Merchant (optional)</Label>
                      <Input
                        id="pg-merchant"
                        placeholder="Amazon"
                        value={customMerchant}
                        onChange={(e) => setCustomMerchant(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor="pg-desc">Description (optional)</Label>
                      <Input
                        id="pg-desc"
                        placeholder="Monthly subscription"
                        value={customDescription}
                        onChange={(e) => setCustomDescription(e.target.value)}
                      />
                    </div>
                  </div>
                  <Button type="submit" disabled={sending || maxReached}>
                    <Send className="mr-1 h-3.5 w-3.5" />
                    {maxReached ? "Limit reached" : sending ? "Sending..." : "Send Request"}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Results */}
            {results.length > 0 && (
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-base">
                    Results ({results.length})
                  </CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setResults([])}
                  >
                    Clear
                  </Button>
                </CardHeader>
                <CardContent className="space-y-2">
                  {results.map((r) => (
                    <div key={r.id} className="rounded-lg border p-3">
                      <div
                        className="flex cursor-pointer items-center justify-between"
                        onClick={() =>
                          setExpandedResult(
                            expandedResult === r.id ? null : r.id,
                          )
                        }
                      >
                        <div className="flex items-center gap-2">
                          <StatusIcon status={r.status} />
                          <span className="text-sm font-medium">
                            ${r.amount}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {r.category}
                          </span>
                          {r.merchant && (
                            <span className="text-xs text-muted-foreground">
                              — {r.merchant}
                            </span>
                          )}
                          <StatusBadge status={r.status} />
                        </div>
                        {r.checks &&
                          (expandedResult === r.id ? (
                            <ChevronUp className="h-4 w-4 text-muted-foreground" />
                          ) : (
                            <ChevronDown className="h-4 w-4 text-muted-foreground" />
                          ))}
                      </div>

                      {expandedResult === r.id && r.checks && (
                        <div className="mt-2 space-y-1 border-t pt-2">
                          {r.checks.map((check, i) => (
                            <div
                              key={i}
                              className="flex items-center gap-2 text-xs"
                            >
                              {check.result === "pass" ? (
                                <CheckCircle2 className="h-3 w-3 text-green-600" />
                              ) : (
                                <XCircle className="h-3 w-3 text-red-600" />
                              )}
                              <span className="font-medium">{check.rule}</span>
                              <span className="text-muted-foreground">
                                {check.detail}
                              </span>
                            </div>
                          ))}
                          {r.budget_remaining && (
                            <p className="mt-1 text-xs text-muted-foreground">
                              Budget remaining: $
                              {parseFloat(r.budget_remaining).toFixed(2)}
                            </p>
                          )}
                        </div>
                      )}

                      {r.error && (
                        <p className="mt-1 text-xs text-destructive">
                          {r.error}
                        </p>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* CTA */}
            <Card className="border-primary/20 bg-primary/5">
              <CardContent className="flex items-center justify-between py-4">
                <div>
                  <p className="font-medium">Ready for the full experience?</p>
                  <p className="text-sm text-muted-foreground">
                    Create a free account to set up your own agents with custom
                    policies.
                  </p>
                </div>
                <Link href="/auth/signin">
                  <Button>
                    Sign Up Free
                    <ArrowRight className="ml-1 h-4 w-4" />
                  </Button>
                </Link>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

function PolicyDisplay({ policy, budget }: { policy: PolicyData; budget: string }) {
  const rules: { label: string; value: string }[] = [];

  rules.push({ label: "Budget", value: `$${parseFloat(budget).toFixed(0)}` });

  if (policy.auto_approve?.enabled) {
    rules.push({
      label: "Auto-approve",
      value: `under $${policy.auto_approve.max_amount}`,
    });
  }

  if (policy.per_request_limit) {
    rules.push({
      label: "Per-request limit",
      value: `$${policy.per_request_limit}`,
    });
  }

  if (policy.daily_limit) {
    rules.push({ label: "Daily limit", value: `$${policy.daily_limit}` });
  }

  if (policy.weekly_limit) {
    rules.push({ label: "Weekly limit", value: `$${policy.weekly_limit}` });
  }

  if (policy.monthly_limit) {
    rules.push({ label: "Monthly limit", value: `$${policy.monthly_limit}` });
  }

  return (
    <div className="rounded-lg border bg-muted/30 p-4">
      <p className="mb-3 text-sm font-semibold">Active Policy</p>
      <div className="flex flex-wrap gap-2">
        {rules.map((r) => (
          <span
            key={r.label}
            className="inline-flex items-center gap-1.5 rounded-lg border border-dashed bg-muted/40 px-3 py-1.5 text-sm"
          >
            <span className="text-muted-foreground">{r.label}:</span>
            <span className="font-semibold">{r.value}</span>
          </span>
        ))}
      </div>
      {policy.categories?.allowed && (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="text-sm text-muted-foreground">Allowed:</span>
          {policy.categories.allowed.map((c) => (
            <Badge key={c} variant="secondary" className="text-xs">
              {c.replace("_", " ")}
            </Badge>
          ))}
        </div>
      )}
      {policy.categories?.blocked && (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="text-sm text-muted-foreground">Blocked:</span>
          {policy.categories.blocked.map((c) => (
            <Badge key={c} variant="destructive" className="text-xs">
              {c.replace("_", " ")}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "auto_approved":
      return <CheckCircle2 className="h-4 w-4 text-green-600" />;
    case "pending":
      return <Clock className="h-4 w-4 text-yellow-600" />;
    case "rejected":
      return <XCircle className="h-4 w-4 text-red-600" />;
    case "sending":
      return (
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      );
    case "error":
      return <XCircle className="h-4 w-4 text-destructive" />;
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
}

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case "auto_approved":
      return (
        <Badge className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
          Auto-approved
        </Badge>
      );
    case "pending":
      return (
        <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
          Pending
        </Badge>
      );
    case "rejected":
      return <Badge variant="destructive">Rejected</Badge>;
    case "sending":
      return <Badge variant="secondary">Sending...</Badge>;
    case "error":
      return <Badge variant="destructive">Error</Badge>;
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
}
