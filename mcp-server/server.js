import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

export function createApiClient(token, apiUrl) {
  return async function apiCall(path, options = {}) {
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
  };
}

export function createServer(apiCall) {
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

  return server;
}
