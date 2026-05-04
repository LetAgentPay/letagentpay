import type {
  AccountBudgetResponse,
  AccountResponse,
  AgentResponse,
  AutoReplenishResponse,
  BudgetResponse,
  BudgetRule,
  CategoryAlias,
  CategoryResponse,
  NotificationChannelResponse,
  PaginatedRequests,
  Policy,
  PolicyAIResponse,
  TelegramLinkResponse,
} from "./types";
import type { Attribution } from "./attribution";
import { eeApi } from "./api-ee";

// In dev, requests are proxied via Next.js rewrites (next.config.ts) to avoid
// cross-origin cookie issues. In production behind a reverse proxy both
// frontend and API share the same origin, so this just works.
const API_URL = "/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }

  return res.json();
}

export const api = {
  // Public config
  publicConfig: () =>
    request<{ playground_enabled: boolean }>("/config/public"),

  // Auth
  authMode: () => request<{ mode: "magic_link" | "password" }>("/auth/mode"),

  sendLink: (email: string, attribution?: Attribution | null) =>
    request<{ message: string }>("/auth/send-link", {
      method: "POST",
      body: JSON.stringify(
        attribution ? { email, attribution } : { email },
      ),
    }),

  passwordLogin: async (password: string) => {
    // Call the Next.js Route Handler directly (not through /api/v1 rewrite)
    // because the rewrite proxy doesn't forward Set-Cookie headers.
    const res = await fetch("/auth/login", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(res.status, body.detail || res.statusText);
    }
    return res.json() as Promise<{ message: string }>;
  },

  verify: (token: string) =>
    request<{ message: string; account_id: string }>(
      `/auth/verify?token=${encodeURIComponent(token)}`,
    ),

  verifyOtp: async (email: string, code: string) => {
    // Call the Next.js Route Handler directly (not through /api/v1 rewrite)
    // because the rewrite proxy doesn't forward Set-Cookie headers.
    const res = await fetch("/auth/verify-otp", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, code }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(res.status, body.detail || res.statusText);
    }
    return res.json() as Promise<{ message: string }>;
  },

  logout: () => request<{ message: string }>("/auth/logout", { method: "POST" }),

  // Account
  getMe: () => request<AccountResponse>("/me"),

  updateMe: (data: { name?: string; currency?: string; timezone?: string; request_expiry_minutes?: number }) =>
    request<AccountResponse>("/me", {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  toggleKillSwitch: (paused: boolean) =>
    request<{ all_agents_paused: boolean }>("/me/kill-switch", {
      method: "POST",
      body: JSON.stringify({ paused }),
    }),

  // Agents
  listAgents: (opts?: { includeArchived?: boolean; isSandbox?: boolean }) => {
    const params = new URLSearchParams();
    if (opts?.includeArchived) params.set("include_archived", "true");
    if (opts?.isSandbox !== undefined) params.set("is_sandbox", String(opts.isSandbox));
    const qs = params.toString();
    return request<{ agents: AgentResponse[] }>(`/agents${qs ? `?${qs}` : ""}`);
  },

  createAgent: (data: { name: string; description?: string; is_sandbox?: boolean }) =>
    request<AgentResponse>("/agents", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getAgent: (agentId: string) => request<AgentResponse>(`/agents/${agentId}`),

  updateAgent: (agentId: string, data: { name?: string; description?: string }) =>
    request<AgentResponse>(`/agents/${agentId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  regenerateToken: (agentId: string) =>
    request<AgentResponse>(`/agents/${agentId}/regenerate-token`, { method: "POST" }),

  pauseAgent: (agentId: string) =>
    request<{ status: string }>(`/agents/${agentId}/pause`, { method: "POST" }),

  resumeAgent: (agentId: string) =>
    request<{ status: string }>(`/agents/${agentId}/resume`, { method: "POST" }),

  archiveAgent: (agentId: string) =>
    request<{ status: string }>(`/agents/${agentId}/archive`, { method: "POST" }),

  restoreAgent: (agentId: string) =>
    request<{ status: string }>(`/agents/${agentId}/restore`, { method: "POST" }),

  adjustBudget: (agentId: string, amount: number) =>
    request<BudgetResponse>(`/agents/${agentId}/budget`, {
      method: "POST",
      body: JSON.stringify({ amount }),
    }),

  setAutoReplenish: (
    agentId: string,
    data: { threshold: number; amount: number; max_budget?: number },
  ) =>
    request<AutoReplenishResponse>(`/agents/${agentId}/auto-replenish`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  disableAutoReplenish: (agentId: string) =>
    request<void>(`/agents/${agentId}/auto-replenish`, { method: "DELETE" }),

  // Policy
  getPolicy: (agentId: string) =>
    request<{ policy: Policy; policy_text: string | null }>(
      `/agents/${agentId}/policy`,
    ),

  aiPolicyPreview: (
    agentId: string,
    message: string,
    chatHistory?: { role: string; content: string }[],
  ) =>
    request<PolicyAIResponse>(`/agents/${agentId}/policy/ai`, {
      method: "POST",
      body: JSON.stringify({ message, chat_history: chatHistory }),
    }),

  confirmAiPolicy: (agentId: string) =>
    request<{ message: string; policy: Policy }>(
      `/agents/${agentId}/policy/ai/confirm`,
      { method: "POST" },
    ),

  updatePolicy: (agentId: string, policy: Record<string, unknown>) =>
    request<{ message: string; policy: Policy }>(
      `/agents/${agentId}/policy`,
      { method: "PUT", body: JSON.stringify(policy) },
    ),

  // Purchase Requests
  listRequests: (
    agentId: string,
    params?: { status?: string; limit?: number; offset?: number },
  ) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    const query = qs.toString();
    return request<PaginatedRequests>(
      `/agents/${agentId}/requests${query ? `?${query}` : ""}`,
    );
  },

  approveRequest: (requestId: string) =>
    request<{ request_id: string; status: string }>(
      `/requests/${requestId}/approve`,
      { method: "POST" },
    ),

  rejectRequest: (requestId: string) =>
    request<{ request_id: string; status: string }>(
      `/requests/${requestId}/reject`,
      { method: "POST" },
    ),

  // Stats
  getSpendingStats: (agentId: string) =>
    request<{ spent_today: string; spent_week: string; spent_month: string }>(
      `/stats/${agentId}/spending`,
    ),

  getX402Stats: (agentId: string) =>
    request<{
      total_transactions: number;
      total_volume_usd: string;
      settled_count: number;
      top_domains: { domain: string; count: number; volume_usd: string }[];
    }>(`/agents/${agentId}/x402-stats`),

  // Budget Rules
  getAccountBudget: () => request<AccountBudgetResponse>("/me/budget"),

  listBudgetRules: () => request<BudgetRule[]>("/me/budget/rules"),

  createBudgetRule: (data: {
    name: string;
    limit_type: string;
    limit_amount: number;
    priority?: number;
    days_of_week?: number[];
    start_at?: string;
    end_at?: string;
  }) =>
    request<BudgetRule>("/me/budget/rules", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateBudgetRule: (
    ruleId: string,
    data: {
      name?: string;
      limit_amount?: number;
      priority?: number;
      is_active?: boolean;
      days_of_week?: number[];
      start_at?: string;
      end_at?: string;
    },
  ) =>
    request<BudgetRule>(`/me/budget/rules/${ruleId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteBudgetRule: (ruleId: string) =>
    request<void>(`/me/budget/rules/${ruleId}`, { method: "DELETE" }),

  // Categories
  listCategories: () => request<CategoryResponse[]>("/me/categories"),

  createCategory: (data: { name: string; display_name?: string }) =>
    request<CategoryResponse>("/me/categories", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateCategory: (
    categoryId: string,
    data: { display_name?: string; is_active?: boolean },
  ) =>
    request<CategoryResponse>(`/me/categories/${categoryId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteCategory: (categoryId: string) =>
    request<void>(`/me/categories/${categoryId}`, { method: "DELETE" }),

  addCategoryAlias: (categoryId: string, alias: string) =>
    request<CategoryAlias>(`/me/categories/${categoryId}/aliases`, {
      method: "POST",
      body: JSON.stringify({ alias }),
    }),

  removeCategoryAlias: (categoryId: string, aliasId: string) =>
    request<void>(`/me/categories/${categoryId}/aliases/${aliasId}`, {
      method: "DELETE",
    }),

  importDefaultCategories: () =>
    request<CategoryResponse[]>("/me/categories/import-defaults", {
      method: "POST",
    }),

  generateAliases: (categoryId: string) =>
    request<CategoryAlias[]>(`/me/categories/${categoryId}/generate-aliases`, {
      method: "POST",
    }),

  // Push notifications
  getVapidKey: () => request<{ vapid_public_key: string }>("/push/vapid-key"),

  pushSubscribe: (subscription: { endpoint: string; p256dh: string; auth: string }) =>
    request<{ message: string }>("/push/subscribe", {
      method: "POST",
      body: JSON.stringify(subscription),
    }),

  // Notification channels
  listNotificationChannels: () =>
    request<NotificationChannelResponse[]>("/me/notifications/channels"),

  updateNotificationChannel: (channelType: string, data: { is_enabled?: boolean; priority?: number }) =>
    request<NotificationChannelResponse>(`/me/notifications/channels/${channelType}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  disconnectNotificationChannel: (channelType: string) =>
    request<{ message: string }>(`/me/notifications/channels/${channelType}`, {
      method: "DELETE",
    }),

  createTelegramLink: () =>
    request<TelegramLinkResponse>("/me/notifications/channels/telegram/link", {
      method: "POST",
    }),

  enableEmailChannel: () =>
    request<NotificationChannelResponse>("/me/notifications/channels/email/enable", {
      method: "POST",
    }),

  // Enterprise extensions (admin, billing) — injected via api-ee.ts overlay
  ...eeApi,
};
