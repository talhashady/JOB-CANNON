"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Play, Sparkles, AlertCircle, Upload } from "lucide-react";
import { api } from "@/lib/api";
import type { PipelineResult } from "@/lib/types";
import AgentFlow from "./AgentFlow";
import JobResultCard from "./JobResultCard";

const SAMPLE_CV =
  "Backend engineer with 4 years of experience building Python microservices.\n" +
  "Skills: python, fastapi, docker, postgresql, redis, aws, sql, git, linux.\n" +
  "Built REST APIs with FastAPI and PostgreSQL; containerized services with Docker on AWS.";

const SITES = ["indeed", "linkedin", "glassdoor", "google", "zip_recruiter"];

const results = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};

export default function PipelineRunner() {
  const [cv, setCv] = useState(SAMPLE_CV);
  const [goals, setGoals] = useState("Grow into a senior platform engineering role.");
  const [query, setQuery] = useState("python developer");
  const [location, setLocation] = useState("Remote");
  const [sites, setSites] = useState<string[]>(["indeed"]);
  const [remote, setRemote] = useState(true);
  const [topK, setTopK] = useState(5);

  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PipelineResult | null>(null);

  const userId = "web-user";

  function toggleSite(s: string) {
    setSites((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));
  }

  async function run() {
    setLoading(true);
    setError(null);
    setResult(null);
    setStep(0);
    // Optimistic stepper animation while the request is in flight.
    const timers = [1, 2, 3, 4, 5, 6, 7, 8].map((n, i) =>
      setTimeout(() => setStep(n), 350 * (i + 1))
    );
    try {
      await api.createProfile(userId, cv, goals);
      const res = await api.run({
        user_id: userId,
        query,
        location,
        sites: sites.length ? sites : ["indeed"],
        results_wanted: 25,
        is_remote: remote,
        top_k: topK,
        auto_apply: true,
      });
      setResult(res);
      setStep(9);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      timers.forEach(clearTimeout);
      setLoading(false);
    }
  }

  return (
    <section id="run" className="relative mx-auto max-w-5xl px-4 py-28">
      <div className="mb-12 text-center">
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-neon-fuchsia">Live demo</p>
        <h2 className="font-display text-4xl font-bold sm:text-5xl">Run your pipeline</h2>
        <p className="mx-auto mt-4 max-w-xl text-white/60">
          Paste a CV, describe the role, and watch nine agents do the work.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* CV + goals */}
        <div className="glass-strong rounded-2xl p-6">
          <label className="mb-2 flex items-center gap-2 text-sm font-semibold text-white/80">
            <Upload className="h-4 w-4 text-neon-cyan" /> Your CV
          </label>
          <textarea
            value={cv}
            onChange={(e) => setCv(e.target.value)}
            rows={7}
            className="w-full resize-none rounded-xl border border-white/10 bg-ink-950/60 p-3 text-sm text-white/90 outline-none transition-colors focus:border-neon-violet/60"
            placeholder="Paste your resume text..."
          />
          <label className="mb-2 mt-4 block text-sm font-semibold text-white/80">Career goals</label>
          <input
            value={goals}
            onChange={(e) => setGoals(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-ink-950/60 p-3 text-sm text-white/90 outline-none transition-colors focus:border-neon-violet/60"
          />
        </div>

        {/* search params */}
        <div className="glass-strong rounded-2xl p-6">
          <label className="mb-2 block text-sm font-semibold text-white/80">Role / keywords</label>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-ink-950/60 p-3 text-sm text-white/90 outline-none focus:border-neon-violet/60"
          />
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div>
              <label className="mb-2 block text-sm font-semibold text-white/80">Location</label>
              <input
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-ink-950/60 p-3 text-sm text-white/90 outline-none focus:border-neon-violet/60"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-white/80">Top matches: {topK}</label>
              <input
                type="range"
                min={1}
                max={10}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="mt-3 w-full accent-neon-fuchsia"
              />
            </div>
          </div>
          <label className="mb-2 mt-4 block text-sm font-semibold text-white/80">Job boards</label>
          <div className="flex flex-wrap gap-2">
            {SITES.map((s) => (
              <button
                key={s}
                onClick={() => toggleSite(s)}
                className={
                  "rounded-full px-3 py-1.5 text-xs font-medium transition-colors " +
                  (sites.includes(s)
                    ? "bg-gradient-to-r from-neon-violet to-neon-cyan text-white"
                    : "glass text-white/60 hover:text-white")
                }
              >
                {s.replace(/_/g, " ")}
              </button>
            ))}
          </div>
          <label className="mt-4 flex cursor-pointer items-center gap-2 text-sm text-white/80">
            <input
              type="checkbox"
              checked={remote}
              onChange={(e) => setRemote(e.target.checked)}
              className="h-4 w-4 accent-neon-cyan"
            />
            Remote only
          </label>
        </div>
      </div>

      <div className="mt-8 flex flex-col items-center gap-6">
        <button onClick={run} disabled={loading} className="btn-glow min-w-[220px] disabled:opacity-60">
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" /> Agents working...
            </>
          ) : (
            <>
              <Play className="h-4 w-4" /> Run pipeline
            </>
          )}
        </button>

        {(loading || result) && (
          <div className="w-full max-w-3xl glass rounded-2xl p-5">
            <AgentFlow active={step} />
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            <AlertCircle className="h-4 w-4" /> {error}
            <span className="text-red-300/70">· Is the API URL set and the backend awake?</span>
          </div>
        )}
      </div>

      <AnimatePresence>
        {result && (
          <motion.div
            variants={results}
            initial="hidden"
            animate="show"
            className="mt-10 space-y-4"
          >
            <div className="flex flex-wrap items-center justify-center gap-6 text-center text-sm text-white/60">
              <Stat label="Scraped" value={result.jobs_scraped} />
              <Stat label="Verified" value={result.jobs_verified} />
              <Stat label="Top matches" value={result.recommendations.length} />
              <Stat label="Time" value={`${result.elapsed_s}s`} />
            </div>
            {result.recommendations.map((rec, i) => (
              <JobResultCard key={rec.job.id} rec={rec} index={i} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center gap-2">
      <Sparkles className="h-4 w-4 text-neon-cyan" />
      <span className="font-display text-xl font-bold text-white">{value}</span>
      <span>{label}</span>
    </div>
  );
}
