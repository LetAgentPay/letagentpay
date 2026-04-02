import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import {
  track,
  identify,
  resetAnalytics,
  EEProvider,
  EESettingsSection,
  getEENavItems,
} from "@/lib/ee-hooks";
import { mockAccount } from "../../mocks/fixtures";

describe("ee-hooks", () => {
  it("track does not throw", () => {
    expect(() => track("event", { key: "value" })).not.toThrow();
  });

  it("identify does not throw", () => {
    expect(() => identify("user-1", { email: "test@example.com" })).not.toThrow();
  });

  it("resetAnalytics does not throw", () => {
    expect(() => resetAnalytics()).not.toThrow();
  });

  it("EEProvider renders children", () => {
    const { getByText } = render(
      <EEProvider>
        <span>child content</span>
      </EEProvider>,
    );
    expect(getByText("child content")).toBeInTheDocument();
  });

  it("EESettingsSection renders without error", () => {
    const { container } = render(
      <EESettingsSection
        account={mockAccount()}
        refresh={async () => {}}
      />,
    );
    // Core renders null; enterprise renders billing card — both are valid
    expect(container).toBeDefined();
  });

  it("getEENavItems returns array", () => {
    expect(Array.isArray(getEENavItems(false))).toBe(true);
    expect(getEENavItems(false)).toEqual([]);
    // isAdmin=true: core returns [], enterprise returns admin nav items — both are arrays
    const adminItems = getEENavItems(true);
    expect(Array.isArray(adminItems)).toBe(true);
  });
});
