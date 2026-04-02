"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { AgentCard } from "@/components/agent-card";
import { RequestList } from "@/components/request-list";
import { PolicyPreview } from "@/components/policy-preview";
import { api, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { track } from "@/lib/ee-hooks";
import { useAuth } from "@/lib/auth-context";
import { useAgentEvents } from "@/lib/hooks/use-agent-events";
import type { AgentResponse } from "@/lib/types";
import { SpendingSummary } from "@/components/spending-summary";
import { Settings, Plus, Link as LinkIcon, AlertTriangle, Circle, Pause } from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const router = useRouter();
  const { account, currency, refresh } = useAuth();
  const [agents, setAgents] = useState<AgentResponse[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<AgentResponse | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [triggerEditBudget, setTriggerEditBudget] = useState(false);

  // Create agent form
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const loadingRef = useRef(false);
  const loadAgents = useCallback(async () => {
    if (loadingRef.current) return; // Deduplicate concurrent calls (SSE bursts)
    loadingRef.current = true;
    try {
      const data = await api.listAgents({ isSandbox: false });
      setAgents(data.agents);

      // Auto-select: previously selected or first agent
      const savedId = localStorage.getItem("agent_id");
      const found = data.agents.find((a) => a.id === savedId);
      if (found) {
        setSelectedAgent(found);
      } else if (data.agents.length > 0) {
        setSelectedAgent(data.agents[0]);
        localStorage.setItem("agent_id", data.agents[0].id);
      } else {
        setSelectedAgent(null);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
      loadingRef.current = false;
    }
  }, []);

  useEffect(() => {
    refresh();
    loadAgents();
  }, [loadAgents, refresh, currency]);

  useAgentEvents(selectedAgent?.id ?? null, (event) => {
    if (event.type === "budget_updated" || event.type === "request_updated" || event.type === "new_request") {
      loadAgents();
      setRefreshKey((k) => k + 1);
    }
  });

  function selectAgent(agent: AgentResponse) {
    setSelectedAgent(agent);
    localStorage.setItem("agent_id", agent.id);
    setRefreshKey((k) => k + 1);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError("");
    try {
      const data = await api.createAgent({
        name,
        description: description || undefined,
      });
      localStorage.setItem("agent_id", data.id);
      track("agent_created", { agent_id: data.id });
      setName("");
      setDescription("");
      setShowCreate(false);
      router.push(`/dashboard/agent/setup?id=${data.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to create agent");
    } finally {
      setCreating(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  // No agents yet — show create form
  if (agents.length === 0 && !showCreate) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-bold">Create Your AI Agent</h2>
        <Card>
          <CardContent className="pt-6">
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Agent Name</Label>
                <Input
                  id="name"
                  placeholder="My Shopping Agent"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="desc">Description (optional)</Label>
                <Textarea
                  id="desc"
                  placeholder="What does this agent do?"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" disabled={creating}>
                {creating ? "Creating..." : "Create Agent"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Kill switch banner */}
      {account?.all_agents_paused && (
        <div className="flex items-start gap-2 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-700 dark:bg-red-950 dark:text-red-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            <strong>All agents paused</strong> — all purchase requests are blocked.{" "}
            <Link href="/dashboard/settings" className="font-medium underline">
              Manage in Settings
            </Link>
          </span>
        </div>
      )}

      {/* Agent selector */}
      {agents.length > 0 && (
        <div>
        {agents.length > 1 && (
          <p className="text-xs text-muted-foreground mb-1.5">
            Total available: {formatMoney(agents.reduce((sum, a) => sum + Math.max(parseFloat(a.remaining || "0"), 0), 0), currency)}
          </p>
        )}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 -mb-1">
          {agents.map((a) => {
            const budgetExhausted =
              parseFloat(a.remaining || "0") <= 0 && parseFloat(a.spent) > 0;
            const noBudget =
              parseFloat(a.budget) === 0 && parseFloat(a.spent) === 0;
            const isPaused = a.status === "paused";
            const hasPending = a.pending_count > 0;
            const isSelected = selectedAgent?.id === a.id;

            return (
              <Button
                key={a.id}
                variant={isSelected ? "default" : "outline"}
                size="sm"
                className="shrink-0 gap-1.5"
                onClick={() => selectAgent(a)}
              >
                {a.name}
                {isPaused && (
                  <Pause className={`h-3 w-3 ${isSelected ? "text-primary-foreground/70" : "text-muted-foreground"}`} />
                )}
                {budgetExhausted && (
                  <Circle className={`h-2 w-2 fill-red-500 ${isSelected ? "text-red-300" : "text-red-500"}`} />
                )}
                {noBudget && !budgetExhausted && (
                  <Circle className={`h-2 w-2 fill-yellow-500 ${isSelected ? "text-yellow-300" : "text-yellow-500"}`} />
                )}
                {hasPending && (
                  <span className={`inline-flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-medium ${
                    isSelected
                      ? "bg-primary-foreground/20 text-primary-foreground"
                      : "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-200"
                  }`}>
                    {a.pending_count}
                  </span>
                )}
              </Button>
            );
          })}
          <Button
            variant="ghost"
            size="sm"
            className="shrink-0"
            onClick={() => setShowCreate(!showCreate)}
          >
            <Plus className="mr-1 h-3.5 w-3.5" />
            New Agent
          </Button>
        </div>
        </div>
      )}

      {/* Create new agent form */}
      {showCreate && (
        <Card>
          <CardContent className="pt-6">
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Agent Name</Label>
                <Input
                  id="name"
                  placeholder="My Shopping Agent"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="desc">Description (optional)</Label>
                <Textarea
                  id="desc"
                  placeholder="What does this agent do?"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <div className="flex gap-2">
                <Button type="submit" disabled={creating}>
                  {creating ? "Creating..." : "Create Agent"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowCreate(false)}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Selected agent */}
      {selectedAgent && (
        <>
          <AgentCard
            agent={selectedAgent}
            currency={currency}
            onUpdate={loadAgents}
            editBudget={triggerEditBudget}
            onEditBudgetHandled={() => setTriggerEditBudget(false)}
          />

          {parseFloat(selectedAgent.budget) === 0 && parseFloat(selectedAgent.spent) === 0 && (
            <div className="flex items-start gap-2 rounded-md border border-yellow-300 bg-yellow-50 p-3 text-sm text-yellow-800 dark:border-yellow-700 dark:bg-yellow-950 dark:text-yellow-200">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                <strong>{selectedAgent.name}</strong>: no budget set — all purchase requests will be rejected.{" "}
                <button
                  onClick={() => setTriggerEditBudget(true)}
                  className="font-medium underline"
                >
                  Top up budget
                </button>
              </span>
            </div>
          )}

          {parseFloat(selectedAgent.remaining || "0") <= 0 &&
            parseFloat(selectedAgent.spent) > 0 && (
            <div className="flex items-start gap-2 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-700 dark:bg-red-950 dark:text-red-200">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                <strong>{selectedAgent.name}</strong>: budget exhausted — new purchase requests will be rejected.{" "}
                <button
                  onClick={() => setTriggerEditBudget(true)}
                  className="font-medium underline"
                >
                  Top up budget
                </button>
              </span>
            </div>
          )}

          <SpendingSummary agentId={selectedAgent.id} currency={currency} refreshKey={refreshKey} />

          {selectedAgent.policy && (
            <div className="flex items-center justify-between">
              <PolicyPreview policy={selectedAgent.policy} currency={currency} />
            </div>
          )}

          <div className="flex items-center gap-2">
            <Link href={`/dashboard/agent/setup?id=${selectedAgent.id}`}>
              <Button variant="outline" size="sm">
                <Settings className="mr-1 h-3.5 w-3.5" />
                {selectedAgent.policy ? "Edit Policy" : "Setup Policy"}
              </Button>
            </Link>
            <Link href={`/dashboard/agent/${selectedAgent.id}/connect`}>
              <Button variant="outline" size="sm">
                <LinkIcon className="mr-1 h-3.5 w-3.5" />
                Connect
              </Button>
            </Link>
          </div>

          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Purchase Requests</h3>
            <RequestList agentId={selectedAgent.id} currency={currency} refreshKey={refreshKey} />
          </div>
        </>
      )}
    </div>
  );
}
