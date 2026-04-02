import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { toast } from "sonner";
import SettingsPage from "@/app/dashboard/settings/page";
import { AuthProvider } from "@/lib/auth-context";
import { server } from "../../mocks/server";
import { mockBudgetRule } from "../../mocks/fixtures";

const API = "/api/v1";

function renderSettings() {
  return render(
    <AuthProvider>
      <SettingsPage />
    </AuthProvider>,
  );
}

describe("SettingsPage", () => {
  it("shows spinner when account not loaded", () => {
    server.use(
      http.get("/api/v1/me", async () => {
        await new Promise((r) => setTimeout(r, 5000));
        return HttpResponse.json({});
      }),
    );
    renderSettings();
    expect(screen.queryByText("Settings")).not.toBeInTheDocument();
  });

  it("populates form from account data", async () => {
    renderSettings();
    await waitFor(() =>
      expect(screen.getByDisplayValue("Test User")).toBeInTheDocument(),
    );
    expect(screen.getByDisplayValue("USD")).toBeInTheDocument();
    expect(screen.getByDisplayValue("America/New_York")).toBeInTheDocument();
  });

  it("email field is disabled", async () => {
    renderSettings();
    await waitFor(() =>
      expect(screen.getByDisplayValue("test@example.com")).toBeInTheDocument(),
    );
    expect(screen.getByDisplayValue("test@example.com")).toBeDisabled();
  });

  it("submitting calls updateMe and shows toast", async () => {
    const user = userEvent.setup();
    renderSettings();
    await waitFor(() =>
      expect(screen.getByDisplayValue("Test User")).toBeInTheDocument(),
    );
    const nameInput = screen.getByDisplayValue("Test User");
    await user.clear(nameInput);
    await user.type(nameInput, "New Name");
    await user.click(screen.getByText("Save"));
    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith("Settings saved"),
    );
  });

  it("shows error toast on failure", async () => {
    const user = userEvent.setup();
    server.use(
      http.put("/api/v1/me", () =>
        HttpResponse.json({ detail: "Invalid data" }, { status: 400 }),
      ),
    );
    renderSettings();
    await waitFor(() =>
      expect(screen.getByDisplayValue("Test User")).toBeInTheDocument(),
    );
    await user.click(screen.getByText("Save"));
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("Invalid data"),
    );
  });

  it("shows generic error toast on network failure", async () => {
    const user = userEvent.setup();
    server.use(
      http.put("/api/v1/me", () => HttpResponse.error()),
    );
    renderSettings();
    await waitFor(() =>
      expect(screen.getByDisplayValue("Test User")).toBeInTheDocument(),
    );
    await user.click(screen.getByText("Save"));
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("Failed to save"),
    );
  });

  it("shows Saving... while submitting", async () => {
    const user = userEvent.setup();
    server.use(
      http.put("/api/v1/me", async () => {
        await new Promise((r) => setTimeout(r, 100));
        return HttpResponse.json({});
      }),
    );
    renderSettings();
    await waitFor(() =>
      expect(screen.getByDisplayValue("Test User")).toBeInTheDocument(),
    );
    await user.click(screen.getByText("Save"));
    expect(screen.getByText("Saving...")).toBeInTheDocument();
  });

  it("populates request expiry minutes", async () => {
    renderSettings();
    await waitFor(() =>
      expect(screen.getByDisplayValue("30")).toBeInTheDocument(),
    );
    expect(
      screen.getByText(/Pending requests expire after this time/),
    ).toBeInTheDocument();
  });

  it("logout button is present", async () => {
    renderSettings();
    await waitFor(() =>
      expect(screen.getByText("Log out")).toBeInTheDocument(),
    );
  });

  describe("budget rules", () => {
    it("shows budget rules section", async () => {
      renderSettings();
      expect(
        await screen.findByText("Account Budget Rules"),
      ).toBeInTheDocument();
    });

    it("renders existing budget rules", async () => {
      renderSettings();
      expect(await screen.findByText("Daily Limit")).toBeInTheDocument();
      expect(screen.getByText(/Limit: \$200\.00/)).toBeInTheDocument();
      expect(screen.getByText(/Spent: \$50\.00/)).toBeInTheDocument();
    });

    it("shows empty state when no rules exist", async () => {
      server.use(
        http.get(`${API}/me/budget/rules`, () =>
          HttpResponse.json([]),
        ),
      );
      renderSettings();
      expect(
        await screen.findByText(/No budget rules yet/),
      ).toBeInTheDocument();
    });

    it("shows Add Rule button that toggles form", async () => {
      const user = userEvent.setup();
      renderSettings();
      const addBtn = await screen.findByText("Add Rule");
      await user.click(addBtn);
      expect(screen.getByPlaceholderText("e.g. Weekday limit")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("200.00")).toBeInTheDocument();
    });

    it("creates a new budget rule", async () => {
      const user = userEvent.setup();
      renderSettings();
      const addBtn = await screen.findByText("Add Rule");
      await user.click(addBtn);
      await user.type(screen.getByPlaceholderText("e.g. Weekday limit"), "Weekly Cap");
      await user.type(screen.getByPlaceholderText("200.00"), "500");
      await user.click(screen.getByText("Create"));
      await waitFor(() =>
        expect(toast.success).toHaveBeenCalledWith("Budget rule created"),
      );
    });

    it("shows error toast on create failure", async () => {
      const user = userEvent.setup();
      server.use(
        http.post(`${API}/me/budget/rules`, () =>
          HttpResponse.json({ detail: "Limit exceeded" }, { status: 400 }),
        ),
      );
      renderSettings();
      const addBtn = await screen.findByText("Add Rule");
      await user.click(addBtn);
      await user.type(screen.getByPlaceholderText("e.g. Weekday limit"), "Bad Rule");
      await user.type(screen.getByPlaceholderText("200.00"), "999999");
      await user.click(screen.getByText("Create"));
      await waitFor(() =>
        expect(toast.error).toHaveBeenCalledWith("Limit exceeded"),
      );
    });

    it("cancel hides create form", async () => {
      const user = userEvent.setup();
      renderSettings();
      const addBtn = await screen.findByText("Add Rule");
      await user.click(addBtn);
      expect(screen.getByPlaceholderText("e.g. Weekday limit")).toBeInTheDocument();
      // Find the Cancel button inside the form
      const cancelBtns = screen.getAllByText("Cancel");
      await user.click(cancelBtns[cancelBtns.length - 1]);
      expect(screen.queryByPlaceholderText("e.g. Weekday limit")).not.toBeInTheDocument();
    });

    it("toggles rule active state", async () => {
      const user = userEvent.setup();
      renderSettings();
      const disableBtn = await screen.findByText("Disable");
      await user.click(disableBtn);
      // After toggle, rules reload
      await waitFor(() =>
        expect(screen.getByText("Daily Limit")).toBeInTheDocument(),
      );
    });

    it("shows error on toggle failure", async () => {
      const user = userEvent.setup();
      server.use(
        http.put(`${API}/me/budget/rules/:id`, () =>
          HttpResponse.json({ detail: "Update failed" }, { status: 400 }),
        ),
      );
      renderSettings();
      const disableBtn = await screen.findByText("Disable");
      await user.click(disableBtn);
      await waitFor(() =>
        expect(toast.error).toHaveBeenCalledWith("Update failed"),
      );
    });

    it("deletes a rule and shows toast", async () => {
      const user = userEvent.setup();
      renderSettings();
      // Wait for the rule to load
      await screen.findByText("Daily Limit");
      // The delete button is next to the Disable button in the rule row
      // Find all buttons and pick the one that is not Disable/Enable/Add Rule/Save/Log out/Cancel
      const allButtons = screen.getAllByRole("button");
      const deleteBtn = allButtons.find(
        (b) => !b.textContent?.trim() || b.innerHTML.includes("text-destructive"),
      );
      expect(deleteBtn).toBeDefined();
      await user.click(deleteBtn!);
      await waitFor(() =>
        expect(toast.success).toHaveBeenCalledWith("Rule deleted"),
      );
    });

    it("shows error on delete failure", async () => {
      const user = userEvent.setup();
      server.use(
        http.delete(`${API}/me/budget/rules/:id`, () =>
          HttpResponse.json({ detail: "Cannot delete" }, { status: 400 }),
        ),
      );
      renderSettings();
      await screen.findByText("Daily Limit");
      const allButtons = screen.getAllByRole("button");
      const deleteBtn = allButtons.find(
        (b) => !b.textContent?.trim() || b.innerHTML.includes("text-destructive"),
      );
      await user.click(deleteBtn!);
      await waitFor(() =>
        expect(toast.error).toHaveBeenCalledWith("Cannot delete"),
      );
    });

    it("renders rule with days of week", async () => {
      server.use(
        http.get(`${API}/me/budget/rules`, () =>
          HttpResponse.json([
            mockBudgetRule({
              name: "Weekday Only",
              days_of_week: [0, 1, 2, 3, 4],
              priority: 2,
            }),
          ]),
        ),
      );
      renderSettings();
      expect(await screen.findByText("Weekday Only")).toBeInTheDocument();
      expect(screen.getByText(/Days: Mon, Tue, Wed, Thu, Fri/)).toBeInTheDocument();
      expect(screen.getByText("p2")).toBeInTheDocument();
    });

    it("renders disabled rule with Enable button", async () => {
      server.use(
        http.get(`${API}/me/budget/rules`, () =>
          HttpResponse.json([
            mockBudgetRule({ is_active: false }),
          ]),
        ),
      );
      renderSettings();
      expect(await screen.findByText("Enable")).toBeInTheDocument();
      expect(screen.getByText("disabled")).toBeInTheDocument();
    });

    it("day-of-week buttons toggle in create form", async () => {
      const user = userEvent.setup();
      renderSettings();
      const addBtn = await screen.findByText("Add Rule");
      await user.click(addBtn);
      // Click Mon and Wed
      const monBtn = screen.getByText("Mon");
      const wedBtn = screen.getByText("Wed");
      await user.click(monBtn);
      await user.click(wedBtn);
      // They should be highlighted (primary class)
      expect(monBtn.className).toContain("bg-primary");
      expect(wedBtn.className).toContain("bg-primary");
      // Click Mon again to deselect
      await user.click(monBtn);
      expect(monBtn.className).toContain("bg-muted");
    });
  });
});
