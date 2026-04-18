/**
 * Stripe + LetAgentPay governance example — policy middleware before payments.
 *
 * Architecture:
 *   Agent → LetAgentPay (policy check) → Stripe (payment execution)
 *
 * Requirements:
 *   npm install letagentpay stripe ai @ai-sdk/anthropic zod
 *
 * Usage:
 *   LETAGENTPAY_TOKEN=agt_... STRIPE_SECRET_KEY=sk_test_... ANTHROPIC_API_KEY=... npx tsx examples/stripe_governance.ts
 */

import { generateText, tool } from "ai";
import { anthropic } from "@ai-sdk/anthropic";
import { z } from "zod";
import Stripe from "stripe";
import { LetAgentPay } from "letagentpay";

const lap = new LetAgentPay(); // reads LETAGENTPAY_TOKEN from env
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || "sk_test_demo");

// --- Tool 1: Request Permission from LetAgentPay ---

const requestPurchase = tool({
  description:
    "Request approval to spend money. Use BEFORE calling executePayment.",
  parameters: z.object({
    amount: z.number().positive().describe("Amount in dollars"),
    category: z.string().describe("Spending category"),
    merchantName: z.string().describe("Merchant name"),
    description: z.string().describe("What the purchase is for"),
  }),
  execute: async ({ amount, category, merchantName, description }) => {
    const result = await lap.requestPurchase({
      amount,
      category,
      merchantName,
      description,
    });

    if (result.status === "auto_approved") {
      return {
        status: result.status,
        requestId: result.requestId,
        budgetRemaining: result.budgetRemaining,
        message: `Approved (request_id=${result.requestId}). You may now call executePayment.`,
      };
    } else if (result.status === "pending") {
      return {
        status: result.status,
        requestId: result.requestId,
        message: "Pending human review. Do NOT call executePayment.",
      };
    } else {
      const failed =
        result.policyCheck?.checks
          .filter((c) => c.result === "fail")
          .map((c) => c.detail) ?? [];
      return {
        status: result.status,
        message: "Rejected. Find a cheaper alternative.",
        reasons: failed,
      };
    }
  },
});

// --- Tool 2: Execute Payment via Stripe ---

const executePayment = tool({
  description:
    "Execute payment via Stripe. ONLY call after requestPurchase returns auto_approved.",
  parameters: z.object({
    requestId: z.string().describe("Request ID from requestPurchase"),
    amount: z.number().positive().describe("Amount in dollars"),
    description: z.string().describe("Payment description"),
    customerEmail: z.string().email().describe("Customer email for receipt"),
  }),
  execute: async ({ requestId, amount, description, customerEmail }) => {
    // Verify approval
    const status = await lap.checkRequest(requestId);
    if (status.status !== "auto_approved" && status.status !== "approved") {
      return {
        error: `Request ${requestId} is ${status.status}, not approved.`,
      };
    }

    try {
      // Create Stripe PaymentIntent
      const intent = await stripe.paymentIntents.create({
        amount: Math.round(amount * 100),
        currency: "usd",
        description,
        receipt_email: customerEmail,
        metadata: {
          letagentpay_request_id: requestId,
          agent_managed: "true",
        },
      });

      // Report success to LetAgentPay
      await lap.confirmPurchase(requestId, {
        success: true,
        actualAmount: amount,
        receiptUrl: `https://dashboard.stripe.com/payments/${intent.id}`,
      });

      return {
        status: "payment_created",
        stripePaymentId: intent.id,
        amount,
        message: `Payment of $${amount} created.`,
      };
    } catch (err) {
      // Report failure
      await lap
        .confirmPurchase(requestId, { success: false })
        .catch(() => {});
      return {
        error: `Stripe error: ${err instanceof Error ? err.message : String(err)}`,
      };
    }
  },
});

// --- Tool 3: Budget Check ---

const checkBudget = tool({
  description: "Check current budget status.",
  parameters: z.object({}),
  execute: async () => {
    const budget = await lap.checkBudget();
    return {
      budget: budget.budget,
      spent: budget.spent,
      held: budget.held,
      remaining: budget.remaining,
      currency: budget.currency,
    };
  },
});

// --- Run ---

async function main() {
  const tasks = [
    "Check my budget",
    "Pay $25 to Whole Foods for groceries, receipt to user@example.com",
    "Pay $5000 for a luxury item, receipt to user@example.com",
  ];

  for (const task of tasks) {
    console.log(`\n${"=".repeat(60)}`);
    console.log(`Task: ${task}`);
    console.log("=".repeat(60));

    const { text } = await generateText({
      model: anthropic("claude-sonnet-4-20250514"),
      system:
        "You are a payment assistant with spending governance.\n" +
        "RULES:\n" +
        "1. ALWAYS call requestPurchase FIRST before any payment.\n" +
        "2. Only call executePayment if requestPurchase returns auto_approved.\n" +
        "3. If pending, tell user to wait. If rejected, suggest alternatives.\n" +
        "4. NEVER call executePayment without a valid approved requestId.",
      prompt: task,
      tools: { requestPurchase, executePayment, checkBudget },
      maxSteps: 5,
    });

    console.log(`\nAgent: ${text}`);
  }
}

main().catch(console.error);
