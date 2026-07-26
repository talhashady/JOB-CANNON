"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Play, Sparkles, AlertCircle, Upload, CheckSquare, Square, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import type { DiscoveryResult, PipelineResult, UserProfile } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { logStep, logSuccess } from "@/lib/logger";
import AgentFlow from "./AgentFlow";
import JobResultCard from "./JobResultCard";
import JobSelectCard from "./JobSelectCard";
import CvDropzone from "./CvDropzone";
import AuthModal from "./AuthModal";

const SITES = ["indeed", "linkedin", "glassdoor", "google", "zip_recruiter"];

type Arrangement = "any" | "remote" | "hybrid" | "onsite";
const WORK_ARRANGEMENTS: { value: Arrangement; label: string }[] = [
  { value: "any", label: "Any" },
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "onsite", label: "On-site" },
];

const PHASE1_STEPS = ["Scraper Agent", "Verification Agent", "Matching Agent"];
const PHASE2_STEPS = ["Resume Agent", "Cover Letter Agent", "Skill Gap Agent", "Interview Prep Agent", "Application Agent"];

const results = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};

function deriveGoals(p: UserProfile): string {
  const title = (p.titles && p.titles[0]) || p.headline || "my field";
  const years = p.years_experience ? `${p.years_experience}+ years` : "";
  const top = (p.skills || []).slice(0, 6).join(", ");
  const parts: string[] = [`Advance my career as a ${title}`];
  if (years) parts.push(`leveraging ${years} of experience`);
  if (top) parts.push(`with strengths in ${top}`);
  return parts.join(" ") + ".";
}

function parseCvTextClient(text: string) {
  if (!text || text.trim().length < 15) return null;
  const lower = text.toLowerCase();

  const titleMatches = [
    "full stack engineer", "fullstack developer", "full stack developer",
    "backend engineer", "backend developer", "frontend engineer", "frontend developer",
    "software engineer", "software developer", "python developer", "python engineer",
    "java developer", "react developer", "node.js developer", "node developer",
    "devops engineer", "cloud engineer", "data engineer", "data scientist",
    "data analyst", "product manager", "project manager", "qa engineer",
    "ui/ux designer", "machine learning engineer", "ai engineer", "system architect"
  ];

  let detectedTitle = "";
  for (const title of titleMatches) {
    if (lower.includes(title)) {
      detectedTitle = title;
      break;
    }
  }

  if (!detectedTitle) {
    const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
    for (const line of lines.slice(0, 5)) {
      if (/\b(engineer|developer|architect|analyst|specialist|manager|lead|consultant)\b/i.test(line) && line.length < 50) {
        detectedTitle = line.replace(/^(senior|junior|lead|principal|staff)\s+/i, "");
        break;
      }
    }
  }

  if (!detectedTitle) detectedTitle = "software engineer";

  const commonSkills = [
    "python", "javascript", "typescript", "react", "next.js", "node.js", "vue", "angular",
    "java", "c++", "c#", "go", "golang", "rust", "sql", "postgresql", "mysql", "mongodb",
    "redis", "docker", "kubernetes", "aws", "azure", "gcp", "fastapi", "django", "flask",
    "express", "tailwind", "html", "css", "git", "linux", "rest api", "graphql", "ci/cd"
  ];

  const foundSkills: string[] = [];
  for (const skill of commonSkills) {
    const regex = new RegExp(`\\b${skill.replace(".", "\\.")}\\b`, "i");
    if (regex.test(text)) {
      foundSkills.push(skill);
    }
  }

  const expMatch = text.match(/(\d+)\+?\s*(?:years?|yrs?)\b/i);
  const years = expMatch ? `${expMatch[1]}+ years` : "";

  const capitalizedTitle = detectedTitle.replace(/\b\w/g, (l) => l.toUpperCase());
  const topSkillsStr = foundSkills.slice(0, 5).join(", ");

  let generatedGoal = `Advance my career as a ${capitalizedTitle}`;
  if (years) generatedGoal += ` leveraging ${years} of experience`;
  if (topSkillsStr) generatedGoal += ` with strengths in ${topSkillsStr}`;
  generatedGoal += ".";

  return {
    title: detectedTitle,
    goals: generatedGoal,
    query: detectedTitle.toLowerCase(),
    skills: foundSkills,
  };
}

export default function PipelineRunner() {
  const { user } = useAuth();

  const [cv, setCv] = useState("");
  const [goals, setGoals] = useState("");
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("Remote");
  const [sites, setSites] = useState<string[]>(["indeed"]);
  const [workArrangement, setWorkArrangement] = useState<Arrangement>("remote");
  const [jobCount, setJobCount] = useState(80);
  const [topK, setTopK] = useState(10);
  const [autoApply, setAutoApply] = useState(false);

  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(0);
  const [phase, setPhase] = useState<"idle" | "discovering" | "selection" | "preparing" | "complete">("idle");
  const [error, setError] = useState<string | null>(null);

  // Phase 1 Discovery results & user selections
  const [discoveryResult, setDiscoveryResult] = useState<DiscoveryResult | null>(null);
  const [selectedJobIds, setSelectedJobIds] = useState<string[]>([]);

  // Phase 2 Final Pipeline recommendations
  const [result, setResult] = useState<PipelineResult | null>(null);

  const [authOpen, setAuthOpen] = useState(false);

  useEffect(() => {
    if (user) setError(null);
  }, [user]);

  function toggleSite(s: string) {
    setSites((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));
  }

  function applyParsedProfile(p: UserProfile) {
    const rawText = (p.raw_cv_text || p.summary || (p.skills && p.skills.length ? p.skills.join(", ") : "")).trim();
    if (rawText) {
      setCv(rawText);
    }

    // Populate Career Goals
    const goalsText = p.career_goals?.trim() || deriveGoals(p);
    if (goalsText) {
      setGoals(goalsText);
    }

    // Populate ONLY ONE single job title into the Role / keywords box
    let singleTitle = "";
    if (p.titles && p.titles.length > 0 && p.titles[0].trim()) {
      singleTitle = p.titles[0].trim();
    } else if (p.headline && p.headline.trim()) {
      singleTitle = p.headline.trim();
    }

    if (!singleTitle && rawText) {
      const parsed = parseCvTextClient(rawText);
      if (parsed && parsed.title) {
        singleTitle = parsed.title;
      }
    }

    if (singleTitle) {
      // Ensure strictly one job title by splitting on punctuation
      singleTitle = singleTitle.split(/[,|;]/)[0].trim();
    }

    if (!singleTitle) {
      singleTitle = "software engineer";
    }

    setQuery(singleTitle.toLowerCase());
    logSuccess(`CV uploaded: full text, goals, and primary role "${singleTitle}" populated`);
  }

  function toggleJobSelection(jobId: string) {
    setSelectedJobIds((prev) =>
      prev.includes(jobId) ? prev.filter((id) => id !== jobId) : [...prev, jobId]
    );
  }

  function toggleSelectAll() {
    if (!discoveryResult) return;
    const allIds = discoveryResult.matches.map((m) => m.job.id);
    if (selectedJobIds.length === allIds.length) {
      setSelectedJobIds([]);
    } else {
      setSelectedJobIds(allIds);
    }
  }

  // Helper for background task polling with 10 min max timeout (300 polls x 2s)
  async function pollUntilDone<T>(taskId: string): Promise<T> {
    let taskDone = false;
    let finalResult: T | null = null;
    const MAX_POLLS = 300; // 300 x 2s = 10 minutes max
    let pollCount = 0;

    while (!taskDone) {
      if (pollCount >= MAX_POLLS) {
        throw new Error("Pipeline timed out after 10 minutes. The server may have restarted — please try again.");
      }
      await new Promise((resolve) => setTimeout(resolve, 2000));
      pollCount++;
      const statusRes = await api.pollTask<T>(taskId);
      if (statusRes.status === "done") {
        finalResult = statusRes.result;
        taskDone = true;
      } else if (statusRes.status === "error") {
        throw new Error(statusRes.error || "Background task failed.");
      }
    }

    if (!finalResult) {
      throw new Error("No pipeline result returned from server.");
    }
    return finalResult;
  }

  // Phase 1: Job Discovery (Scrape -> Verify -> Match)
  async function runDiscovery() {
    if (!user) {
      setAuthOpen(true);
      return;
    }

    if (!cv.trim()) {
      setError("Please add your CV (paste text or upload a file) before running.");
      return;
    }

    setLoading(true);
    setPhase("discovering");
    setError(null);
    setDiscoveryResult(null);
    setResult(null);
    setSelectedJobIds([]);
    setStep(0);

    logStep(
      `Phase 1 Discovery started - query: "${query}", location: "${location}", ` +
        `scan ${jobCount}/board on ${(sites.length ? sites : ["indeed"]).join(", ")}`
    );

    const timers = PHASE1_STEPS.map((name, i) =>
      setTimeout(() => {
        setStep(i + 1);
        logStep(`Agent started - ${name}`);
      }, 400 * (i + 1))
    );

    try {
      logStep("Saving profile (CV + goals)...");
      await api.createProfile(cv, goals);
      logSuccess("Profile saved");

      logStep("Dispatching discovery job to agent pipeline...");
      const startRes = await api.runDiscover({
        query,
        location,
        sites: sites.length ? sites : ["indeed"],
        results_wanted: jobCount,
        is_remote: workArrangement === "remote",
        work_arrangement: workArrangement,
        top_k: topK,
        auto_apply: autoApply,
      });

      const taskId = startRes.task_id;
      logStep(`Discovery task dispatched (ID: ${taskId}). Finding and matching jobs...`);

      const res = await pollUntilDone<DiscoveryResult>(taskId);
      timers.forEach(clearTimeout);

      for (const s of res.agent_chain || []) {
        const note = (s.summary as string) || (s.note as string) || "";
        logSuccess(`Agent complete - ${s.agent}${note ? " - " + note : ""}`);
      }

      logSuccess(
        `Phase 1 complete in ${res.elapsed_s}s - ${res.matches.length} top matches found out of ${res.jobs_verified} verified.`
      );

      setDiscoveryResult(res);
      // Auto-select top matches by default (up to 5)
      const initialSelected = res.matches.slice(0, 5).map((m) => m.job.id);
      setSelectedJobIds(initialSelected);
      setStep(4);
      setPhase("selection");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase("idle");
    } finally {
      timers.forEach(clearTimeout);
      setLoading(false);
    }
  }

  // Phase 2: Document Generation & Application (Resume -> Cover -> Apply -> Skills)
  async function runPrepare() {
    if (!user) {
      setAuthOpen(true);
      return;
    }

    if (selectedJobIds.length === 0) {
      setError("Please select at least one company to process.");
      return;
    }

    setLoading(true);
    setPhase("preparing");
    setError(null);
    setStep(4);

    logStep(`Phase 2 started for ${selectedJobIds.length} selected company/companies.`);

    const timers = PHASE2_STEPS.map((name, i) =>
      setTimeout(() => {
        setStep(4 + i + 1);
        logStep(`Agent started - ${name}`);
      }, 500 * (i + 1))
    );

    try {
      logStep("Dispatching document preparation & application tasks...");
      const startRes = await api.runPrepare({
        job_ids: selectedJobIds,
        auto_apply: autoApply,
      });

      const taskId = startRes.task_id;
      logStep(`Prepare task dispatched (ID: ${taskId}). Building tailored resumes & cover letters...`);

      const res = await pollUntilDone<PipelineResult>(taskId);
      timers.forEach(clearTimeout);

      for (const s of res.agent_chain || []) {
        const note = (s.summary as string) || (s.note as string) || "";
        logSuccess(`Agent complete - ${s.agent}${note ? " - " + note : ""}`);
      }

      logSuccess(
        `Phase 2 complete in ${res.elapsed_s}s - ${res.recommendations.length} tailored applications generated.`
      );

      setResult(res);
      setStep(9);
      setPhase("complete");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase("selection");
    } finally {
      timers.forEach(clearTimeout);
      setLoading(false);
    }
  }

  return (
    <section id="run" className="relative mx-auto max-w-5xl px-4 py-28">
      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />

      <div className="mb-12 text-center">
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-neon-fuchsia">Production Pipeline</p>
        <h2 className="font-display text-4xl font-bold sm:text-5xl">Run your pipeline</h2>
        <p className="mx-auto mt-4 max-w-xl text-white/60">
          Paste a CV, discover top matching jobs, and pick which companies to tailor documents for.
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
          <div className="mt-4">
            <p className="mb-2 text-sm font-semibold text-white/80">...or upload your CV</p>
            <CvDropzone
              careerGoals={goals}
              onParsed={applyParsedProfile}
              onRequireAuth={() => setAuthOpen(true)}
            />
          </div>
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
              <label className="mb-2 block text-sm font-semibold text-white/80">
                Top matches: {topK}
              </label>
              <input
                type="range"
                min={1}
                max={25}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="mt-3 w-full accent-neon-fuchsia"
              />
            </div>
          </div>
          <label className="mb-2 mt-4 block text-sm font-semibold text-white/80">
            Jobs to scan per board: {jobCount}
          </label>
          <input
            type="range"
            min={10}
            max={250}
            step={10}
            value={jobCount}
            onChange={(e) => setJobCount(Number(e.target.value))}
            className="w-full accent-neon-cyan"
          />
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
          <label className="mb-2 mt-4 block text-sm font-semibold text-white/80">Job type</label>
          <div className="flex flex-wrap gap-2">
            {WORK_ARRANGEMENTS.map((w) => (
              <button
                key={w.value}
                onClick={() => setWorkArrangement(w.value)}
                className={
                  "rounded-full px-3 py-1.5 text-xs font-medium transition-colors " +
                  (workArrangement === w.value
                    ? "bg-gradient-to-r from-neon-violet to-neon-cyan text-white"
                    : "glass text-white/60 hover:text-white")
                }
              >
                {w.label}
              </button>
            ))}
          </div>
          <label className="mt-3 flex cursor-pointer items-center gap-2 text-sm text-white/80">
            <input
              type="checkbox"
              checked={autoApply}
              onChange={(e) => setAutoApply(e.target.checked)}
              className="h-4 w-4 accent-neon-fuchsia"
            />
            Auto-apply by email to strong matches
          </label>
        </div>
      </div>

      <div className="mt-8 flex flex-col items-center gap-6">
        <button
          onClick={runDiscovery}
          disabled={loading || phase === "preparing"}
          className="btn-glow min-w-[220px] disabled:opacity-60"
        >
          {loading && phase === "discovering" ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" /> Discovering jobs...
            </>
          ) : (
            <>
              <Play className="h-4 w-4" /> Find Matching Jobs (Phase 1)
            </>
          )}
        </button>

        {(loading || discoveryResult || result) && (
          <div className="w-full max-w-3xl glass rounded-2xl p-5">
            <AgentFlow active={step} pausedAtSelection={phase === "selection"} />
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            <AlertCircle className="h-4 w-4" /> {error}
            <span className="text-red-300/70">- check activity log for details.</span>
          </div>
        )}
      </div>

      {/* Phase 1 Job Selection UI */}
      {discoveryResult && (phase === "selection" || phase === "preparing") && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-12 rounded-3xl border border-neon-cyan/30 glass-strong p-6"
        >
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="font-display text-2xl font-bold text-white">
                Select Companies to Apply & Prepare Documents
              </h3>
              <p className="text-sm text-white/60">
                Found {discoveryResult.matches.length} verified match(es) in {discoveryResult.elapsed_s}s. Choose which ones to generate tailored resumes & cover letters for.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={toggleSelectAll}
                className="glass inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold text-white/80 hover:text-white"
              >
                {selectedJobIds.length === discoveryResult.matches.length ? (
                  <>
                    <CheckSquare className="h-4 w-4 text-neon-cyan" /> Deselect All
                  </>
                ) : (
                  <>
                    <Square className="h-4 w-4" /> Select All ({discoveryResult.matches.length})
                  </>
                )}
              </button>

              <button
                onClick={runPrepare}
                disabled={loading || selectedJobIds.length === 0}
                className="btn-glow inline-flex items-center gap-2 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50"
              >
                {loading && phase === "preparing" ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> Tailoring Documents...
                  </>
                ) : (
                  <>
                    Generate for {selectedJobIds.length} Selected <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {discoveryResult.matches.map((item, index) => (
              <JobSelectCard
                key={item.job.id}
                matchItem={item}
                selected={selectedJobIds.includes(item.job.id)}
                onToggle={() => toggleJobSelection(item.job.id)}
                index={index}
              />
            ))}
          </div>
        </motion.div>
      )}

      {/* Phase 2 Tailored Results UI */}
      <AnimatePresence>
        {result && (
          <motion.div variants={results} initial="hidden" animate="show" className="mt-10 space-y-4">
            <div className="flex flex-wrap items-center justify-center gap-6 text-center text-sm text-white/60">
              <Stat label="Tailored Applications" value={result.recommendations.length} />
              <Stat label="Total Time" value={`${result.elapsed_s}s`} />
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
