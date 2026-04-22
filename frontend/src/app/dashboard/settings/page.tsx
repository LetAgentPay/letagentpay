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
import { AlertTriangle, ChevronDown, ChevronRight, Plus, Sparkles, Trash2, ArchiveRestore } from "lucide-react";
import type { AgentResponse, BudgetRule, CategoryResponse } from "@/lib/types";

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

      <CategoriesSection />

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
function CategoriesSection() {
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDisplayName, setNewDisplayName] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [newAlias, setNewAlias] = useState("");
  const [importing, setImporting] = useState(false);
  const [generating, setGenerating] = useState<string | null>(null);

  const loadCategories = useCallback(async () => {
    try {
      const data = await api.listCategories();
      setCategories(data);
    } catch {
      toast.error("Failed to load categories");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCategories();
  }, [loadCategories]);

  const handleCreate = async () => {
    const name = newName.trim().toLowerCase().replace(/\s+/g, "_").replace(/-/g, "_");
    if (!name) return;
    try {
      await api.createCategory({
        name,
        display_name: newDisplayName.trim() || undefined,
      });
      setNewName("");
      setNewDisplayName("");
      setShowForm(false);
      toast.success(`Category "${name}" created`);
      await loadCategories();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : "Failed to create category");
    }
  };

  const handleToggle = async (cat: CategoryResponse) => {
    try {
      await api.updateCategory(cat.id, { is_active: !cat.is_active });
      await loadCategories();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : "Failed to update category");
    }
  };

  const handleDelete = async (cat: CategoryResponse) => {
    try {
      await api.deleteCategory(cat.id);
      toast.success(`Category "${cat.name}" deleted`);
      await loadCategories();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : "Failed to delete category");
    }
  };

  const handleAddAlias = async (categoryId: string) => {
    const alias = newAlias.trim();
    if (!alias) return;
    try {
      await api.addCategoryAlias(categoryId, alias);
      setNewAlias("");
      await loadCategories();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : "Failed to add alias");
    }
  };

  const handleRemoveAlias = async (categoryId: string, aliasId: string) => {
    try {
      await api.removeCategoryAlias(categoryId, aliasId);
      await loadCategories();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : "Failed to remove alias");
    }
  };

  const handleImportDefaults = async () => {
    setImporting(true);
    try {
      await api.importDefaultCategories();
      toast.success("Default categories imported");
      await loadCategories();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : "Failed to import defaults");
    } finally {
      setImporting(false);
    }
  };

  const handleGenerateAliases = async (categoryId: string) => {
    setGenerating(categoryId);
    try {
      const created = await api.generateAliases(categoryId);
      if (created.length > 0) {
        toast.success(`Generated ${created.length} aliases`);
      } else {
        toast.info("No new aliases generated");
      }
      await loadCategories();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : "Failed to generate aliases");
    } finally {
      setGenerating(null);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader><CardTitle>Categories</CardTitle></CardHeader>
        <CardContent><p className="text-sm text-muted-foreground">Loading...</p></CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Categories</CardTitle>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleImportDefaults}
              disabled={importing}
            >
              {importing ? "Importing..." : "Import Defaults"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowForm(!showForm)}
            >
              <Plus className="h-4 w-4 mr-1" />
              Add
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {showForm && (
          <div className="flex gap-2 items-end">
            <div className="flex-1">
              <Label className="text-xs">Name (snake_case)</Label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="api_costs"
                className="h-8"
              />
            </div>
            <div className="flex-1">
              <Label className="text-xs">Display Name</Label>
              <Input
                value={newDisplayName}
                onChange={(e) => setNewDisplayName(e.target.value)}
                placeholder="API Costs"
                className="h-8"
              />
            </div>
            <Button size="sm" onClick={handleCreate} className="h-8">
              Create
            </Button>
          </div>
        )}

        {categories.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No categories configured. Import defaults or create custom categories.
          </p>
        )}

        {categories.map((cat) => {
          const isExpanded = expandedId === cat.id;
          return (
            <div key={cat.id} className="border rounded-lg p-3">
              <div className="flex items-center justify-between">
                <div
                  className="flex items-center gap-2 cursor-pointer flex-1"
                  onClick={() => {
                    setNewAlias("");
                    setExpandedId(isExpanded ? null : cat.id);
                  }}
                >
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}
                  <span className="font-mono text-sm">{cat.name}</span>
                  {cat.display_name && cat.display_name !== cat.name && (
                    <span className="text-sm text-muted-foreground">
                      ({cat.display_name})
                    </span>
                  )}
                  {!cat.is_active && (
                    <Badge variant="secondary" className="text-xs">
                      inactive
                    </Badge>
                  )}
                  <span className="text-xs text-muted-foreground">
                    {cat.aliases.length} aliases
                  </span>
                </div>
                <div className="flex gap-1">
                  {cat.name !== "other" && (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs"
                        onClick={() => handleToggle(cat)}
                      >
                        {cat.is_active ? "Disable" : "Enable"}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs text-destructive"
                        onClick={() => handleDelete(cat)}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </>
                  )}
                </div>
              </div>

              {isExpanded && (
                <div className="mt-3 ml-6 space-y-2">
                  <div className="flex flex-wrap gap-1">
                    {cat.aliases.map((alias) => (
                      <Badge
                        key={alias.id}
                        variant={alias.is_auto_generated ? "secondary" : "outline"}
                        className="text-xs gap-1"
                      >
                        {alias.alias}
                        <button
                          type="button"
                          className="ml-1 hover:text-destructive"
                          aria-label={`Remove alias ${alias.alias}`}
                          onClick={() => handleRemoveAlias(cat.id, alias.id)}
                        >
                          ×
                        </button>
                      </Badge>
                    ))}
                  </div>
                  <div className="flex gap-2 items-center">
                    <Input
                      value={newAlias}
                      onChange={(e) => setNewAlias(e.target.value)}
                      placeholder="Add alias..."
                      className="h-7 text-xs flex-1"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleAddAlias(cat.id);
                      }}
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => handleAddAlias(cat.id)}
                    >
                      Add
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => handleGenerateAliases(cat.id)}
                      disabled={generating === cat.id}
                    >
                      <Sparkles className="h-3 w-3 mr-1" />
                      {generating === cat.id ? "..." : "Generate"}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

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
