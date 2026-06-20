"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Sparkles, LayoutDashboard, LogIn, LogOut } from "lucide-react";
import { useAuth } from "@/lib/auth";
import AuthModal from "./AuthModal";

const enter = {
  initial: { y: -24, opacity: 0 },
  animate: { y: 0, opacity: 1 },
  transition: { duration: 0.6, ease: "easeOut" },
};

export default function Navbar() {
  const { user, signout } = useAuth();
  const [authOpen, setAuthOpen] = useState(false);

  return (
    <>
      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />
      <motion.header
        {...enter}
        className="fixed inset-x-0 top-0 z-50 flex justify-center px-4 pt-4"
      >
        <nav className="glass-strong flex w-full max-w-5xl items-center justify-between rounded-full px-5 py-3 shadow-glow">
          <a href="#top" className="flex items-center gap-2 font-display text-lg font-bold">
            <span className="grid h-8 w-8 place-items-center rounded-xl bg-gradient-to-br from-neon-violet to-neon-cyan shadow-glow">
              <Sparkles className="h-4 w-4 text-white" />
            </span>
            <span className="text-gradient">CareerOS</span>
          </a>
          <div className="hidden items-center gap-8 text-sm text-white/70 md:flex">
            <a href="#how" className="transition-colors hover:text-white">How it works</a>
            <a href="#agents" className="transition-colors hover:text-white">Agents</a>
            <a href="#run" className="transition-colors hover:text-white">Try it</a>
            <Link href="/dashboard" className="inline-flex items-center gap-1.5 transition-colors hover:text-white">
              <LayoutDashboard className="h-4 w-4" /> Dashboard
            </Link>
          </div>
          {user ? (
            <div className="flex items-center gap-3">
              <span className="hidden text-sm text-white/60 sm:inline">{user.full_name || user.email}</span>
              <button onClick={signout} className="btn-ghost !px-4 !py-2">
                <LogOut className="h-4 w-4" /> Sign out
              </button>
            </div>
          ) : (
            <button onClick={() => setAuthOpen(true)} className="btn-glow !px-5 !py-2">
              <LogIn className="h-4 w-4" /> Sign in
            </button>
          )}
        </nav>
      </motion.header>
    </>
  );
}
