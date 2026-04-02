import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { AuthProvider } from "@/lib/auth-context";
import { server } from "../../mocks/server";
import { mockAgent } from "../../mocks/fixtures";

const API = "/api/v1";

// Must mock useParams for dynamic route
vi.mock("next/navigation", async () => {
  const actual = await vi.importActual("next/navigation");
  return {
    ...actual,
    useRouter: () => ({
      push: vi.fn(),
      replace: vi.fn(),
      back: vi.fn(),
      refresh: vi.fn(),
    }),
    useParams: () => ({ id: "agent-1" }),
    useSearchParams: () => new URLSearchParams(),
    usePathname: () => "/dashboard/agent/agent-1/connect",
  };
});

// Dynamic import after mock setup
const { default: ConnectPage } = await import(
  "@/app/dashboard/agent/[id]/connect/page"
);

function renderConnect() {
  return render(
    <AuthProvider>
      <ConnectPage />
    </AuthProvider>,
  );
}

describe("ConnectPage", () => {
  it("shows agent name in header", async () => {
    renderConnect();
    expect(
      await screen.findByText(/Connect: Test Agent/),
    ).toBeInTheDocument();
  });

  it("shows agent token", async () => {
    renderConnect();
    expect(
      await screen.findByText("agt_test_token_abc123"),
    ).toBeInTheDocument();
  });

  it("shows copy button for token", async () => {
    renderConnect();
    await screen.findByText("agt_test_token_abc123");
    // The copy button is an icon button
    const buttons = screen.getAllByRole("button");
    const copyBtn = buttons.find(
      (b) => b.querySelector("svg") !== null,
    );
    expect(copyBtn).toBeDefined();
  });

  it("shows connection method tabs", async () => {
    renderConnect();
    await screen.findByText("agt_test_token_abc123");
    expect(screen.getByText("curl")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("JavaScript")).toBeInTheDocument();
    expect(screen.getByText("MCP")).toBeInTheDocument();
  });

  it("shows curl example by default", async () => {
    renderConnect();
    await screen.findByText("Quick Test with curl");
  });

  it("shows API endpoints list", async () => {
    renderConnect();
    await screen.findByText("API Endpoints");
    expect(
      screen.getByText("POST /agent-api/requests"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("GET /agent-api/budget"),
    ).toBeInTheDocument();
  });

  it("shows back button", async () => {
    renderConnect();
    expect(await screen.findByText("Back")).toBeInTheDocument();
  });

  it("shows not found when agent fails to load", async () => {
    server.use(
      http.get(`${API}/agents/:id`, () =>
        HttpResponse.json({ detail: "Not found" }, { status: 404 }),
      ),
    );
    renderConnect();
    expect(
      await screen.findByText("Agent not found"),
    ).toBeInTheDocument();
  });

  it("switches to MCP tab and shows config", async () => {
    const user = userEvent.setup();
    renderConnect();
    await screen.findByText("Quick Test with curl");
    await user.click(screen.getByRole("tab", { name: "MCP" }));
    await waitFor(() =>
      expect(
        screen.getByText("Model Context Protocol", { exact: false }),
      ).toBeInTheDocument(),
    );
  });
});
