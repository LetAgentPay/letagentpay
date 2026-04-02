import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import DashboardPage from "@/app/dashboard/page";
import { AuthProvider } from "@/lib/auth-context";
import { server } from "../../mocks/server";
import { mockAgent, mockPaginatedRequests } from "../../mocks/fixtures";
import { mockPush } from "../../setup";

const API = "/api/v1";

function renderDashboard() {
  return render(
    <AuthProvider>
      <DashboardPage />
    </AuthProvider>,
  );
}

describe("DashboardPage", () => {
  describe("no agents", () => {
    beforeEach(() => {
      server.use(
        http.get(`${API}/agents`, () =>
          HttpResponse.json({ agents: [] }),
        ),
      );
    });

    it("shows create agent form when no agents exist", async () => {
      renderDashboard();
      expect(
        await screen.findByText("Create Your AI Agent"),
      ).toBeInTheDocument();
      expect(
        screen.getByPlaceholderText("My Shopping Agent"),
      ).toBeInTheDocument();
    });

    it("creates agent and redirects to setup", async () => {
      const user = userEvent.setup();
      renderDashboard();
      await screen.findByText("Create Your AI Agent");

      await user.type(
        screen.getByPlaceholderText("My Shopping Agent"),
        "Shopper",
      );
      await user.click(screen.getByText("Create Agent"));

      await waitFor(() => {
        expect(localStorage.getItem("agent_id")).toBeTruthy();
        expect(mockPush).toHaveBeenCalledWith(
          expect.stringContaining("/dashboard/agent/setup?id="),
        );
      });
    });

    it("shows error on create failure", async () => {
      const user = userEvent.setup();
      server.use(
        http.post(`${API}/agents`, () =>
          HttpResponse.json({ detail: "Already exists" }, { status: 409 }),
        ),
      );
      renderDashboard();
      await screen.findByText("Create Your AI Agent");

      await user.type(
        screen.getByPlaceholderText("My Shopping Agent"),
        "Bot",
      );
      await user.click(screen.getByText("Create Agent"));
      expect(await screen.findByText("Already exists")).toBeInTheDocument();
    });
  });

  describe("with agent", () => {
    beforeEach(() => {
      localStorage.setItem("agent_id", "agent-1");
    });

    it("shows agent card", async () => {
      renderDashboard();
      const elements = await screen.findAllByText("Test Agent");
      expect(elements.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("active")).toBeInTheDocument();
    });

    it("shows policy preview when agent has policy", async () => {
      renderDashboard();
      expect(await screen.findByText("Edit Policy")).toBeInTheDocument();
    });

    it("shows 'Setup Policy' when agent has no policy", async () => {
      server.use(
        http.get(`${API}/agents`, () =>
          HttpResponse.json({ agents: [mockAgent({ policy: null })] }),
        ),
      );
      renderDashboard();
      expect(await screen.findByText("Setup Policy")).toBeInTheDocument();
    });

    it("shows purchase requests section", async () => {
      renderDashboard();
      expect(
        await screen.findByText("Purchase Requests"),
      ).toBeInTheDocument();
    });

    it("shows spending summary", async () => {
      renderDashboard();
      expect(await screen.findByText("Today")).toBeInTheDocument();
      expect(screen.getByText("This week")).toBeInTheDocument();
      expect(screen.getByText("This month")).toBeInTheDocument();
    });

    it("shows connect button", async () => {
      renderDashboard();
      expect(await screen.findByText("Connect")).toBeInTheDocument();
    });
  });

  describe("agent selector with multiple agents", () => {
    const agent1 = mockAgent({ id: "agent-1", name: "Agent One" });
    const agent2 = mockAgent({ id: "agent-2", name: "Agent Two", status: "paused" });

    beforeEach(() => {
      localStorage.setItem("agent_id", "agent-1");
      server.use(
        http.get(`${API}/agents`, () =>
          HttpResponse.json({ agents: [agent1, agent2] }),
        ),
      );
    });

    it("renders agent selector buttons", async () => {
      renderDashboard();
      const agentOneElements = await screen.findAllByText("Agent One");
      expect(agentOneElements.length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Agent Two").length).toBeGreaterThanOrEqual(1);
    });

    it("selecting a different agent stores it in localStorage", async () => {
      const user = userEvent.setup();
      renderDashboard();
      await screen.findAllByText("Agent One");
      // Agent Two appears only in the selector (not in AgentCard since agent-1 is selected)
      const agent2Buttons = screen.getAllByText("Agent Two");
      await user.click(agent2Buttons[0]);
      expect(localStorage.getItem("agent_id")).toBe("agent-2");
    });

    it("shows New Agent button", async () => {
      renderDashboard();
      expect(await screen.findByText("New Agent")).toBeInTheDocument();
    });

    it("toggling New Agent shows/hides create form", async () => {
      const user = userEvent.setup();
      renderDashboard();
      const newBtn = await screen.findByText("New Agent");
      await user.click(newBtn);
      expect(screen.getByPlaceholderText("My Shopping Agent")).toBeInTheDocument();
      // Cancel button hides the form
      await user.click(screen.getByText("Cancel"));
      expect(screen.queryByPlaceholderText("My Shopping Agent")).not.toBeInTheDocument();
    });

    it("auto-selects first agent when saved agent_id not found", async () => {
      localStorage.setItem("agent_id", "non-existent");
      renderDashboard();
      await waitFor(() => {
        expect(localStorage.getItem("agent_id")).toBe("agent-1");
      });
    });
  });

  describe("budget warnings", () => {
    beforeEach(() => {
      localStorage.setItem("agent_id", "agent-1");
    });

    it("shows no-budget warning when budget is zero", async () => {
      server.use(
        http.get(`${API}/agents`, () =>
          HttpResponse.json({
            agents: [mockAgent({ budget: "0.00", spent: "0.00", held: "0.00", remaining: "0.00" })],
          }),
        ),
      );
      renderDashboard();
      expect(
        await screen.findByText(/no budget set/),
      ).toBeInTheDocument();
      expect(screen.getByText("Top up budget")).toBeInTheDocument();
    });

    it("shows budget-exhausted warning when remaining is zero", async () => {
      server.use(
        http.get(`${API}/agents`, () =>
          HttpResponse.json({
            agents: [mockAgent({ budget: "100.00", spent: "100.00", held: "0.00", remaining: "0.00" })],
          }),
        ),
      );
      renderDashboard();
      expect(
        await screen.findByText(/budget exhausted/),
      ).toBeInTheDocument();
      expect(screen.getByText("Top up budget")).toBeInTheDocument();
    });

    it("shows pending count badge in agent selector", async () => {
      server.use(
        http.get(`${API}/agents`, () =>
          HttpResponse.json({
            agents: [mockAgent({ pending_count: 3 })],
          }),
        ),
      );
      renderDashboard();
      expect(await screen.findByText("3")).toBeInTheDocument();
    });
  });

  describe("create form error handling", () => {
    beforeEach(() => {
      localStorage.setItem("agent_id", "agent-1");
    });

    it("shows generic error when create fails with non-ApiError", async () => {
      const user = userEvent.setup();
      server.use(
        http.post(`${API}/agents`, () => HttpResponse.error()),
      );
      renderDashboard();
      // Open the create form
      const newBtn = await screen.findByText("New Agent");
      await user.click(newBtn);
      await user.type(screen.getByPlaceholderText("My Shopping Agent"), "Bot");
      await user.click(screen.getByText("Create Agent"));
      expect(await screen.findByText("Failed to create agent")).toBeInTheDocument();
    });
  });
});
