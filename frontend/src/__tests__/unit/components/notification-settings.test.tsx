import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderPlain } from "../../helpers/render";
import { NotificationSettings } from "@/components/notification-settings";
import { http, HttpResponse } from "msw";
import { server } from "../../mocks/server";
import type { NotificationChannelResponse } from "@/lib/types";

const API = "/api/v1";

function mockChannel(
  overrides?: Partial<NotificationChannelResponse>,
): NotificationChannelResponse {
  return {
    channel_type: "email",
    is_enabled: true,
    priority: 10,
    verified: true,
    config: {},
    ...overrides,
  };
}

describe("NotificationSettings", () => {
  beforeEach(() => {
    // Default: no channels configured
    server.use(
      http.get(`${API}/me/notifications/channels`, () =>
        HttpResponse.json([]),
      ),
    );
  });

  it("renders notification card", async () => {
    renderPlain(<NotificationSettings />);
    expect(screen.getByText("Notifications")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Email")).toBeInTheDocument();
    });
  });

  it("shows enable button for unconfigured email", async () => {
    renderPlain(<NotificationSettings />);
    await waitFor(() => {
      expect(screen.getByText("Enable")).toBeInTheDocument();
    });
  });

  it("shows connect button for Telegram", async () => {
    renderPlain(<NotificationSettings />);
    await waitFor(() => {
      expect(screen.getByText("Connect")).toBeInTheDocument();
    });
  });

  it("shows on/off toggle for configured channel", async () => {
    server.use(
      http.get(`${API}/me/notifications/channels`, () =>
        HttpResponse.json([mockChannel()]),
      ),
    );
    renderPlain(<NotificationSettings />);
    await waitFor(() => {
      expect(screen.getByText("On")).toBeInTheDocument();
    });
  });

  it("shows Connected badge for verified channel", async () => {
    server.use(
      http.get(`${API}/me/notifications/channels`, () =>
        HttpResponse.json([mockChannel({ verified: true })]),
      ),
    );
    renderPlain(<NotificationSettings />);
    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });
  });

  it("shows Telegram username when connected", async () => {
    server.use(
      http.get(`${API}/me/notifications/channels`, () =>
        HttpResponse.json([
          mockChannel({
            channel_type: "telegram",
            config: { username: "testuser" },
          }),
        ]),
      ),
    );
    renderPlain(<NotificationSettings />);
    await waitFor(() => {
      expect(screen.getByText(/testuser/)).toBeInTheDocument();
    });
  });
});
