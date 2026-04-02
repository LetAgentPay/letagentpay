import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RequestCard } from "@/components/request-card";
import { mockRequest } from "../../mocks/fixtures";

describe("RequestCard", () => {
  it("renders amount, category, and status", () => {
    render(<RequestCard request={mockRequest()} currency="USD" onUpdate={vi.fn()} />);
    expect(screen.getByText("$42.50")).toBeInTheDocument();
    expect(screen.getByText("groceries")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
  });

  it("renders merchant and description", () => {
    render(<RequestCard request={mockRequest()} currency="USD" onUpdate={vi.fn()} />);
    expect(screen.getByText("Test Store")).toBeInTheDocument();
    expect(screen.getByText("Weekly groceries")).toBeInTheDocument();
  });

  it("renders only merchant when no description", () => {
    render(
      <RequestCard
        request={mockRequest({ description: null })}
        currency="USD" onUpdate={vi.fn()}
      />,
    );
    expect(screen.getByText("Test Store")).toBeInTheDocument();
    expect(screen.queryByText("—")).not.toBeInTheDocument();
  });

  it("shows approve/reject buttons for pending", () => {
    render(<RequestCard request={mockRequest()} currency="USD" onUpdate={vi.fn()} />);
    expect(screen.getAllByRole("button")).toHaveLength(2);
  });

  it("hides buttons for non-pending", () => {
    render(
      <RequestCard
        request={mockRequest({ status: "approved" })}
        currency="USD" onUpdate={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("approve calls onUpdate", async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn();
    render(<RequestCard request={mockRequest()} currency="USD" onUpdate={onUpdate} />);
    const buttons = screen.getAllByRole("button");
    await user.click(buttons[0]); // approve button
    await waitFor(() => expect(onUpdate).toHaveBeenCalled());
  });

  it("reject calls onUpdate", async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn();
    render(<RequestCard request={mockRequest()} currency="USD" onUpdate={onUpdate} />);
    const buttons = screen.getAllByRole("button");
    await user.click(buttons[1]); // reject button
    await waitFor(() => expect(onUpdate).toHaveBeenCalled());
  });

  it("renders agent_comment when present", () => {
    render(
      <RequestCard
        request={mockRequest({ agent_comment: "Need for meal prep" })}
        currency="USD" onUpdate={vi.fn()}
      />,
    );
    expect(screen.getByText(/Need for meal prep/)).toBeInTheDocument();
  });

  it("does not render comment section when null", () => {
    render(
      <RequestCard
        request={mockRequest({ agent_comment: null })}
        currency="USD" onUpdate={vi.fn()}
      />,
    );
    expect(screen.queryByText(/"/)).not.toBeInTheDocument();
  });

  it("renders completed status", () => {
    render(
      <RequestCard
        request={mockRequest({ status: "completed" })}
        currency="USD" onUpdate={vi.fn()}
      />,
    );
    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders failed status", () => {
    render(
      <RequestCard
        request={mockRequest({ status: "failed" })}
        currency="USD" onUpdate={vi.fn()}
      />,
    );
    expect(screen.getByText("failed")).toBeInTheDocument();
  });

  it("shows actual amount when different from requested", () => {
    render(
      <RequestCard
        request={mockRequest({ status: "completed", amount: "50.00", actual_amount: "45.00", completed_at: "2026-01-01T12:00:00" })}
        currency="USD" onUpdate={vi.fn()}
      />,
    );
    expect(screen.getByText("$50.00")).toBeInTheDocument();
    expect(screen.getByText("Actual: $45.00")).toBeInTheDocument();
  });

  it("does not show actual amount when same as requested", () => {
    render(
      <RequestCard
        request={mockRequest({ status: "completed", amount: "50.00", actual_amount: "50.00", completed_at: "2026-01-01T12:00:00" })}
        currency="USD" onUpdate={vi.fn()}
      />,
    );
    expect(screen.queryByText(/Actual/)).not.toBeInTheDocument();
  });

  it("shows confirmation block for completed requests", () => {
    render(
      <RequestCard
        request={mockRequest({ status: "completed", completed_at: "2026-01-01T12:00:00" })}
        currency="USD" onUpdate={vi.fn()}
      />,
    );
    expect(screen.getByText(/Confirmed by agent/)).toBeInTheDocument();
  });

  it("shows failed purchase block for failed requests", () => {
    render(
      <RequestCard
        request={mockRequest({ status: "failed", completed_at: "2026-01-01T12:00:00" })}
        currency="USD" onUpdate={vi.fn()}
      />,
    );
    expect(screen.getByText(/Purchase failed/)).toBeInTheDocument();
  });

  it("shows receipt link when receipt_url is present", () => {
    render(
      <RequestCard
        request={mockRequest({ status: "completed", completed_at: "2026-01-01T12:00:00", receipt_url: "https://example.com/receipt" })}
        currency="USD" onUpdate={vi.fn()}
      />,
    );
    const link = screen.getByText("Receipt");
    expect(link).toBeInTheDocument();
    expect(link.closest("a")).toHaveAttribute("href", "https://example.com/receipt");
  });

  it("renders auto_approved status without buttons", () => {
    render(
      <RequestCard
        request={mockRequest({ status: "auto_approved" })}
        currency="USD" onUpdate={vi.fn()}
      />,
    );
    expect(screen.getByText("auto_approved")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("buttons disabled while loading", async () => {
    const user = userEvent.setup();
    // Use a slow handler to keep loading state
    const { server } = await import("../../mocks/server");
    const { http, HttpResponse } = await import("msw");
    server.use(
      http.post("/api/v1/requests/:id/approve", async () => {
        await new Promise((r) => setTimeout(r, 500));
        return HttpResponse.json({ request_id: "req-1", status: "approved" });
      }),
    );
    render(<RequestCard request={mockRequest()} currency="USD" onUpdate={vi.fn()} />);
    const buttons = screen.getAllByRole("button");
    await user.click(buttons[0]);
    await waitFor(() => {
      buttons.forEach((btn) => expect(btn).toBeDisabled());
    });
  });
});
