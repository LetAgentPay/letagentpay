import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatInput } from "@/components/chat/chat-input";

describe("ChatInput", () => {
  it("renders textarea with default placeholder", () => {
    render(<ChatInput onSend={vi.fn()} />);
    expect(
      screen.getByPlaceholderText("Describe your spending policy..."),
    ).toBeInTheDocument();
  });

  it("uses custom placeholder", () => {
    render(<ChatInput onSend={vi.fn()} placeholder="Custom text" />);
    expect(screen.getByPlaceholderText("Custom text")).toBeInTheDocument();
  });

  it("submit button disabled when empty", () => {
    render(<ChatInput onSend={vi.fn()} />);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("submit button enabled when textarea has text", async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={vi.fn()} />);
    await user.type(screen.getByRole("textbox"), "hello");
    expect(screen.getByRole("button")).toBeEnabled();
  });

  it("calls onSend with trimmed value on submit", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);
    await user.type(screen.getByRole("textbox"), "  hello  ");
    await user.click(screen.getByRole("button"));
    expect(onSend).toHaveBeenCalledWith("hello");
  });

  it("clears textarea after send", async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={vi.fn()} />);
    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "hello");
    await user.click(screen.getByRole("button"));
    expect(textarea).toHaveValue("");
  });

  it("Enter key submits", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);
    await user.type(screen.getByRole("textbox"), "hi{Enter}");
    expect(onSend).toHaveBeenCalledWith("hi");
  });

  it("Shift+Enter does not submit", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);
    await user.type(screen.getByRole("textbox"), "hi{Shift>}{Enter}{/Shift}");
    expect(onSend).not.toHaveBeenCalled();
  });

  it("does not send whitespace-only messages", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);
    await user.type(screen.getByRole("textbox"), "   ");
    await user.click(screen.getByRole("button"));
    expect(onSend).not.toHaveBeenCalled();
  });

  it("disabled prop disables textarea and button", () => {
    render(<ChatInput onSend={vi.fn()} disabled />);
    expect(screen.getByRole("textbox")).toBeDisabled();
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
