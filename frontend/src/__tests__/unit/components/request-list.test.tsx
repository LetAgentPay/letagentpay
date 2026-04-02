import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { RequestList } from "@/components/request-list";
import { mockRequest, mockPaginatedRequests } from "../../mocks/fixtures";
import { server } from "../../mocks/server";

describe("RequestList", () => {
  it("renders list of requests after load", async () => {
    render(<RequestList agentId="agent-1" currency="USD" />);
    expect(await screen.findByText("$42.50")).toBeInTheDocument();
  });

  it("shows 'No requests found' for empty list", async () => {
    server.use(
      http.get("/api/v1/agents/:id/requests", () =>
        HttpResponse.json(mockPaginatedRequests([], { total: 0 })),
      ),
    );
    render(<RequestList agentId="agent-1" currency="USD" />);
    expect(
      await screen.findByText("No requests found"),
    ).toBeInTheDocument();
  });

  it("renders all status filter buttons including new statuses", async () => {
    render(<RequestList agentId="agent-1" currency="USD" />);
    await screen.findByText("$42.50");
    expect(screen.getByText("All")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText("Approved")).toBeInTheDocument();
    expect(screen.getByText("Auto_approved")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("Rejected")).toBeInTheDocument();
    expect(screen.getByText("Expired")).toBeInTheDocument();
  });

  it("clicking filter reloads with that status", async () => {
    const user = userEvent.setup();
    let lastUrl = "";
    server.use(
      http.get("/api/v1/agents/:id/requests", ({ request }) => {
        lastUrl = request.url;
        return HttpResponse.json(mockPaginatedRequests());
      }),
    );
    render(<RequestList agentId="agent-1" currency="USD" />);
    await screen.findByText("$42.50");
    await user.click(screen.getByText("Pending"));
    await waitFor(() => expect(lastUrl).toContain("status=pending"));
  });

  it("pagination controls work", async () => {
    const user = userEvent.setup();
    const items = Array.from({ length: 10 }, (_, i) =>
      mockRequest({ id: `req-${i}`, amount: `${10 + i}.00` }),
    );
    server.use(
      http.get("/api/v1/agents/:id/requests", () =>
        HttpResponse.json(mockPaginatedRequests(items, { total: 25 })),
      ),
    );
    render(<RequestList agentId="agent-1" currency="USD" />);
    await screen.findByText("1-10 of 25");

    expect(screen.getByText("Previous")).toBeDisabled();
    expect(screen.getByText("Next")).toBeEnabled();

    await user.click(screen.getByText("Next"));
    await waitFor(() =>
      expect(screen.getByText("11-20 of 25")).toBeInTheDocument(),
    );
  });

  it("refreshKey prop triggers reload", async () => {
    let fetchCount = 0;
    server.use(
      http.get("/api/v1/agents/:id/requests", () => {
        fetchCount++;
        return HttpResponse.json(mockPaginatedRequests());
      }),
    );
    const { rerender } = render(
      <RequestList agentId="agent-1" currency="USD" refreshKey={0} />,
    );
    await screen.findByText("$42.50");
    const initial = fetchCount;
    rerender(<RequestList agentId="agent-1" currency="USD" refreshKey={1} />);
    await waitFor(() => expect(fetchCount).toBeGreaterThan(initial));
  });
});
