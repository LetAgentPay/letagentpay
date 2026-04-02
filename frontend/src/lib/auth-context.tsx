"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { AccountResponse } from "@/lib/types";
import { identify, resetAnalytics } from "@/lib/ee-hooks";

interface AuthContextValue {
  account: AccountResponse | null;
  loading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  currency: string;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  account: null,
  loading: true,
  isAuthenticated: false,
  isAdmin: false,
  currency: "USD",
  logout: async () => {},
  refresh: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [account, setAccount] = useState<AccountResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const refresh = useCallback(async () => {
    try {
      const data = await api.getMe();
      setAccount(data);
      identify(data.id, { email: data.email, plan: data.plan });
    } catch {
      setAccount(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const logout = useCallback(async () => {
    await api.logout();
    localStorage.removeItem("agent_id");
    setAccount(null);
    resetAnalytics();
    router.replace("/auth/signin");
  }, [router]);

  return (
    <AuthContext.Provider
      value={{
        account,
        loading,
        isAuthenticated: !!account,
        isAdmin: !!account?.is_admin,
        currency: account?.currency ?? "USD",
        logout,
        refresh,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
