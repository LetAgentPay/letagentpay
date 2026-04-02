"use client";

import { ReactNode } from "react";
import {
  PublicConfigContext,
  usePublicConfigLoader,
} from "@/lib/hooks/use-public-config";

export function PublicConfigProvider({ children }: { children: ReactNode }) {
  const config = usePublicConfigLoader();
  return (
    <PublicConfigContext.Provider value={config}>
      {children}
    </PublicConfigContext.Provider>
  );
}