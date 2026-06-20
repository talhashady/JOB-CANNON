"use client";

/**
 * Auth context: holds the signed-in user + JWT, persists the token in localStorage,
 * and exposes signin/signup/signout. Wrap the app with <AuthProvider> in app/layout.tsx.
 */
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api } from "./api";
import type { PublicUser } from "./types";

interface AuthContextValue {
  user: PublicUser | null;
  loading: boolean;
  signin: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, fullName: string) => Promise<void>;
  signout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<PublicUser | null>(null);
  const [loading, setLoading] = useState(true);

  // On mount, if we have a stored token, resolve the current user.
  useEffect(() => {
    let cancelled = false;
    const token = api.getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then((u) => {
        if (!cancelled) setUser(u);
      })
      .catch(() => {
        api.clearToken();
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const signin = useCallback(async (email: string, password: string) => {
    const res = await api.login({ email, password });
    api.setToken(res.access_token);
    setUser(res.user);
  }, []);

  const signup = useCallback(
    async (email: string, password: string, fullName: string) => {
      const res = await api.signup({ email, password, full_name: fullName });
      api.setToken(res.access_token);
      setUser(res.user);
    },
    []
  );

  const signout = useCallback(() => {
    api.clearToken();
    setUser(null);
  }, []);

  const value: AuthContextValue = { user, loading, signin, signup, signout };
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
