import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { BudgetBar } from "@/components/budget-bar";

describe("BudgetBar", () => {
  it("renders remaining as primary text", () => {
    render(<BudgetBar currency="USD" spent={50} budget={100} />);
    expect(screen.getByText("$50.00 available")).toBeInTheDocument();
  });

  it("does not show spent in budget bar", () => {
    render(<BudgetBar currency="USD" spent={50} budget={100} />);
    expect(screen.queryByText(/spent/)).not.toBeInTheDocument();
  });

  it("green segment for available budget", () => {
    const { container } = render(<BudgetBar currency="USD" spent={20} budget={100} />);
    const bar = container.querySelector(".bg-green-500");
    expect(bar).toBeTruthy();
  });

  it("yellow segment for held funds", () => {
    const { container } = render(<BudgetBar currency="USD" spent={50} budget={200} held={30} />);
    const bar = container.querySelector(".bg-yellow-500");
    expect(bar).toBeTruthy();
  });

  it("no yellow segment when no holds", () => {
    const { container } = render(<BudgetBar currency="USD" spent={50} budget={200} held={0} />);
    const bar = container.querySelector(".bg-yellow-500");
    expect(bar).toBeNull();
  });

  it("handles zero budget", () => {
    render(<BudgetBar currency="USD" spent={0} budget={0} />);
    expect(screen.getByText("$0.00 available")).toBeInTheDocument();
  });

  it("green bar fills 100% when no holds", () => {
    const { container } = render(<BudgetBar currency="USD" spent={30} budget={100} />);
    const greenBar = container.querySelector(".bg-green-500") as HTMLElement;
    expect(greenBar.style.width).toBe("100%");
  });

  it("shows held amount text when present", () => {
    render(<BudgetBar currency="USD" spent={50} budget={200} held={30} />);
    expect(screen.getByText("$30.00 held")).toBeInTheDocument();
  });

  it("remaining accounts for held", () => {
    render(<BudgetBar currency="USD" spent={50} budget={200} held={30} />);
    expect(screen.getByText("$120.00 available")).toBeInTheDocument();
  });

  it("shows muted bar when fully spent", () => {
    const { container } = render(<BudgetBar currency="USD" spent={100} budget={100} />);
    const mutedBar = container.querySelector(".bg-muted");
    expect(mutedBar).toBeTruthy();
  });
});
