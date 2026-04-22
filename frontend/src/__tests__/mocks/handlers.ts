import { http, HttpResponse } from "msw";
import {
  mockAccount,
  mockAgent,
  mockBudgetRule,
  mockPaginatedRequests,
} from "./fixtures";

const API = "/api/v1";

export const handlers = [
  // Auth
  http.get(`${API}/auth/mode`, () =>
    HttpResponse.json({ mode: "magic_link" }),
  ),

  http.post(`${API}/auth/send-link`, () =>
    HttpResponse.json({ message: "Magic link sent to your email" }),
  ),

  http.get(`${API}/auth/verify`, () =>
    HttpResponse.json({ message: "Authenticated", account_id: "acc-1" }),
  ),

  http.post("/auth/verify-otp", () =>
    HttpResponse.json({ message: "Authenticated" }),
  ),

  http.post(`${API}/auth/logout`, () =>
    HttpResponse.json({ message: "Logged out" }),
  ),

  // Account
  http.get(`${API}/me`, () => HttpResponse.json(mockAccount())),

  http.put(`${API}/me`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...mockAccount(), ...body });
  }),

  // Kill switch
  http.post(`${API}/me/kill-switch`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ all_agents_paused: body.paused });
  }),

  // Agents
  http.get(`${API}/agents`, () =>
    HttpResponse.json({ agents: [mockAgent()] }),
  ),

  http.post(`${API}/agents`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      mockAgent({ name: body.name as string, policy: null, token: "agt_new_token_shown_once" }),
      { status: 201 },
    );
  }),

  http.get(`${API}/agents/:id`, () => HttpResponse.json(mockAgent())),

  http.post(`${API}/agents/:id/pause`, () =>
    HttpResponse.json({ status: "paused" }),
  ),

  http.post(`${API}/agents/:id/resume`, () =>
    HttpResponse.json({ status: "active" }),
  ),

  http.post(`${API}/agents/:id/budget`, () =>
    HttpResponse.json({ budget: "15000.00", spent: "2500.00", held: "0.00", remaining: "12500.00" }),
  ),

  http.put(`${API}/agents/:id/auto-replenish`, () =>
    HttpResponse.json({ enabled: true, threshold: "10.00", amount: "50.00", max_budget: null }),
  ),

  http.delete(`${API}/agents/:id/auto-replenish`, () =>
    HttpResponse.json({ message: "Auto-replenish disabled" }),
  ),

  // Policy
  http.get(`${API}/agents/:id/policy`, () =>
    HttpResponse.json({
      policy: { daily_limit: 5000 },
      policy_text: "Daily limit 5000",
    }),
  ),

  http.post(`${API}/agents/:id/policy/ai`, () =>
    HttpResponse.json({
      policy_preview: { daily_limit: 1000, allowed_categories: ["groceries"] },
      explanation: "Daily limit of 1000, groceries only",
      session_id: "session-1",
    }),
  ),

  http.post(`${API}/agents/:id/policy/ai/confirm`, () =>
    HttpResponse.json({
      message: "Policy confirmed",
      policy: { daily_limit: 1000 },
    }),
  ),

  // Stats
  http.get(`${API}/stats/:id/spending`, () =>
    HttpResponse.json({
      spent_today: "150.00",
      spent_week: "800.00",
      spent_month: "2500.00",
    }),
  ),

  // Purchase Requests
  http.get(`${API}/agents/:id/requests`, () =>
    HttpResponse.json(mockPaginatedRequests()),
  ),

  http.post(`${API}/requests/:id/approve`, ({ params }) =>
    HttpResponse.json({
      request_id: params.id,
      status: "approved",
      budget_remaining: "7500.00",
    }),
  ),

  http.post(`${API}/requests/:id/reject`, ({ params }) =>
    HttpResponse.json({
      request_id: params.id,
      status: "rejected",
    }),
  ),

  // Budget Rules
  http.get(`${API}/me/budget/rules`, () =>
    HttpResponse.json([mockBudgetRule()]),
  ),

  http.post(`${API}/me/budget/rules`, () =>
    HttpResponse.json(mockBudgetRule(), { status: 201 }),
  ),

  http.put(`${API}/me/budget/rules/:id`, () =>
    HttpResponse.json(mockBudgetRule({ is_active: false })),
  ),

  http.delete(`${API}/me/budget/rules/:id`, () =>
    HttpResponse.json(null, { status: 200 }),
  ),

  // Account Budget
  http.get(`${API}/me/budget`, () =>
    HttpResponse.json({
      account_spent: "500.00",
      currency: "USD",
      daily_spent: "50.00",
      weekly_spent: "200.00",
      monthly_spent: "500.00",
      rules: [mockBudgetRule()],
    }),
  ),

  // Password login (Route Handler at /auth/login, not through /api/v1 rewrite)
  http.post("/auth/login", () =>
    HttpResponse.json({ message: "Authenticated" }),
  ),

  // Push notifications
  http.get(`${API}/push/vapid-key`, () =>
    HttpResponse.json({ vapid_public_key: "test-vapid-key" }),
  ),

  http.post(`${API}/push/subscribe`, () =>
    HttpResponse.json({ message: "Subscribed" }),
  ),

  // Billing (enterprise EESettingsSection calls getPricing on mount)
  http.get(`${API}/billing/pricing`, () =>
    HttpResponse.json({ pro_price: 0, pro_yearly_price: 0 }),
  ),
];
