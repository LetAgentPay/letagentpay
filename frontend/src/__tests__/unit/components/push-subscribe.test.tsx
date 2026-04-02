import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../../mocks/server";

// Must mock auth-context before importing component
vi.mock("@/lib/auth-context", () => ({
  useAuth: vi.fn(() => ({ isAuthenticated: false })),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

import { useAuth } from "@/lib/auth-context";
import { PushSubscribe } from "@/components/push-subscribe";

const API = "/api/v1";

const mockSubscription = {
  toJSON: () => ({
    endpoint: "https://push.example.com/sub/abc",
    keys: { p256dh: "test-p256dh", auth: "test-auth" },
  }),
};

const mockGetSubscription = vi.fn().mockResolvedValue(null);
const mockPushSubscribe = vi.fn().mockResolvedValue(mockSubscription);

function setupNotification(permission: NotificationPermission = "default") {
  // @ts-expect-error - jsdom doesn't have Notification
  globalThis.Notification = class {
    static permission = permission;
    static requestPermission = vi.fn().mockResolvedValue("granted");
  };
}

function setupPushManager() {
  Object.defineProperty(window, "PushManager", { value: class {}, configurable: true });
  Object.defineProperty(navigator, "serviceWorker", {
    value: {
      register: vi.fn(),
      ready: Promise.resolve({
        pushManager: {
          getSubscription: mockGetSubscription,
          subscribe: mockPushSubscribe,
        },
      }),
    },
    configurable: true,
    writable: true,
  });
}

describe("PushSubscribe", () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      account: null,
      loading: false,
      isAuthenticated: false,
      isAdmin: false,
      logout: vi.fn(),
      refresh: vi.fn(),
    });
    mockGetSubscription.mockClear().mockResolvedValue(null);
    mockPushSubscribe.mockClear().mockResolvedValue(mockSubscription);
    setupPushManager();
    setupNotification();

    server.use(
      http.get(`${API}/push/vapid-key`, () =>
        HttpResponse.json({ vapid_public_key: "test-vapid-key" }),
      ),
      http.post(`${API}/push/subscribe`, () =>
        HttpResponse.json({ message: "Subscribed" }),
      ),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nothing", () => {
    const { container } = render(<PushSubscribe />);
    expect(container.innerHTML).toBe("");
  });

  it("does not subscribe when not authenticated", async () => {
    render(<PushSubscribe />);
    await act(() => new Promise((r) => setTimeout(r, 50)));
    expect(mockPushSubscribe).not.toHaveBeenCalled();
  });

  it("subscribes to push when authenticated and permission granted", async () => {
    vi.mocked(useAuth).mockReturnValue({
      account: { id: "acc-1" } as never,
      loading: false,
      isAuthenticated: true,
      isAdmin: false,
      logout: vi.fn(),
      refresh: vi.fn(),
    });
    Notification.requestPermission = vi.fn().mockResolvedValue("granted");

    render(<PushSubscribe />);
    await act(() => new Promise((r) => setTimeout(r, 100)));

    expect(mockPushSubscribe).toHaveBeenCalledWith({
      userVisibleOnly: true,
      applicationServerKey: expect.any(Uint8Array),
    });
  });

  it("does not subscribe when permission denied", async () => {
    vi.mocked(useAuth).mockReturnValue({
      account: { id: "acc-1" } as never,
      loading: false,
      isAuthenticated: true,
      isAdmin: false,
      logout: vi.fn(),
      refresh: vi.fn(),
    });
    Notification.requestPermission = vi.fn().mockResolvedValue("denied");

    render(<PushSubscribe />);
    await act(() => new Promise((r) => setTimeout(r, 100)));

    expect(mockPushSubscribe).not.toHaveBeenCalled();
  });

  it("reuses existing browser subscription and sends to backend", async () => {
    vi.mocked(useAuth).mockReturnValue({
      account: { id: "acc-1" } as never,
      loading: false,
      isAuthenticated: true,
      isAdmin: false,
      logout: vi.fn(),
      refresh: vi.fn(),
    });
    mockGetSubscription.mockResolvedValue(mockSubscription);

    let backendCalled = false;
    server.use(
      http.post(`${API}/push/subscribe`, () => {
        backendCalled = true;
        return HttpResponse.json({ message: "Subscribed" });
      }),
    );

    render(<PushSubscribe />);
    await act(() => new Promise((r) => setTimeout(r, 100)));

    // Should NOT create new browser subscription
    expect(mockPushSubscribe).not.toHaveBeenCalled();
    // Should still notify backend (upsert)
    expect(backendCalled).toBe(true);
  });
});
