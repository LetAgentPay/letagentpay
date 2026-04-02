import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toast } from "sonner";
import { AgentCard } from "@/components/agent-card";
import { mockAgent } from "../../mocks/fixtures";

describe("AgentCard", () => {
  it("renders agent name and status", () => {
    render(<AgentCard agent={mockAgent()} currency="USD" onUpdate={vi.fn()} />);
    expect(screen.getByText("Test Agent")).toBeInTheDocument();
    expect(screen.getByText("active")).toBeInTheDocument();
  });

  it("renders description", () => {
    render(<AgentCard agent={mockAgent()} currency="USD" onUpdate={vi.fn()} />);
    expect(screen.getByText("A test agent")).toBeInTheDocument();
  });

  it("hides description when null", () => {
    render(
      <AgentCard
        agent={mockAgent({ description: null })}
        currency="USD" onUpdate={vi.fn()}
      />,
    );
    expect(screen.queryByText("A test agent")).not.toBeInTheDocument();
  });

  it("token hidden by default", () => {
    render(<AgentCard agent={mockAgent()} currency="USD" onUpdate={vi.fn()} />);
    expect(screen.getByText("agt_••••••••••••")).toBeInTheDocument();
    expect(
      screen.queryByText("agt_test_token_abc123"),
    ).not.toBeInTheDocument();
  });

  function findEyeButton() {
    // The eye toggle is a ghost icon button with h-7 w-7 class, near the token
    const buttons = screen.getAllByRole("button");
    const eyeButtons = buttons.filter(
      (b) => b.className.includes("h-7") && b.className.includes("w-7"),
    );
    // The last h-7 w-7 button is the eye toggle (copy button only appears after reveal)
    return eyeButtons[eyeButtons.length - 1];
  }

  it("clicking eye reveals token", async () => {
    const user = userEvent.setup();
    render(<AgentCard agent={mockAgent()} currency="USD" onUpdate={vi.fn()} />);
    await user.click(findEyeButton());
    expect(screen.getByText("agt_test_token_abc123")).toBeInTheDocument();
  });

  it("clicking revealed token copies to clipboard", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { ...navigator, clipboard: { writeText } });
    render(<AgentCard agent={mockAgent()} currency="USD" onUpdate={vi.fn()} />);
    await user.click(findEyeButton());
    await user.click(screen.getByText("agt_test_token_abc123"));
    expect(writeText).toHaveBeenCalledWith("agt_test_token_abc123");
  });

  it("copy button copies token to clipboard", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { ...navigator, clipboard: { writeText } });
    render(<AgentCard agent={mockAgent()} currency="USD" onUpdate={vi.fn()} />);
    const eyeBtn = findEyeButton();
    await user.click(eyeBtn);
    // After revealing, there are now two h-7 w-7 buttons: copy and eye toggle
    const iconButtons = screen.getAllByRole("button").filter(
      (b) => b.className.includes("h-7") && b.className.includes("w-7"),
    );
    // The copy button is the first one (before the eye toggle)
    const copyBtn = iconButtons.find((b) => b !== eyeBtn)!;
    await user.click(copyBtn);
    expect(writeText).toHaveBeenCalledWith("agt_test_token_abc123");
  });

  it("shows Pause button for active agent", () => {
    render(<AgentCard agent={mockAgent()} currency="USD" onUpdate={vi.fn()} />);
    expect(screen.getByText("Pause")).toBeInTheDocument();
  });

  it("shows Resume button for paused agent", () => {
    render(
      <AgentCard
        agent={mockAgent({ status: "paused" })}
        currency="USD" onUpdate={vi.fn()}
      />,
    );
    expect(screen.getByText("Resume")).toBeInTheDocument();
  });

  it("pause calls onUpdate", async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn();
    render(<AgentCard agent={mockAgent()} currency="USD" onUpdate={onUpdate} />);
    await user.click(screen.getByText("Pause"));
    await waitFor(() => expect(onUpdate).toHaveBeenCalled());
  });

  it("resume calls onUpdate", async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn();
    render(
      <AgentCard
        agent={mockAgent({ status: "paused" })}
        currency="USD" onUpdate={onUpdate}
      />,
    );
    await user.click(screen.getByText("Resume"));
    await waitFor(() => expect(onUpdate).toHaveBeenCalled());
  });

  describe("budget top-up", () => {
    it("clicking budget bar opens top-up form", async () => {
      const user = userEvent.setup();
      render(<AgentCard agent={mockAgent()} currency="USD" onUpdate={vi.fn()} />);
      const budgetArea = screen.getByText(/Click to top up budget/);
      await user.click(budgetArea.closest(".group")!);
      expect(screen.getByPlaceholderText("100.00")).toBeInTheDocument();
      expect(screen.getByText("Top up")).toBeInTheDocument();
      expect(screen.getByText("Cancel")).toBeInTheDocument();
    });

    it("shows 'add' for zero budget agents", () => {
      render(
        <AgentCard
          agent={mockAgent({ budget: "0.00", spent: "0.00", remaining: "0.00" })}
          currency="USD" onUpdate={vi.fn()}
        />,
      );
      expect(screen.getByText(/Click to add budget/)).toBeInTheDocument();
    });

    it("submitting top-up form calls api and shows toast", async () => {
      const user = userEvent.setup();
      const onUpdate = vi.fn();
      render(<AgentCard agent={mockAgent()} currency="USD" onUpdate={onUpdate} />);
      const budgetArea = screen.getByText(/Click to top up budget/);
      await user.click(budgetArea.closest(".group")!);
      const input = screen.getByPlaceholderText("100.00");
      await user.clear(input);
      await user.type(input, "500");
      await user.click(screen.getByText("Top up"));
      await waitFor(() => {
        expect(onUpdate).toHaveBeenCalled();
        expect(toast.success).toHaveBeenCalledWith("Budget topped up by $500.00");
      });
    });

    it("cancel closes budget form", async () => {
      const user = userEvent.setup();
      render(<AgentCard agent={mockAgent()} currency="USD" onUpdate={vi.fn()} />);
      const budgetArea = screen.getByText(/Click to top up budget/);
      await user.click(budgetArea.closest(".group")!);
      expect(screen.getByText("Top up")).toBeInTheDocument();
      await user.click(screen.getByText("Cancel"));
      expect(screen.queryByText("Top up")).not.toBeInTheDocument();
    });

    it("ignores invalid budget input", async () => {
      const user = userEvent.setup();
      const onUpdate = vi.fn();
      render(<AgentCard agent={mockAgent()} currency="USD" onUpdate={onUpdate} />);
      const budgetArea = screen.getByText(/Click to top up budget/);
      await user.click(budgetArea.closest(".group")!);
      const input = screen.getByPlaceholderText("100.00");
      await user.clear(input);
      await user.click(screen.getByText("Top up"));
      expect(onUpdate).not.toHaveBeenCalled();
    });

    it("editBudget prop opens form automatically", () => {
      const onHandled = vi.fn();
      render(
        <AgentCard
          agent={mockAgent()}
          currency="USD" onUpdate={vi.fn()}
          editBudget={true}
          onEditBudgetHandled={onHandled}
        />,
      );
      expect(screen.getByPlaceholderText("100.00")).toBeInTheDocument();
      expect(onHandled).toHaveBeenCalled();
    });

    it("editBudget starts with empty input (not pre-filled)", () => {
      render(
        <AgentCard
          agent={mockAgent({ budget: "5000.00" })}
          currency="USD" onUpdate={vi.fn()}
          editBudget={true}
          onEditBudgetHandled={vi.fn()}
        />,
      );
      const input = screen.getByPlaceholderText("100.00") as HTMLInputElement;
      expect(input.value).toBe("");
    });
  });

  describe("auto-replenish badge", () => {
    it("shows auto badge when auto-replenish is configured", () => {
      render(
        <AgentCard
          agent={mockAgent({
            auto_replenish: {
              enabled: true,
              threshold: "10.00",
              amount: "50.00",
              max_budget: null,
            },
          })}
          currency="USD" onUpdate={vi.fn()}
        />,
      );
      expect(screen.getByText("auto")).toBeInTheDocument();
    });

    it("hides auto badge when auto-replenish is null", () => {
      render(
        <AgentCard
          agent={mockAgent({ auto_replenish: null })}
          currency="USD" onUpdate={vi.fn()}
        />,
      );
      expect(screen.queryByText("auto")).not.toBeInTheDocument();
    });
  });
});
