import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { api, ApiError } from "@/lib/api";
import { server } from "../../mocks/server";

const API = "/api/v1";

describe("api", () => {
  describe("request wrapper", () => {
    it("successful GET returns parsed JSON", async () => {
      const data = await api.getMe();
      expect(data.id).toBe("acc-1");
      expect(data.email).toBe("test@example.com");
    });

    it("throws ApiError on 4xx", async () => {
      server.use(
        http.get(`${API}/me`, () =>
          HttpResponse.json({ detail: "Unauthorized" }, { status: 401 }),
        ),
      );
      await expect(api.getMe()).rejects.toThrow(ApiError);
      try {
        await api.getMe();
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        expect((err as ApiError).status).toBe(401);
        expect((err as ApiError).detail).toBe("Unauthorized");
      }
    });

    it("throws ApiError on 5xx", async () => {
      server.use(
        http.get(`${API}/me`, () =>
          HttpResponse.json({ detail: "Server error" }, { status: 500 }),
        ),
      );
      await expect(api.getMe()).rejects.toThrow(ApiError);
    });

    it("ApiError falls back to statusText when no JSON body", async () => {
      server.use(
        http.get(`${API}/me`, () => new HttpResponse("not json", { status: 500 })),
      );
      try {
        await api.getMe();
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        expect((err as ApiError).detail).toBeTruthy();
      }
    });
  });

  describe("auth endpoints", () => {
    it("sendLink sends correct body", async () => {
      let body: Record<string, unknown> = {};
      server.use(
        http.post(`${API}/auth/send-link`, async ({ request }) => {
          body = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({ message: "ok" });
        }),
      );
      await api.sendLink("test@example.com");
      expect(body.email).toBe("test@example.com");
    });

    it("verify encodes token in query string", async () => {
      let url = "";
      server.use(
        http.get(`${API}/auth/verify`, ({ request }) => {
          url = request.url;
          return HttpResponse.json({ message: "ok", account_id: "1" });
        }),
      );
      await api.verify("abc+123");
      expect(url).toContain("token=abc%2B123");
    });

    it("logout sends POST", async () => {
      let method = "";
      server.use(
        http.post(`${API}/auth/logout`, ({ request }) => {
          method = request.method;
          return HttpResponse.json({ message: "ok" });
        }),
      );
      await api.logout();
      expect(method).toBe("POST");
    });
  });

  describe("agent endpoints", () => {
    it("createAgent sends name and description", async () => {
      let body: Record<string, unknown> = {};
      server.use(
        http.post(`${API}/agents`, async ({ request }) => {
          body = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({ id: "1" }, { status: 201 });
        }),
      );
      await api.createAgent({ name: "Bot", description: "My bot" });
      expect(body.name).toBe("Bot");
      expect(body.description).toBe("My bot");
    });

    it("pauseAgent sends to correct path", async () => {
      let url = "";
      server.use(
        http.post(`${API}/agents/:id/pause`, ({ request }) => {
          url = request.url;
          return HttpResponse.json({ status: "paused" });
        }),
      );
      await api.pauseAgent("agent-42");
      expect(url).toContain("/agents/agent-42/pause");
    });

    it("adjustBudget sends amount in body", async () => {
      let body: Record<string, unknown> = {};
      server.use(
        http.post(`${API}/agents/:id/budget`, async ({ request }) => {
          body = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({
            budget: "100",
            spent: "0",
            held: "0",
            remaining: "100",
          });
        }),
      );
      await api.adjustBudget("agent-1", 500);
      expect(body.amount).toBe(500);
    });
  });

  describe("request endpoints", () => {
    it("listRequests builds query string", async () => {
      let url = "";
      server.use(
        http.get(`${API}/agents/:id/requests`, ({ request }) => {
          url = request.url;
          return HttpResponse.json({
            items: [],
            total: 0,
            limit: 10,
            offset: 0,
          });
        }),
      );
      await api.listRequests("agent-1", {
        status: "pending",
        limit: 5,
        offset: 10,
      });
      expect(url).toContain("status=pending");
      expect(url).toContain("limit=5");
      expect(url).toContain("offset=10");
    });

    it("listRequests omits empty params", async () => {
      let url = "";
      server.use(
        http.get(`${API}/agents/:id/requests`, ({ request }) => {
          url = request.url;
          return HttpResponse.json({
            items: [],
            total: 0,
            limit: 10,
            offset: 0,
          });
        }),
      );
      await api.listRequests("agent-1");
      expect(url).not.toContain("?");
    });

    it("approveRequest sends to correct path", async () => {
      let url = "";
      server.use(
        http.post(`${API}/requests/:id/approve`, ({ request }) => {
          url = request.url;
          return HttpResponse.json({ request_id: "r1", status: "approved" });
        }),
      );
      await api.approveRequest("req-55");
      expect(url).toContain("/requests/req-55/approve");
    });
  });

  describe("budget rule endpoints", () => {
    it("listBudgetRules fetches rules", async () => {
      const rules = await api.listBudgetRules();
      expect(Array.isArray(rules)).toBe(true);
      expect(rules[0].name).toBe("Daily Limit");
    });

    it("createBudgetRule sends correct body", async () => {
      let body: Record<string, unknown> = {};
      server.use(
        http.post(`${API}/me/budget/rules`, async ({ request }) => {
          body = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({ id: "rule-1" }, { status: 201 });
        }),
      );
      await api.createBudgetRule({
        name: "Weekly",
        limit_type: "weekly",
        limit_amount: 500,
        priority: 1,
        days_of_week: [0, 1, 2],
      });
      expect(body.name).toBe("Weekly");
      expect(body.limit_type).toBe("weekly");
      expect(body.limit_amount).toBe(500);
      expect(body.priority).toBe(1);
      expect(body.days_of_week).toEqual([0, 1, 2]);
    });

    it("updateBudgetRule sends PUT with correct body", async () => {
      let body: Record<string, unknown> = {};
      let url = "";
      server.use(
        http.put(`${API}/me/budget/rules/:id`, async ({ request }) => {
          url = request.url;
          body = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({ id: "rule-1" });
        }),
      );
      await api.updateBudgetRule("rule-42", { is_active: false, name: "Updated" });
      expect(url).toContain("/me/budget/rules/rule-42");
      expect(body.is_active).toBe(false);
      expect(body.name).toBe("Updated");
    });

    it("deleteBudgetRule sends DELETE", async () => {
      let method = "";
      let url = "";
      server.use(
        http.delete(`${API}/me/budget/rules/:id`, ({ request }) => {
          method = request.method;
          url = request.url;
          return HttpResponse.json(null, { status: 200 });
        }),
      );
      await api.deleteBudgetRule("rule-99");
      expect(method).toBe("DELETE");
      expect(url).toContain("/me/budget/rules/rule-99");
    });

    it("getAccountBudget returns budget data", async () => {
      const data = await api.getAccountBudget();
      expect(data.account_spent).toBe("500.00");
      expect(data.currency).toBe("USD");
    });
  });

  describe("password auth", () => {
    it("passwordLogin sends password in body", async () => {
      let body: Record<string, unknown> = {};
      server.use(
        http.post("/auth/login", async ({ request }) => {
          body = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({ message: "ok" });
        }),
      );
      await api.passwordLogin("secret123");
      expect(body.password).toBe("secret123");
    });
  });

  describe("push notification endpoints", () => {
    it("getVapidKey returns key", async () => {
      const data = await api.getVapidKey();
      expect(data.vapid_public_key).toBe("test-vapid-key");
    });

    it("pushSubscribe sends subscription data", async () => {
      let body: Record<string, unknown> = {};
      server.use(
        http.post(`${API}/push/subscribe`, async ({ request }) => {
          body = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({ message: "ok" });
        }),
      );
      await api.pushSubscribe({
        endpoint: "https://push.example.com",
        p256dh: "key1",
        auth: "auth1",
      });
      expect(body.endpoint).toBe("https://push.example.com");
      expect(body.p256dh).toBe("key1");
    });
  });

  describe("policy endpoints", () => {
    it("aiPolicyPreview sends message and chat_history", async () => {
      let body: Record<string, unknown> = {};
      server.use(
        http.post(`${API}/agents/:id/policy/ai`, async ({ request }) => {
          body = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({
            policy_preview: {},
            explanation: "ok",
            session_id: "s1",
          });
        }),
      );
      await api.aiPolicyPreview("a1", "set limit", [
        { role: "user", content: "hi" },
      ]);
      expect(body.message).toBe("set limit");
      expect(body.chat_history).toEqual([{ role: "user", content: "hi" }]);
    });

    it("confirmAiPolicy sends POST", async () => {
      let method = "";
      server.use(
        http.post(`${API}/agents/:id/policy/ai/confirm`, ({ request }) => {
          method = request.method;
          return HttpResponse.json({ message: "ok", policy: {} });
        }),
      );
      await api.confirmAiPolicy("a1");
      expect(method).toBe("POST");
    });
  });
});
