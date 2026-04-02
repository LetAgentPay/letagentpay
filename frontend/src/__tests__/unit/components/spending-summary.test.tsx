import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { SpendingSummary } from "@/components/spending-summary";
import { server } from "../../mocks/server";

const API = "/api/v1";

describe("SpendingSummary", () => {
  it("renders spending stats", async () => {
    render(<SpendingSummary currency="USD" agentId="agent-1" />);
    expect(await screen.findByText("Today")).toBeInTheDocument();
    expect(screen.getByText("This week")).toBeInTheDocument();
    expect(screen.getByText("This month")).toBeInTheDocument();
    expect(screen.getByText("$150.00")).toBeInTheDocument();
    expect(screen.getByText("$800.00")).toBeInTheDocument();
    expect(screen.getByText("$2,500.00")).toBeInTheDocument();
  });

  it("renders nothing when stats fail to load", async () => {
    server.use(
      http.get(`${API}/stats/:id/spending`, () =>
        HttpResponse.json({ detail: "Not found" }, { status: 404 }),
      ),
    );
    const { container } = render(<SpendingSummary currency="USD" agentId="bad-id" />);
    // Wait a tick for the async call to resolve
    await new Promise((r) => setTimeout(r, 100));
    expect(container.textContent).toBe("");
  });

  it("re-fetches on refreshKey change", async () => {
    let fetchCount = 0;
    server.use(
      http.get(`${API}/stats/:id/spending`, () => {
        fetchCount++;
        return HttpResponse.json({
          spent_today: "200.00",
          spent_week: "900.00",
          spent_month: "3000.00",
        });
      }),
    );
    const { rerender } = render(
      <SpendingSummary currency="USD" agentId="agent-1" refreshKey={0} />,
    );
    await screen.findByText("$200.00");
    const initial = fetchCount;
    rerender(<SpendingSummary currency="USD" agentId="agent-1" refreshKey={1} />);
    await screen.findByText("$200.00");
    expect(fetchCount).toBeGreaterThan(initial);
  });
});
