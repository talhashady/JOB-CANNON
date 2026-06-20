"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2, LogIn, UserPlus, Sparkles } from "lucide-react";
import { useAuth } from "@/lib/auth";

const backdrop = { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 } };
const panel = {
  initial: { y: 24, opacity: 0, scale: 0.98 },
  animate: { y: 0, opacity: 1, scale: 1 },
  exit: { y: 24, opacity: 0, scale: 0.98 },
  transition: { duration: 0.25, ease: "easeOut" },
};

export default function AuthModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { signin, signup } = useAuth();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") await signin(email, password);
      else await signup(email, password, fullName);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  const inputCls =
    "w-full rounded-xl border border-white/10 bg-ink-950/60 p-3 text-sm text-white/90 outline-none transition-colors focus:border-neon-violet/60";

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          {...backdrop}
          className="fixed inset-0 z-[100] grid place-items-center bg-black/70 p-4 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            {...panel}
            onClick={(e) => e.stopPropagation()}
            className="glass-strong relative w-full max-w-md rounded-2xl p-7 shadow-glow"
          >
            <button
              onClick={onClose}
              className="absolute right-4 top-4 text-white/50 transition-colors hover:text-white"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="mb-6 flex items-center gap-2">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-neon-violet to-neon-cyan shadow-glow">
                <Sparkles className="h-4 w-4 text-white" />
              </span>
              <h3 className="font-display text-xl font-bold">
                {mode === "login" ? "Welcome back" : "Create your account"}
              </h3>
            </div>

            <form onSubmit={submit} className="space-y-3">
              {mode === "signup" && (
                <input
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Full name"
                  className={inputCls}
                />
              )}
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@email.com"
                className={inputCls}
              />
              <input
                type="password"
                required
                minLength={mode === "signup" ? 8 : 1}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === "signup" ? "Password (min 8 chars)" : "Password"}
                className={inputCls}
              />

              {error && (
                <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-200">
                  {error}
                </p>
              )}

              <button type="submit" disabled={busy} className="btn-glow w-full disabled:opacity-60">
                {busy ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> Please wait...
                  </>
                ) : mode === "login" ? (
                  <>
                    <LogIn className="h-4 w-4" /> Sign in
                  </>
                ) : (
                  <>
                    <UserPlus className="h-4 w-4" /> Create account
                  </>
                )}
              </button>
            </form>

            <p className="mt-5 text-center text-sm text-white/50">
              {mode === "login" ? "New here?" : "Already have an account?"}{" "}
              <button
                onClick={() => {
                  setError(null);
                  setMode(mode === "login" ? "signup" : "login");
                }}
                className="font-semibold text-neon-cyan hover:underline"
              >
                {mode === "login" ? "Create an account" : "Sign in"}
              </button>
            </p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
