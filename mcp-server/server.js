import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

export function createApiClient(token, apiUrl) {
  async function apiCall(path, options = {}) {
    const res = await fetch(`${apiUrl}/agent-api${path}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || `API error: ${res.status}`);
    }
    return data;
  }

  async function x402Call(path, options = {}) {
    const res = await fetch(`${apiUrl}/x402${path}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || `API error: ${res.status}`);
    }
    return data;
  }

  return { apiCall, x402Call };
}

export function createServer({ apiCall, x402Call }) {
  const server = new McpServer({
    name: "letagentpay",
    version: "0.1.0",
  });

  server.tool(
    "request_purchase",
    "Request approval for a purchase. Returns request ID and status (auto_approved, pending, or rejected).",
    {
      amount: z.number().positive().describe("Purchase amount in account currency"),
      category: z.string().describe("Purchase category (use list_categories to see valid options)"),
      merchant_name: z.string().optional().describe("Merchant or store name"),
      description: z.string().optional().describe("What is being purchased"),
      agent_comment: z.string().optional().describe("Why this purchase is needed — shown to the human reviewer"),
    },
    async ({ amount, category, merchant_name, description, agent_comment }) => {
      const result = await apiCall("/requests", {
        method: "POST",
        body: JSON.stringify({ amount, category, merchant_name, description, agent_comment }),
      });
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    },
  );

  server.tool(
    "check_budget",
    "Check the current budget, amount spent, and remaining balance.",
    {},
    async () => {
      const result = await apiCall("/budget");
      return {
        content: [
          {
            type: "text",
            text: `Budget: $${result.budget}\nSpent: $${result.spent}\nRemaining: $${result.remaining}`,
          },
        ],
      };
    },
  );

  server.tool(
    "list_categories",
    "List all valid purchase categories.",
    {},
    async () => {
      const result = await apiCall("/categories");
      return {
        content: [
          {
            type: "text",
            text: `Valid categories:\n${result.categories.map((c) => `- ${c}`).join("\n")}`,
          },
        ],
      };
    },
  );

  server.tool(
    "my_requests",
    "Get the status of a specific purchase request by ID.",
    {
      request_id: z.string().describe("The purchase request ID"),
    },
    async ({ request_id }) => {
      const result = await apiCall(`/requests/${request_id}`);
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    },
  );

  server.tool(
    "list_requests",
    "List agent's purchase requests with optional status filter.",
    {
      status: z.string().optional().describe("Filter by status: pending, auto_approved, approved, rejected, expired, completed, failed"),
      limit: z.number().optional().describe("Max results to return (default 20, max 100)"),
      offset: z.number().optional().describe("Offset for pagination (default 0)"),
    },
    async ({ status, limit, offset }) => {
      const params = new URLSearchParams();
      if (status) params.set("status", status);
      if (limit != null) params.set("limit", String(limit));
      if (offset != null) params.set("offset", String(offset));
      const query = params.toString();
      const result = await apiCall(`/requests${query ? `?${query}` : ""}`);
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    },
  );

  server.tool(
    "confirm_purchase",
    "Confirm that a purchase was completed (or failed). Call after an approved request.",
    {
      request_id: z.string().describe("The purchase request ID"),
      success: z.boolean().describe("Whether the purchase was successful"),
      actual_amount: z.number().optional().describe("Actual amount if different from requested"),
      receipt_url: z.string().optional().describe("URL to receipt or confirmation"),
    },
    async ({ request_id, success, actual_amount, receipt_url }) => {
      const result = await apiCall(`/requests/${request_id}/confirm`, {
        method: "POST",
        body: JSON.stringify({ success, actual_amount, receipt_url }),
      });
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    },
  );

  // --- x402 tools ---

  server.tool(
    "x402_authorize",
    "Request authorization for an x402 crypto-micropayment. Call this when you receive HTTP 402 from a resource. Returns authorized/declined with reason.",
    {
      amount_usd: z.number().positive().describe("Payment amount in USD"),
      asset: z.string().optional().describe("Asset symbol (default: USDC)"),
      network: z.string().optional().describe("CAIP-2 network ID (default: eip155:84532 for Base Sepolia)"),
      pay_to: z.string().describe("Recipient wallet address"),
      resource_url: z.string().optional().describe("URL of the resource being paid for"),
      category: z.string().optional().describe("Purchase category (e.g. api, data, compute). Default: api"),
    },
    async ({ amount_usd, asset, network, pay_to, resource_url, category }) => {
      const result = await x402Call("/authorize", {
        method: "POST",
        body: JSON.stringify({
          payment_requirements: {
            scheme: "exact",
            network: network || "eip155:84532",
            amount: String(Math.round(amount_usd * 1_000_000)),
            asset: asset || "USDC",
            pay_to,
            resource: resource_url,
          },
          max_amount_usd: amount_usd,
          category: category || "api",
        }),
      });

      if (result.authorized) {
        return {
          content: [{
            type: "text",
            text: `Authorized. ID: ${result.authorization_id}\nExpires: ${result.expires_at}\nDaily remaining: $${result.remaining_daily_budget ?? "unlimited"}\nMonthly remaining: $${result.remaining_monthly_budget ?? "unlimited"}`,
          }],
        };
      }
      return {
        content: [{
          type: "text",
          text: `Declined: ${result.reason}`,
        }],
      };
    },
  );

  server.tool(
    "x402_report",
    "Report a completed x402 transaction. Call after the on-chain payment is settled.",
    {
      authorization_id: z.string().describe("Authorization ID from x402_authorize"),
      tx_hash: z.string().describe("On-chain transaction hash"),
      actual_amount_usd: z.number().optional().describe("Actual amount paid in USD"),
    },
    async ({ authorization_id, tx_hash, actual_amount_usd }) => {
      const body = { authorization_id, tx_hash };
      if (actual_amount_usd != null) body.actual_amount_usd = actual_amount_usd;
      const result = await x402Call("/report", {
        method: "POST",
        body: JSON.stringify(body),
      });
      return {
        content: [{
          type: "text",
          text: `Recorded. Transaction ID: ${result.transaction_id}`,
        }],
      };
    },
  );

  server.tool(
    "x402_budget",
    "Check x402 payment budget, spending limits, allowed chains, and registered wallets.",
    {},
    async () => {
      const result = await x402Call("/budget");
      const p = result.x402_policy || {};
      const wallets = (result.wallets || []).map((w) => `${w.chain}: ${w.address}`).join("\n  ");
      return {
        content: [{
          type: "text",
          text: [
            `Budget: $${result.budget}  Spent: $${result.spent}  Remaining: $${result.remaining}`,
            `Daily: $${p.daily_spent || 0} / $${p.daily_limit || "unlimited"}`,
            `Monthly: $${p.monthly_spent || 0} / $${p.monthly_limit || "unlimited"}`,
            `Chains: ${(p.allowed_chains || []).join(", ")}`,
            wallets ? `Wallets:\n  ${wallets}` : "No wallets registered",
          ].join("\n"),
        }],
      };
    },
  );

  return server;
}
