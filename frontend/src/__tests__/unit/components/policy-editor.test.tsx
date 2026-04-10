import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PolicyEditor } from "@/components/policy-editor";

describe("PolicyEditor", () => {
  const defaultProps = {
    policy: {},
    currency: "USD",
    onSave: vi.fn(),
  };

  it("renders form fields for limits", () => {
    render(<PolicyEditor {...defaultProps} />);
    expect(screen.getByText("Per request limit")).toBeInTheDocument();
    expect(screen.getByText("Daily limit")).toBeInTheDocument();
    expect(screen.getByText("Weekly limit")).toBeInTheDocument();
    expect(screen.getByText("Monthly limit")).toBeInTheDocument();
  });

  it("populates fields from existing policy", () => {
    render(
      <PolicyEditor
        {...defaultProps}
        policy={{ daily_limit: 500, per_request_limit: 100 }}
      />,
    );
    const inputs = screen.getAllByRole("spinbutton");
    const values = inputs.map((i) => (i as HTMLInputElement).value);
    expect(values).toContain("100");
    expect(values).toContain("500");
  });

  it("shows auto-approve checkbox", () => {
    render(<PolicyEditor {...defaultProps} />);
    expect(screen.getByLabelText("Auto-approve")).toBeInTheDocument();
  });

  it("shows max amount input when auto-approve is checked", async () => {
    const user = userEvent.setup();
    render(<PolicyEditor {...defaultProps} />);
    await user.click(screen.getByLabelText("Auto-approve"));
    expect(screen.getByText(/Max amount/)).toBeInTheDocument();
  });

  it("calls onSave with updated policy on save", async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(<PolicyEditor {...defaultProps} onSave={onSave} />);

    const inputs = screen.getAllByPlaceholderText("No limit");
    // First input is per_request_limit
    await user.type(inputs[0], "50");

    await user.click(screen.getByRole("button", { name: /Save Policy/ }));
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ per_request_limit: 50 }),
    );
  });

  it("switches to JSON mode", async () => {
    const user = userEvent.setup();
    render(
      <PolicyEditor {...defaultProps} policy={{ daily_limit: 100 }} />,
    );
    await user.click(screen.getByRole("button", { name: /JSON/ }));
    const textarea = screen.getByRole("textbox");
    expect((textarea as HTMLTextAreaElement).value).toContain('"daily_limit": 100');
  });

  it("saves valid JSON in JSON mode", async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(<PolicyEditor {...defaultProps} onSave={onSave} />);

    await user.click(screen.getByRole("button", { name: /JSON/ }));
    const textarea = screen.getByRole("textbox");
    await user.clear(textarea);
    await user.paste('{"daily_limit": 200}');
    await user.click(screen.getByRole("button", { name: /Save Policy/ }));

    expect(onSave).toHaveBeenCalledWith({ daily_limit: 200 });
  });

  it("shows error for invalid JSON", async () => {
    const user = userEvent.setup();
    render(<PolicyEditor {...defaultProps} />);

    await user.click(screen.getByRole("button", { name: /JSON/ }));
    const textarea = screen.getByRole("textbox");
    await user.clear(textarea);
    await user.paste("not json");
    await user.click(screen.getByRole("button", { name: /Save Policy/ }));

    expect(screen.getByText("Invalid JSON")).toBeInTheDocument();
  });

  it("adds and removes allowed categories", async () => {
    const user = userEvent.setup();
    render(<PolicyEditor {...defaultProps} />);

    const inputs = screen.getAllByPlaceholderText("Add category...");
    // First "Add category..." input is for allowed categories
    await user.type(inputs[0], "food");
    await user.keyboard("{Enter}");

    expect(screen.getByText("food")).toBeInTheDocument();

    // Remove it
    const removeButtons = screen.getAllByRole("button").filter(
      (btn) => btn.querySelector("svg") && btn.closest(".gap-1"),
    );
    // Find the X button next to "food" badge
    const foodBadge = screen.getByText("food").closest("[class*='badge']");
    const removeBtn = foodBadge?.querySelector("button");
    if (removeBtn) await user.click(removeBtn);

    expect(screen.queryByText("food")).not.toBeInTheDocument();
  });

  it("disables save button when saving", () => {
    render(<PolicyEditor {...defaultProps} saving={true} />);
    expect(screen.getByRole("button", { name: /Saving/ })).toBeDisabled();
  });
});