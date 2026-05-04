import { LetAgentPay } from "./client.js";
import { LetAgentPayError } from "./errors.js";
import type { LetAgentPayConfig } from "./types.js";

/** Options for the guard wrapper. */
export interface GuardOptions extends LetAgentPayConfig {
  /** Existing client instance. Takes priority over token/baseUrl. */
  client?: LetAgentPay;
  /** Purchase category for the request. */
  category?: string;
  /** Fixed amount per call. If not set, must be passed to the guarded function. */
  amount?: number;
  /** Purchase description. */
  description?: string;
  /** Optional comment explaining the purchase. */
  agentComment?: string;
}

/**
 * Wrap an async function so it checks spending policy before executing.
 *
 * @example
 * ```ts
 * const guardedBuy = guard(
 *   async (item: string, amount: number) => {
 *     return `Bought ${item} for $${amount}`;
 *   },
 *   { token: "agt_...", category: "groceries" }
 * );
 *
 * // amount is extracted from the last numeric argument
 * await guardedBuy("apples", 9.99);
 * ```
 */
export function guard<TArgs extends unknown[], TReturn>(
  fn: (...args: TArgs) => TReturn | Promise<TReturn>,
  options: GuardOptions & { amount?: number },
): (...args: TArgs) => Promise<TReturn> {
  return async (...args: TArgs): Promise<TReturn> => {
    let resolvedAmount = options.amount;
    if (resolvedAmount == null) {
      // Try to find a numeric argument (first one)
      for (const arg of args) {
        if (typeof arg === "number") {
          resolvedAmount = arg;
          break;
        }
      }
    }

    if (resolvedAmount == null) {
      throw new Error(
        "guard: could not determine amount from arguments. " +
          "Pass amount in guard options or as a numeric function argument.",
      );
    }

    const client = options.client ?? new LetAgentPay(options);

    const result = await client.requestPurchase({
      amount: resolvedAmount,
      category: options.category ?? "other",
      description:
        options.description ?? `Auto-guarded call to ${fn.name || "anonymous"}`,
      agentComment: options.agentComment,
    });

    if (result.status === "auto_approved" || result.status === "pending") {
      if (result.status === "pending") {
        throw new LetAgentPayError(
          403,
          `Purchase request pending approval: ${result.requestId}`,
        );
      }
      return fn(...args);
    }

    throw new LetAgentPayError(
      403,
      `Purchase request ${result.status}: ${result.requestId}`,
    );
  };
}
