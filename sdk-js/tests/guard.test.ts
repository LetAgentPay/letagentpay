import { describe, it, expect, vi, afterEach } from "vitest";
import { guard } from "../src/guard.js";
import { LetAgentPayError } from "../src/errors.js";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function jsonResponse(data: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    statusText: "OK",
    json: () => Promise.resolve(data),
  });
}

describe("guard", () => {
  afterEach(() => {
    mockFetch.mockReset();
    vi.restoreAllMocks();
  });

  it("executes function when auto_approved", async () => {
    mockFetch.mockReturnValueOnce(
      jsonResponse({
        request_id: "req-1",
        status: "auto_approved",
        auto_approved: true,
      }),
    );

    const buyItem = guard(
      async (item: string, amount: number) => `Bought ${item} for $${amount}`,
      {
        token: "agt_test",
        baseUrl: "https://api.example.com/api/v1/agent-api",
        category: "groceries",
      },
    );

    const result = await buyItem("apples", 9.99);
    expect(result).toBe("Bought apples for $9.99");
  });

  it("throws when request is rejected", async () => {
    mockFetch.mockReturnValueOnce(
      jsonResponse({
        request_id: "req-2",
        status: "rejected",
        auto_approved: false,
      }),
    );

    const buyItem = guard(async () => "done", {
      token: "agt_test",
      baseUrl: "https://api.example.com/api/v1/agent-api",
      category: "hardware",
      amount: 500,
    });

    await expect(buyItem()).rejects.toThrow(LetAgentPayError);
  });

  it("throws when request is pending", async () => {
    mockFetch.mockReturnValueOnce(
      jsonResponse({
        request_id: "req-3",
        status: "pending",
        auto_approved: false,
      }),
    );

    const buyItem = guard(async (_item: string, amount: number) => amount, {
      token: "agt_test",
      baseUrl: "https://api.example.com/api/v1/agent-api",
      category: "software",
    });

    await expect(buyItem("license", 99)).rejects.toThrow("pending approval");
  });

  it("uses fixed amount from options", async () => {
    mockFetch.mockReturnValueOnce(
      jsonResponse({
        request_id: "req-4",
        status: "auto_approved",
        auto_approved: true,
      }),
    );

    const callApi = guard(async (prompt: string) => `Response to: ${prompt}`, {
      token: "agt_test",
      baseUrl: "https://api.example.com/api/v1/agent-api",
      category: "api_calls",
      amount: 0.03,
    });

    await callApi("Hello");

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.amount).toBe(0.03);
  });

  it("throws if amount cannot be determined", async () => {
    const noAmount = guard(async (text: string) => text, {
      token: "agt_test",
      baseUrl: "https://api.example.com/api/v1/agent-api",
      category: "other",
    });

    await expect(noAmount("hello")).rejects.toThrow(
      "could not determine amount",
    );
  });
});
