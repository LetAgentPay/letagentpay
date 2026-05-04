import { describe, it, expect, vi, beforeEach } from "vitest";
import { createLetAgentPayTools } from "../src/index.js";

const mockRequestPurchase = vi.fn();
const mockCheckBudget = vi.fn();
const mockListCategories = vi.fn();
const mockMyRequests = vi.fn();
const mockConfirmPurchase = vi.fn();

vi.mock("letagentpay", () => ({
  LetAgentPay: vi.fn().mockImplementation(() => ({
    requestPurchase: mockRequestPurchase,
    checkBudget: mockCheckBudget,
    listCategories: mockListCategories,
    myRequests: mockMyRequests,
    confirmPurchase: mockConfirmPurchase,
  })),
  LetAgentPayError: class extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
}));

describe("createLetAgentPayTools", () => {
  let tools: ReturnType<typeof createLetAgentPayTools>;

  beforeEach(() => {
    vi.clearAllMocks();
    tools = createLetAgentPayTools({ token: "agt_test" });
  });

  it("returns all tool keys", () => {
    expect(Object.keys(tools).sort()).toEqual([
      "checkBudget",
      "confirmPurchase",
      "listCategories",
      "myRequests",
      "requestPurchase",
    ]);
  });

  describe("requestPurchase", () => {
    it("returns approved status", async () => {
      mockRequestPurchase.mockResolvedValue({
        requestId: "req_1",
        status: "auto_approved",
        budgetRemaining: 75.0,
        policyCheck: { passed: true, checks: [] },
      });

      const result = await tools.requestPurchase.execute(
        {
          amount: 25,
          category: "groceries",
          merchantName: "Whole Foods",
          description: "Weekly groceries",
        },
        { toolCallId: "call_1", messages: [], abortSignal: undefined as never },
      );

      expect(result.status).toBe("auto_approved");
      expect(result.budgetRemaining).toBe(75.0);
      expect(result.message).toContain("Approved");
      expect(mockRequestPurchase).toHaveBeenCalledWith({
        amount: 25,
        category: "groceries",
        merchantName: "Whole Foods",
        description: "Weekly groceries",
      });
    });

    it("returns pending status", async () => {
      mockRequestPurchase.mockResolvedValue({
        requestId: "req_2",
        status: "pending",
        budgetRemaining: 75.0,
        policyCheck: { passed: true, checks: [] },
      });

      const result = await tools.requestPurchase.execute(
        {
          amount: 100,
          category: "electronics",
          merchantName: "Amazon",
          description: "Keyboard",
        },
        { toolCallId: "call_2", messages: [], abortSignal: undefined as never },
      );

      expect(result.status).toBe("pending");
      expect(result.message).toContain("Do NOT proceed");
    });

    it("returns rejected with failed checks", async () => {
      mockRequestPurchase.mockResolvedValue({
        requestId: "req_3",
        status: "rejected",
        budgetRemaining: 0,
        policyCheck: {
          passed: false,
          checks: [
            { rule: "budget", result: "fail", detail: "Budget exceeded" },
          ],
        },
      });

      const result = await tools.requestPurchase.execute(
        {
          amount: 500,
          category: "electronics",
          merchantName: "BestBuy",
          description: "Monitor",
        },
        { toolCallId: "call_3", messages: [], abortSignal: undefined as never },
      );

      expect(result.status).toBe("rejected");
      expect(result.message).toContain("Rejected");
      expect(result.message).toContain("Budget exceeded");
    });
  });

  describe("checkBudget", () => {
    it("returns budget info", async () => {
      mockCheckBudget.mockResolvedValue({
        budget: 100,
        spent: 20,
        held: 5,
        remaining: 75,
        currency: "USD",
      });

      const result = await tools.checkBudget.execute(
        {},
        { toolCallId: "call_4", messages: [], abortSignal: undefined as never },
      );

      expect(result.budget).toBe(100);
      expect(result.remaining).toBe(75);
      expect(result.message).toContain("Budget: 100 USD");
    });
  });

  describe("listCategories", () => {
    it("returns categories", async () => {
      mockListCategories.mockResolvedValue(["groceries", "electronics"]);

      const result = await tools.listCategories.execute(
        {},
        { toolCallId: "call_5", messages: [], abortSignal: undefined as never },
      );

      expect(result.categories).toEqual(["groceries", "electronics"]);
    });
  });

  describe("myRequests", () => {
    it("returns request list", async () => {
      mockMyRequests.mockResolvedValue({
        requests: [
          {
            requestId: "req_1",
            status: "auto_approved",
            amount: 25,
            category: "groceries",
            merchant: "Whole Foods",
            description: "Groceries",
            createdAt: "2026-04-17T10:00:00Z",
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      });

      const result = await tools.myRequests.execute(
        {},
        { toolCallId: "call_6", messages: [], abortSignal: undefined as never },
      );

      expect(result.requests).toHaveLength(1);
      expect(result.total).toBe(1);
    });

    it("passes status filter", async () => {
      mockMyRequests.mockResolvedValue({
        requests: [],
        total: 0,
        limit: 20,
        offset: 0,
      });

      await tools.myRequests.execute(
        { status: "pending", limit: 5 },
        { toolCallId: "call_7", messages: [], abortSignal: undefined as never },
      );

      expect(mockMyRequests).toHaveBeenCalledWith({
        status: "pending",
        limit: 5,
      });
    });
  });

  describe("confirmPurchase", () => {
    it("confirms successful purchase", async () => {
      mockConfirmPurchase.mockResolvedValue({
        requestId: "req_1",
        status: "completed",
        actualAmount: 24.5,
      });

      const result = await tools.confirmPurchase.execute(
        {
          requestId: "req_1",
          success: true,
          actualAmount: 24.5,
        },
        { toolCallId: "call_8", messages: [], abortSignal: undefined as never },
      );

      expect(result.status).toBe("completed");
      expect(result.message).toContain("confirmed");
    });

    it("marks failed purchase", async () => {
      mockConfirmPurchase.mockResolvedValue({
        requestId: "req_2",
        status: "failed",
        actualAmount: null,
      });

      const result = await tools.confirmPurchase.execute(
        { requestId: "req_2", success: false },
        { toolCallId: "call_9", messages: [], abortSignal: undefined as never },
      );

      expect(result.status).toBe("failed");
      expect(result.message).toContain("failed");
    });
  });
});
