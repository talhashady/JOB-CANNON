"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Play, Sparkles, AlertCircle, Upload } from "lucide-react";
import { api } from "@/lib/api";
import type { PipelineResult, UserProfile } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { logStep, logSuccess } from "@/lib/logger";
import AgentFlow from "./AgentFlow";
import JobResultCard from "./JobResultCard";
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

// Labels used for the live "agent started" log lines (mirrors the AgentFlow stepper).
const AGENT_STEPS = [
  "Scraper Agent",
  "Verification Agent",
  "Matching Agent",
  "Resume Agent",
  "Cover Letter Agent",
  "Skill Gap Agent",
  "Interview Prep Agent",
  "Application Agent",
];

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
  const [topK, setTopK] = useState(25);
  const [autoApply, setAutoApply] = useState(false);

  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [authOpen, setAuthOpen] = useState(false);

  // Clear any auth-related error once the user signs in.
  useEffect(() => {
    if (user) setError(null);
  }, [user]);

  // Debounced auto-update of Career Goals and Role/Keywords when user stops typing in CV box (800ms)
  useEffect(() => {
    if (!cv || cv.trim().length < 15) return;

    const timer = setTimeout(() => {
      const parsed = parseCvTextClient(cv);
      if (parsed) {
        setGoals(parsed.goals);
        setQuery(parsed.query);
        logStep(`Auto-detected goals & role keywords for "${parsed.title}" from your CV`);
      }
    }, 800);

    return () => clearTimeout(timer);
  }, [cv]);

  function toggleSite(s: string) {
    setSites((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));
  }

  function applyParsedProfile(p: UserProfile) {
    // Fill the "Your CV" box with the LLM-generated summary of the whole CV.
    if (p.summary && p.summary.trim()) {
      setCv(p.summary.trim());
      logSuccess("CV summary loaded into the CV box");
    } else if (p.raw_cv_text && p.raw_cv_text.trim()) {
      setCv(p.raw_cv_text);
    } else if (p.skills && p.skills.length) {
      setCv(p.skills.join(", "));
    }
    const derivedG = deriveGoals(p);
    setGoals(derivedG);
    const mainRole = (p.titles && p.titles[0]) || (p.skills && p.skills[0] ? `${p.skills[0]} developer` : "software engineer");
    setQuery(mainRole.toLowerCase());
  }

  async function run() {
    // Require sign-in before scraping; open the login modal silently.
    if (!user) {
      setAuthOpen(true);
      return;
    }

    if (!cv.trim()) {
      setError("Please add your CV (paste text or upload a file) before running.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setStep(0);
    logStep(
      `Pipeline run started - query: "${query}", location: "${location}", ` +
        `scan ${jobCount}/board on ${(sites.length ? sites : ["indeed"]).join(", ")}` +
        (autoApply ? `, auto-apply to top ${topK}` : "")
    );

    // Optimistic stepper + live "agent started" logs while the request is in flight.
    const timers = AGENT_STEPS.map((name, i) =>
      setTimeout(() => {
        setStep(i + 1);
        logStep(`Agent started - ${name}`);
      }, 350 * (i + 1))
    );

    try {
      logStep("Saving profile (CV + goals)...");
      await api.createProfile(cv, goals);
      logSuccess("Profile saved");

      logStep("Dispatching job to the agent pipeline...");
      const startRes = await api.run({
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
      logStep(`Job dispatched. Task ID: ${taskId}. Processing background run...`);

      let taskDone = false;
      let finalResult: PipelineResult | null = null;
      const MAX_POLLS = 150; // 150 × 2s = 5 minutes max
      let pollCount = 0;

      while (!taskDone) {
        if (pollCount >= MAX_POLLS) {
          throw new Error("Pipeline timed out after 5 minutes. The server may have restarted — please try again.");
        }
        await new Promise((resolve) => setTimeout(resolve, 2000));
        pollCount++;
        const statusRes = await api.pollTask(taskId);
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

      // Clear the optimistic timers
      timers.forEach(clearTimeout);

      // Log the real completion of each agent from the returned audit trail.
      for (const s of finalResult.agent_chain || []) {
        const note = (s.summary as string) || (s.note as string) || "";
        logSuccess(`Agent complete - ${s.agent}${note ? " - " + note : ""}`);
      }
      logSuccess(
        `Pipeline complete in ${finalResult.elapsed_s}s - ${finalResult.recommendations.length} matches, ${finalResult.jobs_scraped} scraped, ${finalResult.jobs_verified} verified`
      );

      setResult(finalResult);
      setStep(9);
    } catch (e) {
      // The api client already logged the RAW error (operation + url + raw message).
      setError(e instanceof Error ? e.message : String(e));
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
                {autoApply ? "Apply to top" : "Top matches"}: {topK}
              </label>
              <input
                type="range"
                min={1}
                max={50}
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
            <span className="text-red-300/70">- open the activity panel (bottom-right) for the raw error.</span>
          </div>
        )}
      </div>

      <AnimatePresence>
        {result && (
          <motion.div variants={results} initial="hidden" animate="show" className="mt-10 space-y-4">
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
