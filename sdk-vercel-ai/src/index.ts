import { LetAgentPay } from "letagentpay";
import type { LetAgentPayConfig } from "letagentpay";
import {
  createRequestPurchaseTool,
  createCheckBudgetTool,
  createListCategoriesTool,
  createMyRequestsTool,
  createConfirmPurchaseTool,
} from "./tools.js";

export interface CreateToolsOptions extends LetAgentPayConfig {}

/**
 * Create all LetAgentPay tools for use with the Vercel AI SDK.
 *
 * @example
 * ```ts
 * import { generateText } from 'ai';
 * import { anthropic } from '@ai-sdk/anthropic';
 * import { createLetAgentPayTools } from '@letagentpay/ai';
 *
 * const tools = createLetAgentPayTools({ token: 'agt_...' });
 *
 * const { text } = await generateText({
 *   model: anthropic('claude-sonnet-4-20250514'),
 *   prompt: 'Buy the cheapest weather API plan',
 *   tools,
 * });
 * ```
 */
export function createLetAgentPayTools(options: CreateToolsOptions = {}) {
  const client = new LetAgentPay(options);

  return {
    requestPurchase: createRequestPurchaseTool(client),
    checkBudget: createCheckBudgetTool(client),
    listCategories: createListCategoriesTool(client),
    myRequests: createMyRequestsTool(client),
    confirmPurchase: createConfirmPurchaseTool(client),
  };
}

export {
  createRequestPurchaseTool,
  createCheckBudgetTool,
  createListCategoriesTool,
  createMyRequestsTool,
  createConfirmPurchaseTool,
} from "./tools.js";
