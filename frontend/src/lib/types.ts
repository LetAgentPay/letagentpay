export interface AccountResponse {
  id: string;
  email: string;
  name: string | null;
  currency: string;
  timezone: string;
  plan: string;
  plan_price?: string;
  billing_period?: string;
  is_admin: boolean;
  blocked: boolean;
  all_agents_paused: boolean;
  request_expiry_minutes: number;
  created_at: string;
}

export interface AutoReplenishResponse {
  enabled: boolean;
  threshold: string | null;
  amount: string | null;
  max_budget: string | null;
}

// --- Policy types ---

export interface PolicyScheduleOverride {
  days: string[];
  deny?: boolean;
  allow?: string;
  daily_limit?: number;
}

export interface PolicySchedule {
  timezone?: string;
  default?: { allow?: string };
  overrides?: PolicyScheduleOverride[];
}

export interface AutoApproveConfig {
  enabled: boolean;
  max_amount?: number;
  categories?: string[];
}

export interface Policy {
  per_request_limit?: number;
  daily_limit?: number;
  weekly_limit?: number;
  monthly_limit?: number;
  allowed_categories?: string[];
  blocked_categories?: string[];
  schedule?: PolicySchedule;
  auto_approve?: AutoApproveConfig;
}

export interface AgentResponse {
  id: string;
  name: string;
  description: string | null;
  status: string;
  is_sandbox: boolean;
  budget: string; // Decimal comes as string
  spent: string;
  held: string;
  remaining: string;
  pending_count: number;
  policy: Policy | null;
  policy_text: string | null;
  token: string;
  auto_replenish: AutoReplenishResponse | null;
  created_at: string;
}

export interface PurchaseRequestItem {
  id: string;
  agent_id: string;
  agent_name: string | null;
  amount: string;
  currency: string | null;
  category: string;
  original_category: string | null;
  merchant: string | null;
  description: string | null;
  agent_comment: string | null;
  status: string;
  rejection_reason: string | null;
  actual_amount: string | null;
  receipt_url: string | null;
  settlement_method: string | null;
  settlement_currency: string | null;
  tx_hash: string | null;
  completed_at: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface PaginatedRequests {
  items: PurchaseRequestItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface PolicyAIResponse {
  policy_preview: Policy;
  explanation: string;
  session_id: string;
}

export interface BudgetResponse {
  budget: string;
  spent: string;
  held: string;
  remaining: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  policy_preview?: Policy;
}

// --- Budget Rules ---

export interface BudgetRule {
  id: string;
  name: string;
  is_active: boolean;
  priority: number;
  limit_type: "daily" | "weekly" | "monthly" | "total";
  limit_amount: string;
  days_of_week: number[] | null;
  start_at: string | null;
  end_at: string | null;
  created_at: string;
  spent: string | null;
}

// --- Categories ---

export interface CategoryAlias {
  id: string;
  alias: string;
  is_auto_generated: boolean;
  created_at: string;
}

export interface CategoryResponse {
  id: string;
  name: string;
  display_name: string | null;
  is_active: boolean;
  aliases: CategoryAlias[];
  created_at: string;
}

// --- Notification Channels ---

export interface NotificationChannelResponse {
  channel_type: string;
  is_enabled: boolean;
  priority: number;
  verified: boolean;
  config: Record<string, string>;
}

export interface TelegramLinkResponse {
  link_url: string;
  expires_in: number;
}

export interface AccountBudgetResponse {
  account_spent: string;
  currency: string;
  daily_spent: string;
  weekly_spent: string;
  monthly_spent: string;
  rules: BudgetRule[];
}
