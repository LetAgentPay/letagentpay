import { render as rtlRender, type RenderOptions } from "@testing-library/react";
import { AuthProvider } from "@/lib/auth-context";
import type { ReactElement } from "react";

function Providers({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

export function render(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  return rtlRender(ui, { wrapper: Providers, ...options });
}

export function renderPlain(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  return rtlRender(ui, options);
}
