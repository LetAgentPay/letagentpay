import { describe, expect, it } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { AuthProvider, useAuth } from "@/lib/auth-context";
import { server } from "../../mocks/server";
import { mockReplace } from "../../setup";

function TestConsumer() {
  const { account, loading, isAuthenticated, logout, refresh } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="email">{account?.email ?? "none"}</span>
      <button onClick={logout}>Logout</button>
      <button onClick={refresh}>Refresh</button>
    </div>
  );
}

describe("AuthProvider", () => {
  it("loads account on mount", async () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("loading")).toHaveTextContent("false"),
    );
    expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    expect(screen.getByTestId("email")).toHaveTextContent("test@example.com");
  });

  it("sets isAuthenticated=false on failed getMe", async () => {
    server.use(
      http.get("/api/v1/me", () =>
        HttpResponse.json({ detail: "Unauthorized" }, { status: 401 }),
      ),
    );
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("loading")).toHaveTextContent("false"),
    );
    expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    expect(screen.getByTestId("email")).toHaveTextContent("none");
  });

  it("logout clears account and redirects", async () => {
    const user = userEvent.setup();
    localStorage.setItem("agent_id", "agent-1");

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("loading")).toHaveTextContent("false"),
    );

    await user.click(screen.getByText("Logout"));

    await waitFor(() =>
      expect(screen.getByTestId("authenticated")).toHaveTextContent("false"),
    );
    expect(localStorage.getItem("agent_id")).toBeNull();
    expect(mockReplace).toHaveBeenCalledWith("/auth/signin");
  });

  it("refresh re-fetches account", async () => {
    const user = userEvent.setup();
    let callCount = 0;
    server.use(
      http.get("/api/v1/me", () => {
        callCount++;
        return HttpResponse.json({
          id: "acc-1",
          email: `user${callCount}@test.com`,
          name: null,
          currency: "USD",
          timezone: "UTC",
          plan: "free",
          created_at: "2026-01-01",
        });
      }),
    );

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("email")).toHaveTextContent("user1@test.com"),
    );

    await user.click(screen.getByText("Refresh"));
    await waitFor(() =>
      expect(screen.getByTestId("email")).toHaveTextContent("user2@test.com"),
    );
  });
});

describe("useAuth outside provider", () => {
  it("returns defaults", () => {
    function Bare() {
      const { loading, isAuthenticated } = useAuth();
      return (
        <div>
          <span data-testid="loading">{String(loading)}</span>
          <span data-testid="auth">{String(isAuthenticated)}</span>
        </div>
      );
    }
    render(<Bare />);
    expect(screen.getByTestId("loading")).toHaveTextContent("true");
    expect(screen.getByTestId("auth")).toHaveTextContent("false");
  });
});
