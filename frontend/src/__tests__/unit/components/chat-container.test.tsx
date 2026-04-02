import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatContainer } from "@/components/chat/chat-container";
import type { ChatMessage } from "@/lib/types";

describe("ChatContainer", () => {
  const messages: ChatMessage[] = [
    { role: "assistant", content: "Hello!" },
    { role: "user", content: "Set limit 500" },
  ];

  it("renders all messages", () => {
    render(<ChatContainer currency="USD" messages={messages} onSend={vi.fn()} />);
    expect(screen.getByText("Hello!")).toBeInTheDocument();
    expect(screen.getByText("Set limit 500")).toBeInTheDocument();
  });

  it("shows 'Thinking...' when loading", () => {
    render(
      <ChatContainer currency="USD" messages={messages} onSend={vi.fn()} loading />,
    );
    expect(screen.getByText("Thinking...")).toBeInTheDocument();
  });

  it("hides 'Thinking...' when not loading", () => {
    render(
      <ChatContainer
        messages={messages}
        onSend={vi.fn()}
        loading={false}
      />,
    );
    expect(screen.queryByText("Thinking...")).not.toBeInTheDocument();
  });

  it("passes onSend to ChatInput", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatContainer currency="USD" messages={[]} onSend={onSend} />);
    await user.type(screen.getByRole("textbox"), "test{Enter}");
    expect(onSend).toHaveBeenCalledWith("test");
  });

  it("ChatInput is disabled when loading", () => {
    render(
      <ChatContainer currency="USD" messages={[]} onSend={vi.fn()} loading />,
    );
    expect(screen.getByRole("textbox")).toBeDisabled();
  });
});
