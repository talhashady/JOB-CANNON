"use client";

/**
 * Auth context: holds the signed-in user (resolved via HttpOnly cookie on mount),
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
  const [wakingUp, setWakingUp] = useState(false);

  // On mount, resolve the current user by calling /auth/me (using HttpOnly cookie).
  useEffect(() => {
    let cancelled = false;

    const timer = setTimeout(() => {
      if (!cancelled) setWakingUp(true);
    }, 3000);

    api
      .me()
      .then((u) => {
        if (!cancelled) setUser(u);
      })
      .catch(() => {
        api.clearToken();
      })
      .finally(() => {
        clearTimeout(timer);
        if (!cancelled) {
          setWakingUp(false);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  const signin = useCallback(async (email: string, password: string) => {
    const res = await api.login({ email, password });
    setUser(res.user);
  }, []);

  const signup = useCallback(
    async (email: string, password: string, fullName: string) => {
      const res = await api.signup({ email, password, full_name: fullName });
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
      {wakingUp && (
        <div className="fixed left-4 right-4 top-4 z-[9999] mx-auto max-w-md rounded-xl border border-neon-cyan/20 bg-black/80 p-4 text-center text-sm text-neon-cyan shadow-lg shadow-neon-cyan/10 backdrop-blur-md transition-all sm:left-auto sm:right-6 sm:top-6 sm:max-w-sm sm:text-left">
          <div className="flex items-center gap-3">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-neon-cyan border-t-transparent" />
            <p>Waking up the server, this can take up to 15 seconds...</p>
          </div>
        </div>
      )}
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
