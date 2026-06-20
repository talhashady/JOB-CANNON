"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { RefreshCw, LayoutDashboard, LogIn, ArrowLeft } from "lucide-react";
import Background from "@/components/Background";
import ApplicationsTable from "@/components/ApplicationsTable";
import AuthModal from "@/components/AuthModal";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import type { Application } from "@/lib/types";

const fadeIn = { initial: { opacity: 0, y: 12 }, animate: { opacity: 1, y: 0 } };

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="glass rounded-2xl px-5 py-4 text-center">
      <div className="font-display text-3xl font-bold text-gradient">{value}</div>
      <div className="mt-1 text-xs uppercase tracking-wider text-white/50">{label}</div>
    </div>
  );
}

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const [apps, setApps] = useState<Application[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authOpen, setAuthOpen] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      setApps(await api.applicationsMe());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load applications");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  const counts = {
    total: apps.length,
    sent: apps.filter((a) => a.status === "email_sent").length,
    dryRun: apps.filter((a) => a.status === "dry_run").length,
    noContact: apps.filter((a) => a.status === "no_contact").length,
  };

  return (
    <main className="relative min-h-screen">
      <Background />
      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />

      <div className="mx-auto max-w-6xl px-4 pb-24 pt-28">
        <div className="mb-10 flex flex-wrap items-end justify-between gap-4">
          <div>
            <Link href="/" className="mb-3 inline-flex items-center gap-1.5 text-sm text-white/50 hover:text-white">
              <ArrowLeft className="h-4 w-4" /> Back home
            </Link>
            <h1 className="flex items-center gap-3 font-display text-4xl font-bold">
              <LayoutDashboard className="h-8 w-8 text-neon-violet" /> Application Tracker
            </h1>
            <p className="mt-2 text-white/55">Every job your agents have applied to, in one place.</p>
          </div>
          {user && (
            <button onClick={load} disabled={busy} className="btn-ghost">
              <RefreshCw className={busy ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Refresh
            </button>
          )}
        </div>

        {!loading && !user && (
          <motion.div
            initial={fadeIn.initial}
            animate={fadeIn.animate}
            className="glass-strong rounded-2xl p-10 text-center"
          >
            <p className="mb-5 text-white/70">Sign in to view your application history.</p>
            <button onClick={() => setAuthOpen(true)} className="btn-glow">
              <LogIn className="h-4 w-4" /> Sign in
            </button>
          </motion.div>
        )}

        {user && (
          <>
            <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label="Total" value={counts.total} />
              <Stat label="Email sent" value={counts.sent} />
              <Stat label="Dry run" value={counts.dryRun} />
              <Stat label="No contact" value={counts.noContact} />
            </div>

            {error && (
              <p className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {error}
              </p>
            )}

            <ApplicationsTable applications={apps} />
          </>
        )}
      </div>
    </main>
  );
}
