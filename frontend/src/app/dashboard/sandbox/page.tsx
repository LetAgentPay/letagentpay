"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { AgentCard } from "@/components/agent-card";
import { PolicyPreview } from "@/components/policy-preview";
import { RequestList } from "@/components/request-list";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { currencySymbol } from "@/lib/format";
import type { AgentResponse } from "@/lib/types";
import Link from "next/link";
import {
  Send,
  CheckCircle2,
  Clock,
  XCircle,
  ChevronDown,
  ChevronUp,
  Zap,
  Plus,
  Settings,
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

interface PolicyCheck {
  rule: string;
  result: string;
  detail: string;
}

interface SandboxResult {
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

export default function SandboxPage() {
  const { currency } = useAuth();
  const [agents, setAgents] = useState<AgentResponse[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<AgentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [results, setResults] = useState<SandboxResult[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [expandedResult, setExpandedResult] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // Custom request form
  const [customAmount, setCustomAmount] = useState("");
  const [customCategory, setCustomCategory] = useState("");
  const [customMerchant, setCustomMerchant] = useState("");
  const [customDescription, setCustomDescription] = useState("");
  const [creatingAgent, setCreatingAgent] = useState(false);

  const sym = currencySymbol(currency);

  const loadAgents = useCallback(async () => {
    try {
      const data = await api.listAgents({ isSandbox: true });
      setAgents(data.agents);
      setSelectedAgent((prev) => {
        if (prev) {
          const updated = data.agents.find((a) => a.id === prev.id);
          if (updated) return updated;
        }
        return data.agents.length > 0 ? data.agents[0] : null;
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  useEffect(() => {
    if (!selectedAgent) return;
    agentApiRequest(selectedAgent.token, "/categories")
      .then((data) => setCategories(data.categories))
      .catch(() => {});
  }, [selectedAgent]);

  function handleAgentUpdate() {
    loadAgents();
    setRefreshKey((k) => k + 1);
  }

  async function createSandboxAgent() {
    setCreatingAgent(true);
    try {
      // Find next available number
      let num = agents.length + 1;
      const existingNames = new Set(agents.map((a) => a.name));
      while (existingNames.has(`Sandbox Agent ${num}`)) num++;
      const agent = await api.createAgent({
        name: `Sandbox Agent ${num}`,
        description: "Auto-created for testing",
        is_sandbox: true,
      });
      await api.adjustBudget(agent.id, 100);
      await api.updatePolicy(agent.id, {
        auto_approve: { enabled: true, max_amount: 50 },
        daily_limit: 200,
      });
      await loadAgents();
      const refreshed = await api.getAgent(agent.id);
      setSelectedAgent(refreshed);
    } catch {
      // silent
    } finally {
      setCreatingAgent(false);
    }
  }

  async function sendRequest(data: {
    amount: string;
    category: string;
    merchant_name?: string;
    description?: string;
  }) {
    if (!selectedAgent) return;
    setSending(true);

    const resultEntry: SandboxResult = {
      id: crypto.randomUUID(),
      timestamp: new Date(),
      amount: data.amount,
      category: data.category,
      merchant: data.merchant_name || "",
      status: "sending",
    };

    setResults((prev) => [resultEntry, ...prev]);

    try {
      const resp = await agentApiRequest(selectedAgent.token, "/requests", {
        method: "POST",
        body: JSON.stringify({
          amount: data.amount,
          category: data.category,
          merchant_name: data.merchant_name || undefined,
          description: data.description || undefined,
          agent_comment: "Sent from Sandbox",
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
      handleAgentUpdate();
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
    if (!selectedAgent) return;
    const samples = SAMPLE_REQUESTS.slice(0, 5);
    for (const sample of samples) {
      await sendRequest(sample);
      await new Promise((r) => setTimeout(r, 500));
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold">Sandbox</h2>
        <Card>
          <CardContent className="py-8 text-center space-y-3">
            <p className="text-muted-foreground">
              Create a test agent to try the API. It will have a $100 budget and auto-approve purchases under $50.
            </p>
            <Button onClick={createSandboxAgent} disabled={creatingAgent}>
              <Plus className="mr-1 h-3.5 w-3.5" />
              {creatingAgent ? "Creating..." : "Create Sandbox Agent"}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Sandbox</h2>
        <Button
          variant="outline"
          size="sm"
          onClick={sendBurst}
          disabled={sending || !selectedAgent}
        >
          <Zap className="mr-1 h-3.5 w-3.5" />
          Send 5 Random
        </Button>
      </div>

      {/* Agent selector */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {agents.map((a) => (
          <Button
            key={a.id}
            variant={selectedAgent?.id === a.id ? "default" : "outline"}
            size="sm"
            className="shrink-0"
            onClick={() => {
              setSelectedAgent(a);
              setResults([]);
            }}
          >
            {a.name}
          </Button>
        ))}
        <Button
          variant="ghost"
          size="sm"
          className="shrink-0"
          onClick={createSandboxAgent}
          disabled={creatingAgent}
        >
          <Plus className="mr-1 h-3.5 w-3.5" />
          {creatingAgent ? "Creating..." : "New Agent"}
        </Button>
      </div>

      {selectedAgent && (
        <>
          {/* Full agent card — same as Home */}
          <AgentCard
            agent={selectedAgent}
            currency={currency}
            onUpdate={handleAgentUpdate}
          />

          {/* Policy + Edit Policy link */}
          <div className="flex items-start justify-between gap-4">
            {selectedAgent.policy ? (
              <PolicyPreview policy={selectedAgent.policy} currency={currency} />
            ) : (
              <p className="text-sm text-muted-foreground pt-1">No policy configured</p>
            )}
            <Link href={`/dashboard/agent/setup?id=${selectedAgent.id}&return=sandbox`} className="shrink-0">
              <Button variant="outline" size="sm">
                <Settings className="mr-1 h-3.5 w-3.5" />
                {selectedAgent.policy ? "Edit Policy" : "Setup Policy"}
              </Button>
            </Link>
          </div>

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
                    disabled={sending}
                    onClick={() => sendRequest(sample)}
                    className="text-xs"
                  >
                    <Send className="mr-1 h-3 w-3" />
                    {sym}{sample.amount} {sample.category}
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
                    <Label htmlFor="amount">Amount</Label>
                    <Input
                      id="amount"
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
                    <Label htmlFor="category">Category</Label>
                    <select
                      id="category"
                      className="flex h-9 w-full rounded-md border bg-background px-3 py-1 text-sm"
                      value={customCategory}
                      onChange={(e) => setCustomCategory(e.target.value)}
                      required
                    >
                      <option value="">Select...</option>
                      {categories.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="merchant">Merchant (optional)</Label>
                    <Input
                      id="merchant"
                      placeholder="Amazon"
                      value={customMerchant}
                      onChange={(e) => setCustomMerchant(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="desc">Description (optional)</Label>
                    <Input
                      id="desc"
                      placeholder="Monthly subscription"
                      value={customDescription}
                      onChange={(e) => setCustomDescription(e.target.value)}
                    />
                  </div>
                </div>
                <Button type="submit" disabled={sending}>
                  <Send className="mr-1 h-3.5 w-3.5" />
                  {sending ? "Sending..." : "Send Request"}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Sandbox results */}
          {results.length > 0 && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base">
                  Sandbox Results ({results.length})
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
                        setExpandedResult(expandedResult === r.id ? null : r.id)
                      }
                    >
                      <div className="flex items-center gap-2">
                        <StatusIcon status={r.status} />
                        <span className="text-sm font-medium">
                          {sym}{r.amount}
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
                            Budget remaining: {sym}
                            {parseFloat(r.budget_remaining).toFixed(2)}
                          </p>
                        )}
                      </div>
                    )}

                    {r.error && (
                      <p className="mt-1 text-xs text-destructive">{r.error}</p>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Real request list — same as Home */}
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Purchase Requests</h3>
            <RequestList
              agentId={selectedAgent.id}
              currency={currency}
              refreshKey={refreshKey}
            />
          </div>
        </>
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
