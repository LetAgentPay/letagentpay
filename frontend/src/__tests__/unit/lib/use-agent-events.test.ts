import { describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useAgentEvents } from "@/lib/hooks/use-agent-events";
import { MockEventSource } from "../../setup";

describe("useAgentEvents", () => {
  it("creates EventSource with correct URL when agentId provided", () => {
    renderHook(() => useAgentEvents("agent-1", vi.fn()));
    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toContain("/agents/agent-1/events");
  });

  it("sets withCredentials: true", () => {
    renderHook(() => useAgentEvents("agent-1", vi.fn()));
    expect(MockEventSource.instances[0].withCredentials).toBe(true);
  });

  it("calls onEvent with parsed JSON on message", () => {
    const onEvent = vi.fn();
    renderHook(() => useAgentEvents("agent-1", onEvent));
    const es = MockEventSource.instances[0];
    es.onmessage?.(new MessageEvent("message", {
      data: JSON.stringify({ type: "budget_updated", data: { budget: 100 } }),
    }));
    expect(onEvent).toHaveBeenCalledWith({
      type: "budget_updated",
      data: { budget: 100 },
    });
  });

  it("does not create EventSource when agentId is null", () => {
    renderHook(() => useAgentEvents(null, vi.fn()));
    expect(MockEventSource.instances).toHaveLength(0);
  });

  it("closes EventSource on unmount", () => {
    const { unmount } = renderHook(() =>
      useAgentEvents("agent-1", vi.fn()),
    );
    const es = MockEventSource.instances[0];
    unmount();
    expect(es.close).toHaveBeenCalled();
  });

  it("ignores parse errors", () => {
    const onEvent = vi.fn();
    renderHook(() => useAgentEvents("agent-1", onEvent));
    const es = MockEventSource.instances[0];
    // Should not throw
    es.onmessage?.(new MessageEvent("message", { data: "not json" }));
    expect(onEvent).not.toHaveBeenCalled();
  });

  it("reconnects when agentId changes", () => {
    const { rerender } = renderHook(
      ({ id }) => useAgentEvents(id, vi.fn()),
      { initialProps: { id: "agent-1" as string | null } },
    );
    const firstEs = MockEventSource.instances[0];
    rerender({ id: "agent-2" });
    expect(firstEs.close).toHaveBeenCalled();
    expect(MockEventSource.instances).toHaveLength(2);
    expect(MockEventSource.instances[1].url).toContain("/agents/agent-2/events");
  });
});
