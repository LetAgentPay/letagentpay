import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatMessageBubble } from "@/components/chat/chat-message";

describe("ChatMessageBubble", () => {
  it("user message aligned right", () => {
    const { container } = render(
      <ChatMessageBubble currency="USD" message={{ role: "user", content: "Hello" }} />,
    );
    expect(container.firstElementChild).toHaveClass("justify-end");
  });

  it("assistant message aligned left", () => {
    const { container } = render(
      <ChatMessageBubble
        currency="USD"
        message={{ role: "assistant", content: "Hi!" }}
      />,
    );
    expect(container.firstElementChild).toHaveClass("justify-start");
  });

  it("user message has distinct background", () => {
    const { container } = render(
      <ChatMessageBubble currency="USD" message={{ role: "user", content: "Hello" }} />,
    );
    const bubble = container.querySelector(".bg-muted-foreground\\/15");
    expect(bubble).toBeInTheDocument();
  });

  it("assistant message has muted background", () => {
    const { container } = render(
      <ChatMessageBubble
        currency="USD"
        message={{ role: "assistant", content: "Hi!" }}
      />,
    );
    const bubble = container.querySelector(".bg-muted");
    expect(bubble).toBeInTheDocument();
  });

  it("displays message content", () => {
    render(
      <ChatMessageBubble
        currency="USD"
        message={{ role: "user", content: "Test message" }}
      />,
    );
    expect(screen.getByText("Test message")).toBeInTheDocument();
  });

  it("renders PolicyPreview when policy_preview present", () => {
    render(
      <ChatMessageBubble
        currency="USD"
        message={{
          role: "assistant",
          content: "Here's the policy",
          policy_preview: { daily_limit: 500 },
        }}
      />,
    );
    expect(screen.getByText("Policy Preview")).toBeInTheDocument();
    expect(screen.getByText(/\$500\.00/)).toBeInTheDocument();
  });

  it("does not render PolicyPreview when absent", () => {
    render(
      <ChatMessageBubble
        currency="USD"
        message={{ role: "assistant", content: "No policy" }}
      />,
    );
    expect(screen.queryByText("Policy Preview")).not.toBeInTheDocument();
  });

  it("preserves whitespace", () => {
    const { container } = render(
      <ChatMessageBubble currency="USD" message={{ role: "user", content: "Line 1" }} />,
    );
    const p = container.querySelector("p");
    expect(p).toHaveClass("whitespace-pre-wrap");
  });
});
