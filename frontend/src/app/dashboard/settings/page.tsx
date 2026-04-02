"use client";

import { useCallback, useEffect, useState } from "react";
import { Suspense } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/lib/auth-context";
import { api, ApiError } from "@/lib/api";
import { EESettingsSection } from "@/lib/ee-hooks";
import { NotificationSettings } from "@/components/notification-settings";
import { formatMoney } from "@/lib/format";
import { toast } from "sonner";
import { AlertTriangle, Plus, Trash2, ArchiveRestore } from "lucide-react";
import type { AgentResponse, BudgetRule } from "@/lib/types";

const CURRENCIES = [
  "USD", "EUR", "GBP", "JPY", "CNY", "KRW", "INR", "BRL", "RUB", "TRY",
  "AUD", "CAD", "CHF", "SEK", "NOK", "DKK", "PLN", "CZK", "HUF", "RON",
  "BGN", "HRK", "MXN", "ARS", "CLP", "COP", "PEN", "UYU", "ZAR", "EGP",
  "AED", "SAR", "ILS", "THB", "SGD", "HKD", "TWD", "NZD", "PHP", "IDR",
  "MYR", "VND", "NGN", "KES", "GHS", "UAH", "KZT", "GEL", "AMD",
];

const TIMEZONES = Intl.supportedValuesOf("timeZone");

function SettingsContent() {
  const { account, logout, refresh } = useAuth();
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("");
  const [timezone, setTimezone] = useState("");
  const [expiryMinutes, setExpiryMinutes] = useState(30);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (account) {
      setName(account.name || "");
      setCurrency(account.currency);
      setTimezone(account.timezone);
      setExpiryMinutes(account.request_expiry_minutes);
    }
  }, [account]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await api.updateMe({
        name: name || undefined,
        currency: currency || undefined,
        timezone: timezone || undefined,
        request_expiry_minutes: expiryMinutes,
      });
      await refresh();
      toast.success("Settings saved");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  if (!account) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold">Settings</h2>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Profile</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-4">
            <div className="space-y-2">
              <Label>Email</Label>
              <Input value={account.email} disabled />
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="currency">Currency</Label>
              <select
                id="currency"
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                {CURRENCIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="tz">Timezone</Label>
              <select
                id="tz"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                {TIMEZONES.map((tz) => (
                  <option key={tz} value={tz}>{tz}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="expiry">Pending request timeout (minutes)</Label>
              <Input
                id="expiry"
                type="number"
                min={5}
                max={1440}
                value={expiryMinutes}
                onChange={(e) => {
                  const v = parseInt(e.target.value);
                  if (!isNaN(v)) setExpiryMinutes(v);
                }}
              />
              <p className="text-xs text-muted-foreground">
                Pending requests expire after this time (5–1440 min). Held funds are released on expiry.
              </p>
            </div>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <EESettingsSection account={account} refresh={refresh} />

      <KillSwitchSection paused={account.all_agents_paused} refresh={refresh} />

      <ArchivedAgentsSection />

      <NotificationSettings />

      <BudgetRulesSection currency={account.currency} />

      <Separator />

      <Button variant="destructive" onClick={logout}>
        Log out
      </Button>
    </div>
  );
}

function ArchivedAgentsSection() {
  const [agents, setAgents] = useState<AgentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [restoring, setRestoring] = useState<string | null>(null);

  const loadArchived = useCallback(async () => {
    try {
      const all = await api.listAgents({ includeArchived: true });
      setAgents(all.agents.filter((a) => a.status === "archived"));
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadArchived();
  }, [loadArchived]);

  async function handleRestore(agentId: string) {
    setRestoring(agentId);
    try {
      await api.restoreAgent(agentId);
      toast.success("Agent restored");
      await loadArchived();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Failed to restore");
    } finally {
      setRestoring(null);
    }
  }

  if (loading || agents.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Archived Agents</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="flex items-center justify-between rounded-lg border p-3"
          >
            <div className="space-y-0.5">
              <span className="text-sm font-medium">{agent.name}</span>
              {agent.description && (
                <p className="text-xs text-muted-foreground">{agent.description}</p>
              )}
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleRestore(agent.id)}
              disabled={restoring === agent.id}
            >
              <ArchiveRestore className="mr-1 h-3.5 w-3.5" />
              {restoring === agent.id ? "Restoring..." : "Restore"}
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function KillSwitchSection({ paused, refresh }: { paused: boolean; refresh: () => Promise<void> }) {
  const [toggling, setToggling] = useState(false);

  async function handleToggle() {
    setToggling(true);
    try {
      await api.toggleKillSwitch(!paused);
      await refresh();
      toast.success(paused ? "All agents resumed" : "All agents paused");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Failed to toggle kill switch");
    } finally {
      setToggling(false);
    }
  }

  return (
    <Card className={paused ? "border-destructive" : undefined}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <AlertTriangle className={`h-4 w-4 ${paused ? "text-destructive" : "text-muted-foreground"}`} />
          Pause All Agents
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Immediately block all purchase requests from all your agents.
          Individual agent states are preserved — when you resume, each agent returns to its previous state.
        </p>
        <div className="flex items-center gap-3">
          <Button
            variant={paused ? "default" : "destructive"}
            onClick={handleToggle}
            disabled={toggling}
          >
            {toggling ? "..." : paused ? "Resume All Agents" : "Pause All Agents"}
          </Button>
          {paused && (
            <Badge variant="destructive">All agents paused</Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

const LIMIT_TYPES = ["daily", "weekly", "monthly", "total"] as const;
const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function BudgetRulesSection({ currency }: { currency: string }) {
  const [rules, setRules] = useState<BudgetRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState<string>("daily");
  const [newAmount, setNewAmount] = useState("");
  const [newPriority, setNewPriority] = useState("0");
  const [newDays, setNewDays] = useState<number[]>([]);
  const [creating, setCreating] = useState(false);

  const loadRules = useCallback(async () => {
    try {
      const data = await api.listBudgetRules();
      setRules(data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await api.createBudgetRule({
        name: newName,
        limit_type: newType,
        limit_amount: parseFloat(newAmount),
        priority: parseInt(newPriority) || 0,
        days_of_week: newDays.length > 0 ? newDays : undefined,
      });
      toast.success("Budget rule created");
      setShowForm(false);
      setNewName("");
      setNewAmount("");
      setNewPriority("0");
      setNewDays([]);
      await loadRules();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Failed to create rule");
    } finally {
      setCreating(false);
    }
  }

  async function handleToggle(rule: BudgetRule) {
    try {
      await api.updateBudgetRule(rule.id, { is_active: !rule.is_active });
      await loadRules();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Failed to update rule");
    }
  }

  async function handleDelete(ruleId: string) {
    try {
      await api.deleteBudgetRule(ruleId);
      toast.success("Rule deleted");
      await loadRules();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Failed to delete rule");
    }
  }

  function toggleDay(day: number) {
    setNewDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day].sort(),
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Account Budget Rules</CardTitle>
        <Button size="sm" variant="outline" onClick={() => setShowForm(!showForm)}>
          <Plus className="mr-1 h-3.5 w-3.5" />
          Add Rule
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {showForm && (
          <form onSubmit={handleCreate} className="space-y-3 rounded-lg border p-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="rule-name">Name</Label>
                <Input
                  id="rule-name"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Weekday limit"
                  required
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="rule-type">Type</Label>
                <select
                  id="rule-type"
                  className="flex h-9 w-full rounded-md border bg-background px-3 py-1 text-sm"
                  value={newType}
                  onChange={(e) => setNewType(e.target.value)}
                >
                  {LIMIT_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <Label htmlFor="rule-amount">Limit Amount</Label>
                <Input
                  id="rule-amount"
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={newAmount}
                  onChange={(e) => setNewAmount(e.target.value)}
                  placeholder="200.00"
                  required
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="rule-priority">Priority</Label>
                <Input
                  id="rule-priority"
                  type="number"
                  min="0"
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value)}
                  placeholder="0"
                />
              </div>
            </div>
            <div className="space-y-1">
              <Label>Days of week (optional)</Label>
              <div className="flex gap-1">
                {DAY_NAMES.map((name, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => toggleDay(i)}
                    className={`rounded px-2 py-1 text-xs font-medium ${
                      newDays.includes(i)
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {name}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <Button type="submit" size="sm" disabled={creating}>
                {creating ? "Creating..." : "Create"}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => setShowForm(false)}
              >
                Cancel
              </Button>
            </div>
          </form>
        )}

        {loading ? (
          <div className="py-4 text-center text-sm text-muted-foreground">
            Loading...
          </div>
        ) : rules.length === 0 ? (
          <p className="py-4 text-center text-sm text-muted-foreground">
            No budget rules yet. Account-level rules limit spending across all your
            agents.
          </p>
        ) : (
          <div className="space-y-2">
            {rules.map((rule) => (
              <div
                key={rule.id}
                className="flex items-center justify-between rounded-lg border p-3"
              >
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{rule.name}</span>
                    <Badge variant={rule.is_active ? "default" : "secondary"}>
                      {rule.is_active ? "active" : "disabled"}
                    </Badge>
                    <Badge variant="outline">{rule.limit_type}</Badge>
                    {rule.priority > 0 && (
                      <Badge variant="outline">p{rule.priority}</Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Limit: {formatMoney(parseFloat(rule.limit_amount), currency)}
                    {rule.days_of_week &&
                      ` | Days: ${rule.days_of_week.map((d) => DAY_NAMES[d]).join(", ")}`}
                    {rule.spent !== null && ` | Spent: ${formatMoney(parseFloat(rule.spent), currency)}`}
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleToggle(rule)}
                  >
                    {rule.is_active ? "Disable" : "Enable"}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDelete(rule.id)}
                  >
                    <Trash2 className="h-3.5 w-3.5 text-destructive" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      }
    >
      <SettingsContent />
    </Suspense>
  );
}
