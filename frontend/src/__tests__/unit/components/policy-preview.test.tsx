import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PolicyPreview } from "@/components/policy-preview";

describe("PolicyPreview", () => {
  it("shows 'No rules configured' for empty policy", () => {
    render(<PolicyPreview currency="USD" policy={{}} />);
    expect(screen.getByText("No rules configured")).toBeInTheDocument();
  });

  it("renders per_request_limit", () => {
    render(<PolicyPreview currency="USD" policy={{ per_request_limit: 50 }} />);
    expect(screen.getByText(/Per request limit/)).toBeInTheDocument();
    expect(screen.getByText(/\$50\.00/)).toBeInTheDocument();
  });

  it("renders daily_limit", () => {
    render(<PolicyPreview currency="USD" policy={{ daily_limit: 1000 }} />);
    expect(screen.getByText(/Daily limit/)).toBeInTheDocument();
    expect(screen.getByText(/\$1,000\.00/)).toBeInTheDocument();
  });

  it("renders weekly_limit", () => {
    render(<PolicyPreview currency="USD" policy={{ weekly_limit: 5000 }} />);
    expect(screen.getByText(/Weekly limit/)).toBeInTheDocument();
    expect(screen.getByText(/\$5,000\.00/)).toBeInTheDocument();
  });

  it("renders monthly_limit", () => {
    render(<PolicyPreview currency="USD" policy={{ monthly_limit: 20000 }} />);
    expect(screen.getByText(/Monthly limit/)).toBeInTheDocument();
    expect(screen.getByText(/\$20,000\.00/)).toBeInTheDocument();
  });

  it("renders allowed categories as badges", () => {
    render(
      <PolicyPreview
        currency="USD"
        policy={{ allowed_categories: ["food", "transport"] }}
      />,
    );
    expect(screen.getByText("food")).toBeInTheDocument();
    expect(screen.getByText("transport")).toBeInTheDocument();
  });

  it("renders blocked categories", () => {
    render(
      <PolicyPreview currency="USD" policy={{ blocked_categories: ["gambling"] }} />,
    );
    expect(screen.getByText("gambling")).toBeInTheDocument();
  });

  it("renders schedule", () => {
    render(
      <PolicyPreview
        currency="USD"
        policy={{
          schedule: {
            default: { allow: "9:00-17:00" },
            timezone: "UTC",
          },
        }}
      />,
    );
    expect(screen.getByText(/9:00-17:00/)).toBeInTheDocument();
    expect(screen.getByText(/UTC/)).toBeInTheDocument();
  });

  it("renders schedule with overrides", () => {
    render(
      <PolicyPreview
        currency="USD"
        policy={{
          schedule: {
            default: { allow: "00:00-23:59" },
            timezone: "America/New_York",
            overrides: [
              { days: ["saturday", "sunday"], deny: true },
            ],
          },
        }}
      />,
    );
    expect(screen.getByText(/00:00-23:59/)).toBeInTheDocument();
    expect(screen.getByText(/America\/New_York/)).toBeInTheDocument();
    expect(screen.getByText(/saturday, sunday/)).toBeInTheDocument();
    expect(screen.getByText(/denied/)).toBeInTheDocument();
  });

  it("renders auto-approve enabled", () => {
    render(
      <PolicyPreview
        currency="USD"
        policy={{ auto_approve: { enabled: true, max_amount: 25 } }}
      />,
    );
    expect(screen.getByText(/Auto-approve/)).toBeInTheDocument();
    expect(screen.getByText(/Yes/)).toBeInTheDocument();
    expect(screen.getByText(/up to \$25\.00/)).toBeInTheDocument();
  });

  it("renders auto-approve disabled", () => {
    render(
      <PolicyPreview currency="USD" policy={{ auto_approve: { enabled: false } }} />,
    );
    expect(screen.getByText(/No/)).toBeInTheDocument();
  });

  it("renders multiple rules at once", () => {
    render(
      <PolicyPreview
        currency="USD"
        policy={{
          daily_limit: 500,
          per_request_limit: 100,
          allowed_categories: ["groceries"],
        }}
      />,
    );
    expect(screen.getByText(/Daily limit/)).toBeInTheDocument();
    expect(screen.getByText(/Per request limit/)).toBeInTheDocument();
    expect(screen.getByText("groceries")).toBeInTheDocument();
    expect(
      screen.queryByText("No rules configured"),
    ).not.toBeInTheDocument();
  });
});
