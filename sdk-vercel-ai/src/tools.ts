import { tool } from "ai";
import { z } from "zod";
import { LetAgentPay } from "letagentpay";
import type { PurchaseResult, BudgetInfo } from "letagentpay";

function formatPolicyChecks(result: PurchaseResult): string {
  if (!result.policyCheck?.checks.length) return "";
  const failed = result.policyCheck.checks
    .filter((c) => c.result === "fail")
    .map((c) => `${c.rule}: ${c.detail}`);
  return failed.length ? ` Failed checks: ${failed.join("; ")}` : "";
}

function formatBudget(budget: BudgetInfo): string {
  const currency = budget.currency ?? "USD";
  return (
    `Budget: ${budget.budget} ${currency}, ` +
    `Spent: ${budget.spent} ${currency}, ` +
    `Held: ${budget.held} ${currency}, ` +
    `Remaining: ${budget.remaining} ${currency}`
  );
}

export function createRequestPurchaseTool(client: LetAgentPay) {
  return tool({
    description:
      "Request approval to spend money on a purchase. " +
      "Use this BEFORE making any purchase. Returns approval status and budget remaining.",
    inputSchema: z.object({
      amount: z.number().positive().describe("Amount to spend"),
      category: z
        .string()
        .describe(
          "Spending category. Use listCategories to get valid categories for this agent",
        ),
      merchantName: z
        .string()
        .describe("Name of the merchant or service provider"),
      description: z.string().describe("What the purchase is for"),
    }),
    execute: async ({ amount, category, merchantName, description }) => {
      const result = await client.requestPurchase({
        amount,
        category,
        merchantName,
        description,
      });

      return {
        requestId: result.requestId,
        status: result.status,
        budgetRemaining: result.budgetRemaining,
        message:
          result.status === "auto_approved"
            ? `Approved. Remaining budget: ${result.budgetRemaining}`
            : result.status === "pending"
              ? "Pending human review. Do NOT proceed with this purchase yet."
              : `Rejected.${formatPolicyChecks(result)}`,
      };
    },
  });
}

export function createCheckBudgetTool(client: LetAgentPay) {
  return tool({
    description:
      "Check current budget status including total budget, spent, held, and remaining amounts.",
    inputSchema: z.object({}),
    execute: async () => {
      const budget = await client.checkBudget();
      return {
        budget: budget.budget,
        spent: budget.spent,
        held: budget.held,
        remaining: budget.remaining,
        currency: budget.currency,
        message: formatBudget(budget),
      };
    },
  });
}

export function createListCategoriesTool(client: LetAgentPay) {
  return tool({
    description: "List valid spending categories for purchase requests.",
    inputSchema: z.object({}),
    execute: async () => {
      const categories = await client.listCategories();
      return { categories };
    },
  });
}

export function createMyRequestsTool(client: LetAgentPay) {
  return tool({
    description:
      "List your recent purchase requests. Optionally filter by status.",
    inputSchema: z.object({
      status: z
        .enum(["pending", "auto_approved", "approved", "rejected", "expired"])
        .optional()
        .describe("Filter by request status"),
      limit: z
        .number()
        .int()
        .positive()
        .optional()
        .describe("Max number of requests to return (default 20)"),
    }),
    execute: async ({ status, limit }) => {
      const result = await client.myRequests({ status, limit });
      return {
        requests: result.requests.map((r) => ({
          requestId: r.requestId,
          status: r.status,
          amount: r.amount,
          category: r.category,
          merchant: r.merchant,
          description: r.description,
          createdAt: r.createdAt,
        })),
        total: result.total,
      };
    },
  });
}

export function createConfirmPurchaseTool(client: LetAgentPay) {
  return tool({
    description:
      "Confirm the result of an approved purchase. " +
      "Call this AFTER completing (or failing) a purchase to close the request.",
    inputSchema: z.object({
      requestId: z.string().describe("The request ID from request_purchase"),
      success: z.boolean().describe("Whether the purchase was successful"),
      actualAmount: z
        .number()
        .optional()
        .describe("Actual amount spent (if different from requested)"),
      receiptUrl: z
        .string()
        .optional()
        .describe("URL to receipt or confirmation"),
    }),
    execute: async ({ requestId, success, actualAmount, receiptUrl }: { requestId: string; success: boolean; actualAmount?: number; receiptUrl?: string }) => {
      const result = await client.confirmPurchase(requestId, {
        success,
        actualAmount,
        receiptUrl,
      });
      return {
        requestId: result.requestId,
        status: result.status,
        message:
          result.status === "completed"
            ? "Purchase confirmed and recorded."
            : "Purchase marked as failed.",
      };
    },
  });
}
