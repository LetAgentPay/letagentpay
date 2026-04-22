"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { BudgetBar } from "@/components/budget-bar";
import type { AgentResponse } from "@/lib/types";
import { api } from "@/lib/api";
import { formatMoney, currencySymbol } from "@/lib/format";
import { Pause, Play, Pencil, Copy, Plus, Minus, RefreshCw, ChevronDown, ChevronUp, Archive } from "lucide-react";
import { toast } from "sonner";

interface AgentCardProps {
  agent: AgentResponse;
  currency: string;
  onUpdate: () => void;
  editBudget?: boolean;
  onEditBudgetHandled?: () => void;
}

export function AgentCard({ agent, currency, onUpdate, editBudget, onEditBudgetHandled }: AgentCardProps) {
  const [newToken, setNewToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [editingBudget, setEditingBudget] = useState(false);
  const [budgetInput, setBudgetInput] = useState("");
  const [isWithdraw, setIsWithdraw] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [nameInput, setNameInput] = useState(agent.name);

  useEffect(() => {
    setNameInput(agent.name);
    setEditingName(false);
  }, [agent.id, agent.name]);
  const [showAutoReplenish, setShowAutoReplenish] = useState(false);
  const [arThreshold, setArThreshold] = useState("");
  const [arAmount, setArAmount] = useState("");
  const [arMaxBudget, setArMaxBudget] = useState("");

  const spent = parseFloat(agent.spent);
  const budget = parseFloat(agent.budget);
  const held = parseFloat(agent.held || "0");
  const remaining = parseFloat(agent.remaining || "0");

  const sym = currencySymbol(currency);

  useEffect(() => {
    if (editBudget) {
      setBudgetInput("");
      setIsWithdraw(false);
      setEditingBudget(true);
      onEditBudgetHandled?.();
    }
  }, [editBudget, onEditBudgetHandled]);

  useEffect(() => {
    if (agent.auto_replenish) {
      setArThreshold(agent.auto_replenish.threshold || "");
      setArAmount(agent.auto_replenish.amount || "");
      setArMaxBudget(agent.auto_replenish.max_budget || "");
    }
  }, [agent.auto_replenish]);

  async function toggleStatus() {
    setLoading(true);
    try {
      if (agent.status === "active") {
        await api.pauseAgent(agent.id);
      } else {
        await api.resumeAgent(agent.id);
      }
      onUpdate();
    } finally {
      setLoading(false);
    }
  }

  async function handleNameSave() {
    const trimmed = nameInput.trim();
    if (!trimmed || trimmed === agent.name) {
      setEditingName(false);
      setNameInput(agent.name);
      return;
    }
    setLoading(true);
    try {
      await api.updateAgent(agent.id, { name: trimmed });
      onUpdate();
      setEditingName(false);
    } catch {
      toast.error("Failed to rename agent");
    } finally {
      setLoading(false);
    }
  }

  async function handleArchive() {
    if (!confirm("Archive this agent? It will stop accepting requests.")) return;
    setLoading(true);
    try {
      await api.archiveAgent(agent.id);
      toast.success("Agent archived");
      onUpdate();
    } finally {
      setLoading(false);
    }
  }

  async function handleBudgetSubmit(e: React.FormEvent) {
    e.preventDefault();
    const value = parseFloat(budgetInput);
    if (isNaN(value) || value <= 0) return;
    const amount = isWithdraw ? -value : value;
    setLoading(true);
    try {
      await api.adjustBudget(agent.id, amount);
      setEditingBudget(false);
      onUpdate();
      toast.success(
        isWithdraw
          ? `Budget reduced by ${formatMoney(value, currency)}`
          : `Budget topped up by ${formatMoney(value, currency)}`,
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to adjust budget";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }

  async function handleAutoReplenishSave() {
    const threshold = parseFloat(arThreshold);
    const amount = parseFloat(arAmount);
    const maxBudget = arMaxBudget ? parseFloat(arMaxBudget) : undefined;
    if (isNaN(threshold) || threshold <= 0 || isNaN(amount) || amount <= 0) {
      toast.error("Threshold and amount must be positive numbers");
      return;
    }
    setLoading(true);
    try {
      await api.setAutoReplenish(agent.id, { threshold, amount, max_budget: maxBudget });
      onUpdate();
      toast.success("Auto top-up configured");
    } catch {
      toast.error("Failed to save auto top-up settings");
    } finally {
      setLoading(false);
    }
  }

  async function handleAutoReplenishDisable() {
    setLoading(true);
    try {
      await api.disableAutoReplenish(agent.id);
      setArThreshold("");
      setArAmount("");
      setArMaxBudget("");
      onUpdate();
      toast.success("Auto top-up disabled");
    } catch {
      toast.error("Failed to disable auto top-up");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-1 mr-2 min-w-0">
          {editingName ? (
            <Input
              className="h-7 text-lg font-semibold px-1"
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              onBlur={handleNameSave}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleNameSave();
                if (e.key === "Escape") {
                  setEditingName(false);
                  setNameInput(agent.name);
                }
              }}
              autoFocus
            />
          ) : (
            <>
              <CardTitle className="text-lg truncate">{agent.name}</CardTitle>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 shrink-0"
                onClick={() => setEditingName(true)}
              >
                <Pencil className="h-3 w-3" />
              </Button>
            </>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {agent.auto_replenish && (
            <Badge variant="outline" className="border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-950 dark:text-blue-300 text-[10px] px-1.5">
              <RefreshCw className="h-2.5 w-2.5 mr-0.5" />
              auto
            </Badge>
          )}
          <Badge
            variant={agent.status === "active" ? "outline" : "secondary"}
            className={agent.status === "active" ? "border-green-300 bg-green-50 text-green-700 dark:border-green-700 dark:bg-green-950 dark:text-green-300" : ""}
          >
            {agent.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {agent.description && (
          <p className="text-sm text-muted-foreground">{agent.description}</p>
        )}

        {editingBudget ? (
          <form onSubmit={handleBudgetSubmit} className="space-y-2">
            <div className="flex items-center gap-2">
              <Button
                type="button"
                size="icon"
                variant={isWithdraw ? "default" : "outline"}
                className="h-8 w-8 shrink-0"
                onClick={() => setIsWithdraw(!isWithdraw)}
                title={isWithdraw ? "Withdraw mode" : "Top up mode"}
              >
                {isWithdraw ? <Minus className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
              </Button>
              <span className="text-sm text-muted-foreground">{sym}</span>
              <Input
                type="number"
                min="0.01"
                step="0.01"
                placeholder="100.00"
                value={budgetInput}
                onChange={(e) => setBudgetInput(e.target.value)}
                className="w-32"
                autoFocus
              />
              <Button size="sm" type="submit" disabled={loading}>
                {isWithdraw ? "Withdraw" : "Top up"}
              </Button>
              <Button size="sm" variant="ghost" type="button" onClick={() => setEditingBudget(false)}>
                Cancel
              </Button>
            </div>
            {isWithdraw && (
              <p className="text-xs text-muted-foreground">
                Available: {formatMoney(remaining, currency)}
              </p>
            )}
          </form>
        ) : (
          <div
            className="group cursor-pointer"
            onClick={() => {
              setBudgetInput("");
              setIsWithdraw(false);
              setEditingBudget(true);
            }}
          >
            <BudgetBar spent={spent} budget={budget} held={held} currency={currency} />
            <p className={`mt-1 text-xs text-muted-foreground transition-opacity ${budget === 0 ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`}>
              <Pencil className="inline h-3 w-3 mr-1" />Click to {budget > 0 ? "top up" : "add"} budget
            </p>
          </div>
        )}

        {/* Auto top-up settings */}
        <div>
          <button
            onClick={() => setShowAutoReplenish(!showAutoReplenish)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <RefreshCw className="h-3 w-3" />
            Auto top-up
            {showAutoReplenish ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
          {showAutoReplenish && (
            <div className="mt-2 space-y-2 rounded-md border p-3 text-sm">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs text-muted-foreground">When below {sym}</label>
                  <Input
                    type="number"
                    min="0.01"
                    step="0.01"
                    placeholder="10.00"
                    value={arThreshold}
                    onChange={(e) => setArThreshold(e.target.value)}
                    className="h-8 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Add {sym}</label>
                  <Input
                    type="number"
                    min="0.01"
                    step="0.01"
                    placeholder="50.00"
                    value={arAmount}
                    onChange={(e) => setArAmount(e.target.value)}
                    className="h-8 text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Max total budget {sym} (optional)</label>
                <Input
                  type="number"
                  min="0.01"
                  step="0.01"
                  placeholder="500.00"
                  value={arMaxBudget}
                  onChange={(e) => setArMaxBudget(e.target.value)}
                  className="h-8 text-sm"
                />
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="default" onClick={handleAutoReplenishSave} disabled={loading}>
                  Save
                </Button>
                {agent.auto_replenish && (
                  <Button size="sm" variant="outline" onClick={handleAutoReplenishDisable} disabled={loading}>
                    Disable
                  </Button>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Token:</span>
            <code
              className={`flex-1 truncate rounded bg-muted px-2 py-1 text-xs ${newToken ? "cursor-pointer hover:bg-muted/70 transition-colors" : ""}`}
              onClick={() => {
                if (newToken) {
                  navigator.clipboard.writeText(newToken);
                  toast.success("Token copied to clipboard");
                }
              }}
              title={newToken ? "Click to copy" : undefined}
            >
              {newToken || agent.token}
            </code>
            {newToken && (
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => {
                  navigator.clipboard.writeText(newToken);
                  toast.success("Token copied to clipboard");
                }}
              >
                <Copy className="h-3.5 w-3.5" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              title="Regenerate token"
              disabled={loading}
              onClick={async () => {
                if (!confirm("Regenerate token? The current token will stop working immediately.")) return;
                setLoading(true);
                try {
                  const updated = await api.regenerateToken(agent.id);
                  setNewToken(updated.token);
                  toast.success("Token regenerated — copy it now, it won't be shown again");
                  onUpdate();
                } catch {
                  toast.error("Failed to regenerate token");
                } finally {
                  setLoading(false);
                }
              }}
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          </div>
          {newToken && (
            <p className="text-xs text-amber-600">
              Copy this token now — it won&apos;t be shown again.
            </p>
          )}
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={toggleStatus}
            disabled={loading}
          >
            {agent.status === "active" ? (
              <>
                <Pause className="mr-1 h-3.5 w-3.5" /> Pause
              </>
            ) : (
              <>
                <Play className="mr-1 h-3.5 w-3.5" /> Resume
              </>
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleArchive}
            disabled={loading}
            className="text-muted-foreground hover:text-destructive hover:border-destructive"
          >
            <Archive className="mr-1 h-3.5 w-3.5" /> Archive
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
