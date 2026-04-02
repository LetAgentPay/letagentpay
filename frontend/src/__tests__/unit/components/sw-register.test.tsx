import { describe, expect, it, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import { ServiceWorkerRegister } from "@/components/sw-register";

describe("ServiceWorkerRegister", () => {
  const mockRegister = vi.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    mockRegister.mockClear();
    // Set up navigator.serviceWorker mock
    Object.defineProperty(navigator, "serviceWorker", {
      value: { register: mockRegister },
      configurable: true,
      writable: true,
    });
  });

  it("calls navigator.serviceWorker.register with /sw.js", () => {
    render(<ServiceWorkerRegister />);
    expect(mockRegister).toHaveBeenCalledWith("/sw.js");
  });

  it("renders nothing visually", () => {
    const { container } = render(<ServiceWorkerRegister />);
    expect(container.innerHTML).toBe("");
  });

  it("handles missing serviceWorker gracefully", () => {
    // Remove serviceWorker from navigator entirely
    const original = navigator.serviceWorker;
    // @ts-expect-error - intentionally deleting for test
    delete (navigator as Record<string, unknown>).serviceWorker;

    // Should not throw
    expect(() => render(<ServiceWorkerRegister />)).not.toThrow();

    // Restore
    Object.defineProperty(navigator, "serviceWorker", {
      value: original,
      configurable: true,
      writable: true,
    });
  });
});
