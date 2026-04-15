import { describe, it, expect, vi, beforeEach } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer, createApiClient } from "../server.js";

function setup(apiCall, x402Call) {
  const server = createServer({ apiCall, x402Call: x402Call || vi.fn() });
  const client = new Client({ name: "test-client", version: "1.0.0" });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

  return { server, client, clientTransport, serverTransport };
}

async function connect(apiCall, x402Call) {
  const { server, client, clientTransport, serverTransport } = setup(apiCall, x402Call);
  await Promise.all([
    server.server.connect(serverTransport),
    client.connect(clientTransport),
  ]);
  return { server, client };
}

describe("MCP Server", () => {
  describe("tool registration", () => {
    it("registers all 9 tools", async () => {
      const apiCall = vi.fn();
      const { client } = await connect(apiCall);

      const { tools } = await client.listTools();
      const names = tools.map((t) => t.name).sort();

      expect(names).toEqual([
        "check_budget",
        "confirm_purchase",
        "list_categories",
        "list_requests",
        "my_requests",
        "request_purchase",
        "x402_authorize",
        "x402_budget",
        "x402_report",
      ]);
    });

    it("request_purchase has correct required params", async () => {
      const apiCall = vi.fn();
      const { client } = await connect(apiCall);

      const { tools } = await client.listTools();
      const tool = tools.find((t) => t.name === "request_purchase");

      expect(tool.inputSchema.required).toContain("amount");
      expect(tool.inputSchema.required).toContain("category");
    });

    it("confirm_purchase has correct required params", async () => {
      const apiCall = vi.fn();
      const { client } = await connect(apiCall);

      const { tools } = await client.listTools();
      const tool = tools.find((t) => t.name === "confirm_purchase");

      expect(tool.inputSchema.required).toContain("request_id");
      expect(tool.inputSchema.required).toContain("success");
    });
  });

  describe("check_budget", () => {
    it("returns formatted budget string", async () => {
      const apiCall = vi.fn().mockResolvedValue({
        budget: 100,
        spent: 25.5,
        remaining: 74.5,
      });
      const { client } = await connect(apiCall);

      const result = await client.callTool({ name: "check_budget", arguments: {} });

      expect(apiCall).toHaveBeenCalledWith("/budget");
      expect(result.content[0].text).toBe(
        "Budget: $100\nSpent: $25.5\nRemaining: $74.5",
      );
    });
  });

  describe("list_categories", () => {
    it("returns formatted category list", async () => {
      const apiCall = vi.fn().mockResolvedValue({
        categories: ["software", "hosting", "marketing"],
      });
      const { client } = await connect(apiCall);

      const result = await client.callTool({ name: "list_categories", arguments: {} });

      expect(apiCall).toHaveBeenCalledWith("/categories");
      expect(result.content[0].text).toBe(
        "Valid categories:\n- software\n- hosting\n- marketing",
      );
    });
  });

  describe("request_purchase", () => {
    it("sends correct payload and returns JSON", async () => {
      const mockResponse = { id: "req_123", status: "auto_approved" };
      const apiCall = vi.fn().mockResolvedValue(mockResponse);
      const { client } = await connect(apiCall);

      const result = await client.callTool({
        name: "request_purchase",
        arguments: {
          amount: 49.99,
          category: "software",
          merchant_name: "GitHub",
          description: "Copilot subscription",
        },
      });

      expect(apiCall).toHaveBeenCalledWith("/requests", {
        method: "POST",
        body: JSON.stringify({
          amount: 49.99,
          category: "software",
          merchant_name: "GitHub",
          description: "Copilot subscription",
        }),
      });
      expect(JSON.parse(result.content[0].text)).toEqual(mockResponse);
    });

    it("works with only required params", async () => {
      const apiCall = vi.fn().mockResolvedValue({ id: "req_456", status: "pending" });
      const { client } = await connect(apiCall);

      const result = await client.callTool({
        name: "request_purchase",
        arguments: { amount: 10, category: "other" },
      });

      expect(apiCall).toHaveBeenCalledWith("/requests", {
        method: "POST",
        body: JSON.stringify({ amount: 10, category: "other" }),
      });
      expect(JSON.parse(result.content[0].text).status).toBe("pending");
    });
  });

  describe("my_requests", () => {
    it("fetches request by ID", async () => {
      const mockRequest = { id: "req_123", status: "approved", amount: 50 };
      const apiCall = vi.fn().mockResolvedValue(mockRequest);
      const { client } = await connect(apiCall);

      const result = await client.callTool({
        name: "my_requests",
        arguments: { request_id: "req_123" },
      });

      expect(apiCall).toHaveBeenCalledWith("/requests/req_123");
      expect(JSON.parse(result.content[0].text)).toEqual(mockRequest);
    });
  });

  describe("list_requests", () => {
    it("lists requests without filters", async () => {
      const mockList = { requests: [], total: 0, limit: 20, offset: 0 };
      const apiCall = vi.fn().mockResolvedValue(mockList);
      const { client } = await connect(apiCall);

      const result = await client.callTool({
        name: "list_requests",
        arguments: {},
      });

      expect(apiCall).toHaveBeenCalledWith("/requests");
      expect(JSON.parse(result.content[0].text)).toEqual(mockList);
    });

    it("passes status filter as query param", async () => {
      const mockList = { requests: [{ id: "req_1" }], total: 1, limit: 20, offset: 0 };
      const apiCall = vi.fn().mockResolvedValue(mockList);
      const { client } = await connect(apiCall);

      await client.callTool({
        name: "list_requests",
        arguments: { status: "pending", limit: 5 },
      });

      expect(apiCall).toHaveBeenCalledWith("/requests?status=pending&limit=5");
    });
  });

  describe("confirm_purchase", () => {
    it("sends confirmation with all fields", async () => {
      const mockResponse = { id: "req_123", status: "completed" };
      const apiCall = vi.fn().mockResolvedValue(mockResponse);
      const { client } = await connect(apiCall);

      const result = await client.callTool({
        name: "confirm_purchase",
        arguments: {
          request_id: "req_123",
          success: true,
          actual_amount: 45.0,
          receipt_url: "https://example.com/receipt",
        },
      });

      expect(apiCall).toHaveBeenCalledWith("/requests/req_123/confirm", {
        method: "POST",
        body: JSON.stringify({
          success: true,
          actual_amount: 45.0,
          receipt_url: "https://example.com/receipt",
        }),
      });
      expect(JSON.parse(result.content[0].text)).toEqual(mockResponse);
    });

    it("sends failed confirmation", async () => {
      const apiCall = vi.fn().mockResolvedValue({ id: "req_123", status: "failed" });
      const { client } = await connect(apiCall);

      await client.callTool({
        name: "confirm_purchase",
        arguments: { request_id: "req_123", success: false },
      });

      expect(apiCall).toHaveBeenCalledWith("/requests/req_123/confirm", {
        method: "POST",
        body: JSON.stringify({ success: false }),
      });
    });
  });

  describe("error handling", () => {
    it("propagates API errors", async () => {
      const apiCall = vi.fn().mockRejectedValue(new Error("Insufficient budget"));
      const { client } = await connect(apiCall);

      const result = await client.callTool({ name: "check_budget", arguments: {} });

      expect(result.isError).toBe(true);
    });
  });

  describe("createApiClient", () => {
    it("sends correct headers and handles success", async () => {
      const mockData = { budget: 100 };
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      });

      const { apiCall } = createApiClient("agt_test123", "https://api.example.com/api/v1");
      const result = await apiCall("/budget");

      expect(fetch).toHaveBeenCalledWith(
        "https://api.example.com/api/v1/agent-api/budget",
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer agt_test123",
            "Content-Type": "application/json",
          }),
        }),
      );
      expect(result).toEqual(mockData);
    });

    it("x402Call uses /x402 prefix", async () => {
      const mockData = { authorized: true };
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      });

      const { x402Call } = createApiClient("agt_test123", "https://api.example.com/api/v1");
      const result = await x402Call("/authorize", { method: "POST", body: "{}" });

      expect(fetch).toHaveBeenCalledWith(
        "https://api.example.com/api/v1/x402/authorize",
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer agt_test123",
          }),
        }),
      );
      expect(result).toEqual(mockData);
    });

    it("throws on API error with detail message", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        json: () => Promise.resolve({ detail: "Token expired" }),
      });

      const { apiCall } = createApiClient("agt_bad", "https://api.example.com/api/v1");

      await expect(apiCall("/budget")).rejects.toThrow("Token expired");
    });

    it("throws generic error when no detail", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.resolve({}),
      });

      const { apiCall } = createApiClient("agt_bad", "https://api.example.com/api/v1");

      await expect(apiCall("/budget")).rejects.toThrow("API error: 500");
    });
  });

  describe("x402 tools", () => {
    it("x402_authorize sends correct payload", async () => {
      const apiCall = vi.fn();
      const x402Call = vi.fn().mockResolvedValue({
        authorized: true,
        authorization_id: "auth_123",
        expires_at: "2026-04-13T12:01:00Z",
        remaining_daily_budget: 49.95,
        remaining_monthly_budget: 499.95,
      });
      const { client } = await connect(apiCall, x402Call);

      const result = await client.callTool({
        name: "x402_authorize",
        arguments: {
          amount_usd: 0.05,
          pay_to: "0xRecipient",
          resource_url: "https://api.example.com/data",
        },
      });

      expect(x402Call).toHaveBeenCalledWith("/authorize", expect.objectContaining({
        method: "POST",
      }));
      expect(result.content[0].text).toContain("Authorized");
      expect(result.content[0].text).toContain("auth_123");
    });

    it("x402_authorize shows decline reason", async () => {
      const apiCall = vi.fn();
      const x402Call = vi.fn().mockResolvedValue({
        authorized: false,
        reason: "DAILY_BUDGET_EXCEEDED",
      });
      const { client } = await connect(apiCall, x402Call);

      const result = await client.callTool({
        name: "x402_authorize",
        arguments: { amount_usd: 100, pay_to: "0xRecipient" },
      });

      expect(result.content[0].text).toBe("Declined: DAILY_BUDGET_EXCEEDED");
    });

    it("x402_report sends tx_hash", async () => {
      const apiCall = vi.fn();
      const x402Call = vi.fn().mockResolvedValue({
        recorded: true,
        transaction_id: "txn_456",
      });
      const { client } = await connect(apiCall, x402Call);

      const result = await client.callTool({
        name: "x402_report",
        arguments: {
          authorization_id: "auth_123",
          tx_hash: "0xabc123",
        },
      });

      expect(x402Call).toHaveBeenCalledWith("/report", expect.objectContaining({
        method: "POST",
      }));
      expect(result.content[0].text).toContain("txn_456");
    });

    it("x402_budget returns formatted info", async () => {
      const apiCall = vi.fn();
      const x402Call = vi.fn().mockResolvedValue({
        budget: "1000.00",
        spent: "50.00",
        remaining: "950.00",
        x402_policy: {
          daily_spent: "10.00",
          daily_limit: "100",
          monthly_spent: "50.00",
          monthly_limit: "500",
          allowed_chains: ["base", "base-sepolia"],
        },
        wallets: [{ chain: "base", address: "0xWallet" }],
      });
      const { client } = await connect(apiCall, x402Call);

      const result = await client.callTool({
        name: "x402_budget",
        arguments: {},
      });

      expect(result.content[0].text).toContain("Budget: $1000.00");
      expect(result.content[0].text).toContain("base, base-sepolia");
      expect(result.content[0].text).toContain("0xWallet");
    });
  });
});
