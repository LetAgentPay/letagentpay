"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Code, FormInput, Plus, X } from "lucide-react";
import type { Policy } from "@/lib/types";

interface PolicyEditorProps {
  policy: Policy;
  currency: string;
  onSave: (policy: Policy) => void;
  saving?: boolean;
}

type LimitField = "per_request_limit" | "daily_limit" | "weekly_limit" | "monthly_limit";

const LIMIT_FIELDS: { key: LimitField; label: string }[] = [
  { key: "per_request_limit", label: "Per request limit" },
  { key: "daily_limit", label: "Daily limit" },
  { key: "weekly_limit", label: "Weekly limit" },
  { key: "monthly_limit", label: "Monthly limit" },
];

export function PolicyEditor({ policy, currency, onSave, saving }: PolicyEditorProps) {
  const [draft, setDraft] = useState<Policy>(policy);
  const [jsonMode, setJsonMode] = useState(false);
  const [jsonText, setJsonText] = useState(() => JSON.stringify(policy, null, 2));
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [newAllowed, setNewAllowed] = useState("");
  const [newBlocked, setNewBlocked] = useState("");

  function handleLimitChange(key: LimitField, value: string) {
    setDraft((prev) => ({
      ...prev,
      [key]: value === "" ? undefined : Number(value),
    }));
  }

  function addCategory(type: "allowed_categories" | "blocked_categories", value: string) {
    const trimmed = value.trim();
    if (!trimmed) return;
    setDraft((prev) => {
      const existing = prev[type] || [];
      if (existing.includes(trimmed)) return prev;
      return { ...prev, [type]: [...existing, trimmed] };
    });
  }

  function removeCategory(type: "allowed_categories" | "blocked_categories", value: string) {
    setDraft((prev) => {
      const filtered = (prev[type] || []).filter((c) => c !== value);
      return { ...prev, [type]: filtered.length > 0 ? filtered : undefined };
    });
  }

  function handleAutoApproveToggle() {
    setDraft((prev) => {
      if (prev.auto_approve) {
        return { ...prev, auto_approve: undefined };
      }
      return { ...prev, auto_approve: { enabled: true } };
    });
  }

  function handleAutoApproveMax(value: string) {
    setDraft((prev) => ({
      ...prev,
      auto_approve: prev.auto_approve
        ? { ...prev.auto_approve, max_amount: value === "" ? undefined : Number(value) }
        : undefined,
    }));
  }

  function handleSaveForm() {
    // Clean up empty arrays
    const cleaned = { ...draft };
    if (cleaned.allowed_categories?.length === 0) cleaned.allowed_categories = undefined;
    if (cleaned.blocked_categories?.length === 0) cleaned.blocked_categories = undefined;
    onSave(cleaned);
  }

  function handleSaveJson() {
    try {
      const parsed = JSON.parse(jsonText) as Policy;
      setJsonError(null);
      onSave(parsed);
    } catch {
      setJsonError("Invalid JSON");
    }
  }

  function switchToJson() {
    setJsonText(JSON.stringify(draft, null, 2));
    setJsonError(null);
    setJsonMode(true);
  }

  function switchToForm() {
    if (jsonText.trim()) {
      try {
        const parsed = JSON.parse(jsonText) as Policy;
        setDraft(parsed);
        setJsonError(null);
      } catch {
        // keep current draft
      }
    }
    setJsonMode(false);
  }

  return (
    <Card className="bg-muted/50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Edit Policy</CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={jsonMode ? switchToForm : switchToJson}
            className="h-7 gap-1.5 text-xs text-muted-foreground"
          >
            {jsonMode ? <FormInput className="h-3.5 w-3.5" /> : <Code className="h-3.5 w-3.5" />}
            {jsonMode ? "Form" : "JSON"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {jsonMode ? (
          <>
            <Textarea
              value={jsonText}
              onChange={(e) => {
                setJsonText(e.target.value);
                setJsonError(null);
              }}
              rows={14}
              className="font-mono text-sm"
              spellCheck={false}
            />
            {jsonError && <p className="text-sm text-destructive">{jsonError}</p>}
            <Button onClick={handleSaveJson} disabled={saving} className="w-full">
              {saving ? "Saving..." : "Save Policy"}
            </Button>
          </>
        ) : (
          <>
            {/* Limits */}
            <div className="space-y-3">
              <p className="text-sm font-medium text-muted-foreground">Spending limits ({currency})</p>
              <div className="grid grid-cols-2 gap-3">
                {LIMIT_FIELDS.map(({ key, label }) => (
                  <div key={key} className="space-y-1">
                    <Label className="text-xs">{label}</Label>
                    <Input
                      type="number"
                      min={0}
                      step="0.01"
                      placeholder="No limit"
                      value={draft[key] ?? ""}
                      onChange={(e) => handleLimitChange(key, e.target.value)}
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Categories */}
            <div className="space-y-3">
              <p className="text-sm font-medium text-muted-foreground">Categories</p>

              {/* Allowed */}
              <div className="space-y-1.5">
                <Label className="text-xs">Allowed</Label>
                <div className="flex flex-wrap gap-1">
                  {(draft.allowed_categories || []).map((c) => (
                    <Badge key={c} variant="outline" className="gap-1 text-xs">
                      {c}
                      <button onClick={() => removeCategory("allowed_categories", c)} className="hover:text-destructive">
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
                <div className="flex gap-1">
                  <Input
                    placeholder="Add category..."
                    value={newAllowed}
                    onChange={(e) => setNewAllowed(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        addCategory("allowed_categories", newAllowed);
                        setNewAllowed("");
                      }
                    }}
                    className="flex-1"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      addCategory("allowed_categories", newAllowed);
                      setNewAllowed("");
                    }}
                  >
                    <Plus className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>

              {/* Blocked */}
              <div className="space-y-1.5">
                <Label className="text-xs">Blocked</Label>
                <div className="flex flex-wrap gap-1">
                  {(draft.blocked_categories || []).map((c) => (
                    <Badge key={c} variant="destructive" className="gap-1 text-xs">
                      {c}
                      <button onClick={() => removeCategory("blocked_categories", c)} className="hover:opacity-70">
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
                <div className="flex gap-1">
                  <Input
                    placeholder="Add category..."
                    value={newBlocked}
                    onChange={(e) => setNewBlocked(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        addCategory("blocked_categories", newBlocked);
                        setNewBlocked("");
                      }
                    }}
                    className="flex-1"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      addCategory("blocked_categories", newBlocked);
                      setNewBlocked("");
                    }}
                  >
                    <Plus className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </div>

            {/* Auto-approve */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="auto-approve"
                  checked={!!draft.auto_approve?.enabled}
                  onChange={handleAutoApproveToggle}
                  className="h-4 w-4 rounded border-input"
                />
                <Label htmlFor="auto-approve" className="text-sm font-medium text-muted-foreground">
                  Auto-approve
                </Label>
              </div>
              {draft.auto_approve?.enabled && (
                <div className="ml-6 space-y-1">
                  <Label className="text-xs">Max amount ({currency})</Label>
                  <Input
                    type="number"
                    min={0}
                    step="0.01"
                    placeholder="No limit"
                    value={draft.auto_approve.max_amount ?? ""}
                    onChange={(e) => handleAutoApproveMax(e.target.value)}
                    className="w-40"
                  />
                </div>
              )}
            </div>

            <Button onClick={handleSaveForm} disabled={saving} className="w-full">
              {saving ? "Saving..." : "Save Policy"}
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}