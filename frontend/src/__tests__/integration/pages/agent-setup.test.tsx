import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { toast } from "sonner";
import { server } from "../../mocks/server";
import { mockPush } from "../../setup";

// Override useSearchParams to provide agent id
vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>(
    "next/navigation",
  );
  return {
    ...actual,
    useRouter: () => ({
      push: mockPush,
      replace: vi.fn(),
      back: vi.fn(),
      refresh: vi.fn(),
    }),
    useSearchParams: () => new URLSearchParams("id=agent-1"),
    usePathname: () => "/dashboard/agent/setup",
  };
});

import AgentSetupPage from "@/app/dashboard/agent/setup/page";

describe("AgentSetupPage", () => {
  it("shows initial greeting message", () => {
    render(<AgentSetupPage />);
    expect(
      screen.getByText(/I'll help you set up a spending policy/),
    ).toBeInTheDocument();
  });

  it("sending a message adds user bubble and gets response", async () => {
    const user = userEvent.setup();
    render(<AgentSetupPage />);

    await user.type(
      screen.getByPlaceholderText("Describe your spending policy..."),
      "Set daily limit 1000{Enter}",
    );

    // User message appears
    expect(screen.getByText("Set daily limit 1000")).toBeInTheDocument();

    // Assistant response with policy preview
    expect(
      await screen.findByText("Daily limit of 1000, groceries only"),
    ).toBeInTheDocument();
    expect(screen.getByText("Policy Preview")).toBeInTheDocument();
  });

  it("shows Confirm Policy button after first preview", async () => {
    const user = userEvent.setup();
    render(<AgentSetupPage />);

    expect(screen.queryByText("Confirm Policy")).not.toBeInTheDocument();

    await user.type(
      screen.getByPlaceholderText("Describe your spending policy..."),
      "Set limit{Enter}",
    );

    expect(await screen.findByText("Confirm Policy")).toBeInTheDocument();
  });

  it("confirm redirects to dashboard", async () => {
    const user = userEvent.setup();
    render(<AgentSetupPage />);

    await user.type(
      screen.getByPlaceholderText("Describe your spending policy..."),
      "Set limit{Enter}",
    );
    await screen.findByText("Confirm Policy");

    await user.click(screen.getByText("Confirm Policy"));
    await waitFor(() =>
      expect(mockPush).toHaveBeenCalledWith("/dashboard"),
    );
    expect(toast.success).toHaveBeenCalledWith("Policy confirmed!");
  });

  it("shows error on confirm failure", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(
        "/api/v1/agents/:id/policy/ai/confirm",
        () => HttpResponse.json({ detail: "No pending policy" }, { status: 400 }),
      ),
    );
    render(<AgentSetupPage />);

    await user.type(
      screen.getByPlaceholderText("Describe your spending policy..."),
      "Set limit{Enter}",
    );
    await screen.findByText("Confirm Policy");

    await user.click(screen.getByText("Confirm Policy"));
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("No pending policy"),
    );
  });

  it("shows error in chat on AI failure", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/v1/agents/:id/policy/ai", () =>
        HttpResponse.json({ detail: "AI unavailable" }, { status: 422 }),
      ),
    );
    render(<AgentSetupPage />);

    await user.type(
      screen.getByPlaceholderText("Describe your spending policy..."),
      "test{Enter}",
    );

    expect(
      await screen.findByText("Error: AI unavailable"),
    ).toBeInTheDocument();
  });

  it("shows Thinking... while loading", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(
        "/api/v1/agents/:id/policy/ai",
        async () => {
          await new Promise((r) => setTimeout(r, 200));
          return HttpResponse.json({
            policy_preview: {},
            explanation: "ok",
            session_id: "s1",
          });
        },
      ),
    );
    render(<AgentSetupPage />);

    await user.type(
      screen.getByPlaceholderText("Describe your spending policy..."),
      "test{Enter}",
    );

    expect(screen.getByText("Thinking...")).toBeInTheDocument();
  });
});
