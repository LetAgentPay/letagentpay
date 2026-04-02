import { describe, expect, it, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PWAInstallPrompt } from "@/components/pwa-install-prompt";

describe("PWAInstallPrompt", () => {
  it("renders nothing when no beforeinstallprompt event", () => {
    const { container } = render(<PWAInstallPrompt />);
    expect(container.innerHTML).toBe("");
  });

  it("renders install banner when beforeinstallprompt fires", () => {
    render(<PWAInstallPrompt />);

    act(() => {
      const event = new Event("beforeinstallprompt", {
        cancelable: true,
      });
      Object.assign(event, {
        prompt: vi.fn().mockResolvedValue(undefined),
        userChoice: Promise.resolve({ outcome: "dismissed" as const }),
      });
      window.dispatchEvent(event);
    });

    expect(screen.getByText("Install LetAgentPay")).toBeInTheDocument();
    expect(screen.getByText("Install")).toBeInTheDocument();
  });

  it("dismiss button hides banner and sets localStorage", async () => {
    const user = userEvent.setup();
    render(<PWAInstallPrompt />);

    act(() => {
      const event = new Event("beforeinstallprompt", { cancelable: true });
      Object.assign(event, {
        prompt: vi.fn().mockResolvedValue(undefined),
        userChoice: Promise.resolve({ outcome: "dismissed" as const }),
      });
      window.dispatchEvent(event);
    });

    expect(screen.getByText("Install LetAgentPay")).toBeInTheDocument();

    await user.click(screen.getByLabelText("Dismiss"));

    expect(screen.queryByText("Install LetAgentPay")).not.toBeInTheDocument();
    expect(localStorage.getItem("pwa-install-dismissed")).toBe("1");
  });

  it("install button calls prompt()", async () => {
    const user = userEvent.setup();
    const mockPrompt = vi.fn().mockResolvedValue(undefined);

    render(<PWAInstallPrompt />);

    act(() => {
      const event = new Event("beforeinstallprompt", { cancelable: true });
      Object.assign(event, {
        prompt: mockPrompt,
        userChoice: Promise.resolve({ outcome: "accepted" as const }),
      });
      window.dispatchEvent(event);
    });

    await user.click(screen.getByText("Install"));

    expect(mockPrompt).toHaveBeenCalled();
  });

  it("renders nothing when previously dismissed via localStorage", () => {
    localStorage.setItem("pwa-install-dismissed", "1");

    render(<PWAInstallPrompt />);

    act(() => {
      const event = new Event("beforeinstallprompt", { cancelable: true });
      Object.assign(event, {
        prompt: vi.fn().mockResolvedValue(undefined),
        userChoice: Promise.resolve({ outcome: "dismissed" as const }),
      });
      window.dispatchEvent(event);
    });

    expect(screen.queryByText("Install LetAgentPay")).not.toBeInTheDocument();
  });
});
