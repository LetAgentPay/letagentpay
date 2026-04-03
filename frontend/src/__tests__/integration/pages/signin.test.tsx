import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import SignInPage from "@/app/auth/signin/page";
import { server } from "../../mocks/server";
import { mockPush } from "../../setup";

describe("SignInPage", () => {
  it("renders email input and submit button", async () => {
    render(<SignInPage />);
    expect(await screen.findByPlaceholderText("you@example.com")).toBeInTheDocument();
    expect(screen.getByText("Send magic link")).toBeInTheDocument();
  });

  it("submitting calls sendLink and shows OTP input", async () => {
    const user = userEvent.setup();
    render(<SignInPage />);
    await user.type(
      await screen.findByPlaceholderText("you@example.com"),
      "test@example.com",
    );
    await user.click(screen.getByText("Send magic link"));
    expect(await screen.findByText("Check your email")).toBeInTheDocument();
    expect(screen.getByText(/test@example.com/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText("000000")).toBeInTheDocument();
    expect(screen.getByText("Verify code")).toBeInTheDocument();
  });

  it("shows 'Sending...' while loading", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/v1/auth/send-link", async () => {
        await new Promise((r) => setTimeout(r, 100));
        return HttpResponse.json({ message: "ok" });
      }),
    );
    render(<SignInPage />);
    await user.type(
      await screen.findByPlaceholderText("you@example.com"),
      "test@example.com",
    );
    await user.click(screen.getByText("Send magic link"));
    expect(screen.getByText("Sending...")).toBeInTheDocument();
  });

  it("shows error on API failure", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/v1/auth/send-link", () =>
        HttpResponse.json({ detail: "Rate limited" }, { status: 429 }),
      ),
    );
    render(<SignInPage />);
    await user.type(
      await screen.findByPlaceholderText("you@example.com"),
      "test@example.com",
    );
    await user.click(screen.getByText("Send magic link"));
    expect(await screen.findByText("Rate limited")).toBeInTheDocument();
  });

  it("shows generic error on network failure", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/v1/auth/send-link", () =>
        HttpResponse.error(),
      ),
    );
    render(<SignInPage />);
    await user.type(
      await screen.findByPlaceholderText("you@example.com"),
      "test@example.com",
    );
    await user.click(screen.getByText("Send magic link"));
    expect(
      await screen.findByText(/Connection error/),
    ).toBeInTheDocument();
  });

  it("renders password form in self-hosted mode", async () => {
    server.use(
      http.get("/api/v1/auth/mode", () =>
        HttpResponse.json({ mode: "password" }),
      ),
    );
    render(<SignInPage />);
    expect(await screen.findByPlaceholderText("Password")).toBeInTheDocument();
    expect(screen.getByText("Sign in")).toBeInTheDocument();
  });

  describe("OTP verification flow", () => {
    async function sendLinkAndGetOtpView() {
      const user = userEvent.setup();
      render(<SignInPage />);
      await user.type(
        await screen.findByPlaceholderText("you@example.com"),
        "test@example.com",
      );
      await user.click(screen.getByText("Send magic link"));
      await screen.findByText("Check your email");
      return user;
    }

    it("successful OTP verification redirects to dashboard", async () => {
      const user = await sendLinkAndGetOtpView();

      await user.type(screen.getByPlaceholderText("000000"), "123456");
      await user.click(screen.getByText("Verify code"));
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/dashboard");
      });
    });

    it("shows error on invalid OTP", async () => {
      server.use(
        http.post("/auth/verify-otp", () =>
          HttpResponse.json({ detail: "Invalid code" }, { status: 400 }),
        ),
      );
      const user = await sendLinkAndGetOtpView();

      await user.type(screen.getByPlaceholderText("000000"), "000000");
      await user.click(screen.getByText("Verify code"));
      expect(await screen.findByText("Invalid code")).toBeInTheDocument();
    });

    it("shows 'Verifying...' while loading", async () => {
      server.use(
        http.post("/auth/verify-otp", async () => {
          await new Promise((r) => setTimeout(r, 100));
          return HttpResponse.json({ message: "Authenticated" });
        }),
      );
      const user = await sendLinkAndGetOtpView();

      await user.type(screen.getByPlaceholderText("000000"), "123456");
      await user.click(screen.getByText("Verify code"));
      expect(screen.getByText("Verifying...")).toBeInTheDocument();
    });

    it("verify button is disabled until 6 digits entered", async () => {
      await sendLinkAndGetOtpView();
      expect(screen.getByText("Verify code")).toBeDisabled();
    });

    it("resend button sends new link", async () => {
      const user = await sendLinkAndGetOtpView();

      await user.click(screen.getByText("Resend code"));
      // Should still show the OTP view (not go back to email form)
      await waitFor(() => {
        expect(screen.getByPlaceholderText("000000")).toBeInTheDocument();
      });
    });
  });

  describe("password login flow", () => {
    it("successful password login redirects to dashboard", async () => {
      const user = userEvent.setup();
      server.use(
        http.get("/api/v1/auth/mode", () =>
          HttpResponse.json({ mode: "password" }),
        ),
      );
      render(<SignInPage />);
      await user.type(await screen.findByPlaceholderText("Password"), "secret123");
      await user.click(screen.getByText("Sign in"));
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/dashboard");
      });
    });

    it("shows 'Signing in...' while loading", async () => {
      const user = userEvent.setup();
      server.use(
        http.get("/api/v1/auth/mode", () =>
          HttpResponse.json({ mode: "password" }),
        ),
        http.post("/api/v1/auth/login", async () => {
          await new Promise((r) => setTimeout(r, 100));
          return HttpResponse.json({ message: "ok" });
        }),
      );
      render(<SignInPage />);
      await user.type(await screen.findByPlaceholderText("Password"), "secret");
      await user.click(screen.getByText("Sign in"));
      expect(screen.getByText("Signing in...")).toBeInTheDocument();
    });

    it("shows error on password login failure", async () => {
      const user = userEvent.setup();
      server.use(
        http.get("/api/v1/auth/mode", () =>
          HttpResponse.json({ mode: "password" }),
        ),
        http.post("/api/v1/auth/login", () =>
          HttpResponse.json({ detail: "Invalid password" }, { status: 401 }),
        ),
      );
      render(<SignInPage />);
      await user.type(await screen.findByPlaceholderText("Password"), "wrong");
      await user.click(screen.getByText("Sign in"));
      expect(await screen.findByText("Invalid password")).toBeInTheDocument();
    });

    it("shows generic error on password network failure", async () => {
      const user = userEvent.setup();
      server.use(
        http.get("/api/v1/auth/mode", () =>
          HttpResponse.json({ mode: "password" }),
        ),
        http.post("/api/v1/auth/login", () => HttpResponse.error()),
      );
      render(<SignInPage />);
      await user.type(await screen.findByPlaceholderText("Password"), "test");
      await user.click(screen.getByText("Sign in"));
      expect(await screen.findByText(/Connection error/)).toBeInTheDocument();
    });
  });

  it("falls back to magic_link when auth mode request fails", async () => {
    server.use(
      http.get("/api/v1/auth/mode", () => HttpResponse.error()),
    );
    render(<SignInPage />);
    // Should fall back to magic_link mode and show email input
    expect(await screen.findByPlaceholderText("you@example.com")).toBeInTheDocument();
  });
});
