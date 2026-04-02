import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { DashboardShell } from "@/components/dashboard-shell";
import { render } from "../../helpers/render";
import { mockReplace } from "../../setup";
import { http, HttpResponse } from "msw";
import { server } from "../../mocks/server";
import { mockAccount } from "../../mocks/fixtures";

describe("DashboardShell", () => {
  describe("authenticated", () => {
    beforeEach(() => {
      server.use(
        http.get("/api/v1/me", () =>
          HttpResponse.json(mockAccount()),
        ),
      );
    });

    it("renders desktop sidebar with nav items", async () => {
      render(
        <DashboardShell>
          <div>content</div>
        </DashboardShell>,
      );
      expect(await screen.findByText("content")).toBeInTheDocument();
      // Desktop sidebar nav links
      const homeLinks = screen.getAllByText("Home");
      expect(homeLinks.length).toBeGreaterThanOrEqual(1);
      const settingsLinks = screen.getAllByText("Settings");
      expect(settingsLinks.length).toBeGreaterThanOrEqual(1);
    });

    it("shows user email", async () => {
      render(
        <DashboardShell>
          <div>test</div>
        </DashboardShell>,
      );
      expect(
        await screen.findByText("test@example.com"),
      ).toBeInTheDocument();
    });

    it("shows logout button", async () => {
      render(
        <DashboardShell>
          <div>test</div>
        </DashboardShell>,
      );
      await screen.findByText("test@example.com");
      const logoutBtns = screen.getAllByText("Logout");
      expect(logoutBtns.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe("unauthenticated", () => {
    beforeEach(() => {
      server.use(
        http.get("/api/v1/me", () =>
          HttpResponse.json({ detail: "Unauthorized" }, { status: 401 }),
        ),
      );
    });

    it("redirects to signin", async () => {
      render(
        <DashboardShell>
          <div>content</div>
        </DashboardShell>,
      );
      // Wait for redirect
      await vi.waitFor(() => {
        expect(mockReplace).toHaveBeenCalledWith("/auth/signin");
      });
    });
  });
});
