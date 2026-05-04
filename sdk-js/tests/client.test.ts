import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { LetAgentPay } from "../src/client.js";
import { LetAgentPayError } from "../src/errors.js";

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function jsonResponse(data: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    json: () => Promise.resolve(data),
  });
}

describe("LetAgentPay", () => {
  let client: LetAgentPay;

  beforeEach(() => {
    mockFetch.mockReset();
    client = new LetAgentPay({
      token: "agt_test_token",
      baseUrl: "https://api.example.com/api/v1/agent-api",
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("constructor", () => {
    it("requires a token", () => {
      expect(() => new LetAgentPay({})).toThrow("Token is required");
    });

    it("reads token from env", () => {
      vi.stubEnv("LETAGENTPAY_TOKEN", "agt_env_token");
      const c = new LetAgentPay();
      expect(c).toBeInstanceOf(LetAgentPay);
      vi.unstubAllEnvs();
    });

    it("reads base URL from env", () => {
      vi.stubEnv("LETAGENTPAY_BASE_URL", "https://custom.example.com/api");
      const c = new LetAgentPay({ token: "agt_test" });
      expect(c).toBeInstanceOf(LetAgentPay);
      vi.unstubAllEnvs();
    });
  });

  describe("requestPurchase", () => {
    it("creates a purchase request and parses response", async () => {
      mockFetch.mockReturnValueOnce(
        jsonResponse({
          request_id: "req-123",
          status: "auto_approved",
          currency: "USD",
          category: "software",
          original_category: null,
          policy_check: {
            passed: true,
            checks: [
              { rule: "budget", result: "pass", detail: "Within budget" },
            ],
          },
          auto_approved: true,
          budget_remaining: 475.0,
          expires_at: null,
        }),
      );

      const result = await client.requestPurchase({
        amount: 25.0,
        category: "software",
        description: "IDE license",
      });

      expect(result.requestId).toBe("req-123");
      expect(result.status).toBe("auto_approved");
      expect(result.autoApproved).toBe(true);
      expect(result.budgetRemaining).toBe(475.0);
      expect(result.policyCheck?.passed).toBe(true);
      expect(result.policyCheck?.checks).toHaveLength(1);
      expect(result.policyCheck?.checks[0].rule).toBe("budget");

      expect(mockFetch).toHaveBeenCalledWith(
        "https://api.example.com/api/v1/agent-api/requests",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            amount: 25.0,
            category: "software",
            description: "IDE license",
          }),
        }),
      );
    });

    it("sends optional fields when provided", async () => {
      mockFetch.mockReturnValueOnce(
        jsonResponse({
          request_id: "req-456",
          status: "pending",
          auto_approved: false,
          expires_at: "2026-04-07T12:00:00Z",
        }),
      );

      await client.requestPurchase({
        amount: 100,
        category: "hardware",
        merchantName: "TechShop",
        description: "Keyboard",
        agentComment: "Ergonomic model",
      });

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.merchant_name).toBe("TechShop");
      expect(body.description).toBe("Keyboard");
      expect(body.agent_comment).toBe("Ergonomic model");
    });

    it("returns pending status with expires_at", async () => {
      mockFetch.mockReturnValueOnce(
        jsonResponse({
          request_id: "req-789",
          status: "pending",
          currency: "EUR",
          category: "travel",
          auto_approved: false,
          expires_at: "2026-04-07T12:30:00Z",
        }),
      );

      const result = await client.requestPurchase({
        amount: 200,
        category: "travel",
      });

      expect(result.status).toBe("pending");
      expect(result.autoApproved).toBe(false);
      expect(result.expiresAt).toBe("2026-04-07T12:30:00Z");
    });
  });

  describe("checkRequest", () => {
    it("returns request status", async () => {
      mockFetch.mockReturnValueOnce(
        jsonResponse({
          request_id: "req-123",
          status: "approved",
          amount: 25.0,
          category: "software",
          created_at: "2026-04-07T10:00:00Z",
          reviewed_at: "2026-04-07T10:05:00Z",
        }),
      );

      const result = await client.checkRequest("req-123");

      expect(result.requestId).toBe("req-123");
      expect(result.status).toBe("approved");
      expect(result.amount).toBe(25.0);
      expect(result.reviewedAt).toBe("2026-04-07T10:05:00Z");

      expect(mockFetch).toHaveBeenCalledWith(
        "https://api.example.com/api/v1/agent-api/requests/req-123",
        expect.objectContaining({ method: "GET" }),
      );
    });
  });

  describe("confirmPurchase", () => {
    it("confirms with success", async () => {
      mockFetch.mockReturnValueOnce(
        jsonResponse({
          request_id: "req-123",
          status: "completed",
          actual_amount: 24.99,
        }),
      );

      const result = await client.confirmPurchase("req-123", {
        success: true,
        actualAmount: 24.99,
        receiptUrl: "https://example.com/receipt/123",
      });

      expect(result.requestId).toBe("req-123");
      expect(result.status).toBe("completed");
      expect(result.actualAmount).toBe(24.99);

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.success).toBe(true);
      expect(body.actual_amount).toBe(24.99);
      expect(body.receipt_url).toBe("https://example.com/receipt/123");
    });

    it("confirms with failure", async () => {
      mockFetch.mockReturnValueOnce(
        jsonResponse({
          request_id: "req-123",
          status: "failed",
          actual_amount: null,
        }),
      );

      const result = await client.confirmPurchase("req-123", {
        success: false,
      });

      expect(result.status).toBe("failed");
      expect(result.actualAmount).toBeNull();
    });
  });

  describe("checkBudget", () => {
    it("returns budget info", async () => {
      mockFetch.mockReturnValueOnce(
        jsonResponse({
          budget: 500.0,
          spent: 125.5,
          held: 25.0,
          remaining: 349.5,
          currency: "USD",
        }),
      );

      const result = await client.checkBudget();

      expect(result.budget).toBe(500.0);
      expect(result.spent).toBe(125.5);
      expect(result.held).toBe(25.0);
      expect(result.remaining).toBe(349.5);
      expect(result.currency).toBe("USD");
    });
  });

  describe("getPolicy", () => {
    it("returns raw policy object", async () => {
      const policy = {
        policy: {
          daily_limit: 100,
          per_request_limit: 50,
          allowed_categories: ["software", "groceries"],
        },
      };
      mockFetch.mockReturnValueOnce(jsonResponse(policy));

      const result = await client.getPolicy();
      expect(result.policy).toBeDefined();
    });
  });

  describe("listCategories", () => {
    it("returns list of category strings", async () => {
      mockFetch.mockReturnValueOnce(
        jsonResponse({
          categories: ["groceries", "hardware", "software", "travel"],
        }),
      );

      const result = await client.listCategories();

      expect(result).toEqual(["groceries", "hardware", "software", "travel"]);
    });
  });

  describe("myRequests", () => {
    it("returns paginated request list", async () => {
      mockFetch.mockReturnValueOnce(
        jsonResponse({
          requests: [
            {
              request_id: "req-1",
              status: "auto_approved",
              amount: 10.0,
              currency: "USD",
              category: "software",
              merchant: "GitHub",
              description: "Copilot",
              created_at: "2026-04-07T10:00:00Z",
              reviewed_at: null,
              expires_at: null,
            },
            {
              request_id: "req-2",
              status: "pending",
              amount: 50.0,
              currency: "USD",
              category: "hardware",
              merchant: null,
              description: null,
              created_at: "2026-04-07T11:00:00Z",
              reviewed_at: null,
              expires_at: "2026-04-07T11:30:00Z",
            },
          ],
          total: 15,
          limit: 2,
          offset: 0,
        }),
      );

      const result = await client.myRequests({ limit: 2 });

      expect(result.requests).toHaveLength(2);
      expect(result.total).toBe(15);
      expect(result.requests[0].requestId).toBe("req-1");
      expect(result.requests[0].merchant).toBe("GitHub");
      expect(result.requests[1].expiresAt).toBe("2026-04-07T11:30:00Z");
    });

    it("passes status filter as query param", async () => {
      mockFetch.mockReturnValueOnce(
        jsonResponse({ requests: [], total: 0, limit: 20, offset: 0 }),
      );

      await client.myRequests({ status: "pending" });

      const url = mockFetch.mock.calls[0][0] as string;
      expect(url).toContain("status=pending");
    });
  });

  describe("error handling", () => {
    it("throws LetAgentPayError on 4xx", async () => {
      mockFetch.mockReturnValueOnce(
        jsonResponse({ detail: "Agent is paused" }, 403),
      );

      await expect(
        client.requestPurchase({ amount: 10, category: "test" }),
      ).rejects.toThrow(LetAgentPayError);

      try {
        mockFetch.mockReturnValueOnce(
          jsonResponse({ detail: "Agent is paused" }, 403),
        );
        await client.requestPurchase({ amount: 10, category: "test" });
      } catch (e) {
        expect(e).toBeInstanceOf(LetAgentPayError);
        expect((e as LetAgentPayError).status).toBe(403);
        expect((e as LetAgentPayError).detail).toBe("Agent is paused");
      }
    });

    it("throws LetAgentPayError on 401", async () => {
      mockFetch.mockReturnValueOnce(
        jsonResponse({ detail: "Invalid token" }, 401),
      );

      await expect(client.checkBudget()).rejects.toThrow(LetAgentPayError);
    });

    it("throws LetAgentPayError on 429", async () => {
      mockFetch.mockReturnValueOnce(
        jsonResponse({ detail: "Rate limit exceeded" }, 429),
      );

      await expect(
        client.requestPurchase({ amount: 1, category: "test" }),
      ).rejects.toThrow(LetAgentPayError);
    });
  });
});
