import type {
  AccountResponse,
  AgentResponse,
  PurchaseRequestItem,
  PaginatedRequests,
  ChatMessage,
  BudgetRule,
} from "@/lib/types";

export function mockAccount(
  overrides?: Partial<AccountResponse>,
): AccountResponse {
  return {
    id: "acc-1",
    email: "test@example.com",
    name: "Test User",
    currency: "USD",
    timezone: "America/New_York",
    plan: "free",
    is_admin: false,
    blocked: false,
    all_agents_paused: false,
    request_expiry_minutes: 30,
    created_at: "2026-01-01T00:00:00",
    ...overrides,
  };
}

export function mockAgent(overrides?: Partial<AgentResponse>): AgentResponse {
  return {
    id: "agent-1",
    name: "Test Agent",
    description: "A test agent",
    status: "active",
    budget: "10000.00",
    spent: "2500.00",
    held: "0.00",
    remaining: "7500.00",
    pending_count: 0,
    policy: {
      daily_limit: 5000,
      per_request_limit: 2000,
      allowed_categories: ["groceries", "food_delivery"],
    },
    policy_text: "Groceries and food delivery",
    token: "agt_test_token_abc123",
    auto_replenish: null,
    created_at: "2026-01-01T00:00:00",
    ...overrides,
  };
}

export function mockRequest(
  overrides?: Partial<PurchaseRequestItem>,
): PurchaseRequestItem {
  return {
    id: "req-1",
    agent_id: "agent-1",
    agent_name: "Test Agent",
    amount: "42.50",
    currency: "USD",
    category: "groceries",
    original_category: null,
    merchant: "Test Store",
    description: "Weekly groceries",
    agent_comment: null,
    status: "pending",
    rejection_reason: null,
    actual_amount: null,
    receipt_url: null,
    completed_at: null,
    created_at: "2026-01-15T12:00:00",
    reviewed_at: null,
    ...overrides,
  };
}

export function mockBudgetRule(
  overrides?: Partial<BudgetRule>,
): BudgetRule {
  return {
    id: "rule-1",
    name: "Daily Limit",
    is_active: true,
    priority: 0,
    limit_type: "daily",
    limit_amount: "200.00",
    days_of_week: null,
    start_at: null,
    end_at: null,
    created_at: "2026-01-01T00:00:00",
    spent: "50.00",
    ...overrides,
  };
}

export function mockPaginatedRequests(
  items?: PurchaseRequestItem[],
  overrides?: Partial<PaginatedRequests>,
): PaginatedRequests {
  return {
    items: items ?? [mockRequest()],
    total: items?.length ?? 1,
    limit: 10,
    offset: 0,
    ...overrides,
  };
}

export function mockChatMessage(
  overrides?: Partial<ChatMessage>,
): ChatMessage {
  return {
    role: "assistant",
    content: "Hello, how can I help?",
    ...overrides,
  };
}
