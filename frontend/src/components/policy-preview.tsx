"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatMoney } from "@/lib/format";
import type { Policy } from "@/lib/types";

interface PolicyPreviewProps {
  policy: Policy;
  currency: string;
}

export function PolicyPreview({ policy, currency }: PolicyPreviewProps) {
  const { schedule, auto_approve: autoApprove } = policy;
  const { allowed_categories: allowedCategories, blocked_categories: blockedCategories } = policy;

  const hasRules =
    policy.per_request_limit != null ||
    policy.daily_limit != null ||
    policy.weekly_limit != null ||
    policy.monthly_limit != null ||
    policy.requests_per_minute != null ||
    policy.requests_per_hour != null ||
    (allowedCategories && allowedCategories.length > 0) ||
    (blockedCategories && blockedCategories.length > 0) ||
    schedule != null ||
    autoApprove != null;

  return (
    <Card className="bg-muted/50">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Policy Preview</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-base">
        {!hasRules && (
          <p className="text-muted-foreground">No rules configured</p>
        )}
        {policy.per_request_limit != null && (
          <div>
            <span className="text-muted-foreground">Per request limit:</span>{" "}
            {formatMoney(policy.per_request_limit, currency)}
          </div>
        )}
        {policy.daily_limit != null && (
          <div>
            <span className="text-muted-foreground">Daily limit:</span>{" "}
            {formatMoney(policy.daily_limit, currency)}
          </div>
        )}
        {policy.weekly_limit != null && (
          <div>
            <span className="text-muted-foreground">Weekly limit:</span>{" "}
            {formatMoney(policy.weekly_limit, currency)}
          </div>
        )}
        {policy.monthly_limit != null && (
          <div>
            <span className="text-muted-foreground">Monthly limit:</span>{" "}
            {formatMoney(policy.monthly_limit, currency)}
          </div>
        )}
        {policy.requests_per_minute != null && (
          <div>
            <span className="text-muted-foreground">Requests per minute:</span>{" "}
            {policy.requests_per_minute}
          </div>
        )}
        {policy.requests_per_hour != null && (
          <div>
            <span className="text-muted-foreground">Requests per hour:</span>{" "}
            {policy.requests_per_hour}
          </div>
        )}

        {allowedCategories && allowedCategories.length > 0 && (
          <div>
            <span className="text-muted-foreground">Allowed:</span>{" "}
            <span className="flex flex-wrap gap-1 mt-1">
              {allowedCategories.map((c) => (
                <Badge key={c} variant="outline" className="text-xs">
                  {c}
                </Badge>
              ))}
            </span>
          </div>
        )}

        {blockedCategories && blockedCategories.length > 0 && (
          <div>
            <span className="text-muted-foreground">Blocked:</span>{" "}
            <span className="flex flex-wrap gap-1 mt-1">
              {blockedCategories.map((c) => (
                <Badge key={c} variant="destructive" className="text-xs">
                  {c}
                </Badge>
              ))}
            </span>
          </div>
        )}

        {schedule && (
          <div className="space-y-1">
            <div>
              <span className="text-muted-foreground">Schedule:</span>{" "}
              {schedule.default?.allow || "all day"}{" "}
              ({schedule.timezone || "account default"})
            </div>
            {schedule.overrides?.map((override, i) => (
              <div key={i} className="ml-2 text-xs text-muted-foreground">
                {override.days.join(", ")}:{" "}
                {override.deny
                  ? "denied"
                  : override.allow || "allowed"}
              </div>
            ))}
          </div>
        )}

        {autoApprove != null && (
          <div>
            <span className="text-muted-foreground">Auto-approve:</span>{" "}
            {autoApprove.enabled ? "Yes" : "No"}
            {autoApprove.max_amount != null &&
              ` (up to ${formatMoney(autoApprove.max_amount, currency)})`}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
