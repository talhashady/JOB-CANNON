"use client";

import { motion } from "framer-motion";
import {
  Search,
  ShieldCheck,
  Target,
  FileText,
  PenLine,
  Send,
  LineChart,
  GraduationCap,
  Brain,
} from "lucide-react";
import { cn } from "@/lib/cn";

const AGENTS = [
  { icon: Brain, name: "Orchestrator", desc: "Coordinates every specialist and keeps your profile in context.", accent: "from-neon-violet to-neon-fuchsia" },
  { icon: Search, name: "Job Scraping", desc: "Pulls real listings from Indeed, LinkedIn & more via JobSpy.", accent: "from-sky-400 to-neon-cyan" },
  { icon: ShieldCheck, name: "Verification", desc: "Drops duplicates, expired posts, and suspicious companies.", accent: "from-emerald-400 to-neon-lime" },
  { icon: Target, name: "Matching", desc: "Weighted scoring across skills, experience, location & goals.", accent: "from-amber-400 to-orange-500" },
  { icon: FileText, name: "Resume", desc: "Reorders and highlights — never fabricates — ATS-safe output.", accent: "from-neon-fuchsia to-pink-500" },
  { icon: PenLine, name: "Cover Letter", desc: "Tailored, grounded in your real CV. No hallucinated claims.", accent: "from-violet-400 to-neon-violet" },
  { icon: Send, name: "Application", desc: "Dry-run by default. Rate-limited and ToS-aware.", accent: "from-cyan-400 to-blue-500" },
  { icon: LineChart, name: "Tracking", desc: "Persists every status transition across your search.", accent: "from-teal-400 to-emerald-500" },
  { icon: GraduationCap, name: "Skill & Interview", desc: "Gap analysis, a learning roadmap, and mock questions.", accent: "from-fuchsia-400 to-purple-500" },
];

const card = {
  hidden: { opacity: 0, y: 28 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};
const grid = { hidden: {}, show: { transition: { staggerChildren: 0.06 } } };

export default function AgentsShowcase() {
  return (
    <section id="agents" className="relative mx-auto max-w-6xl px-4 py-28">
      <div className="mb-14 text-center">
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-neon-cyan">The team</p>
        <h2 className="font-display text-4xl font-bold sm:text-5xl">Nine agents. One mission.</h2>
        <p className="mx-auto mt-4 max-w-xl text-white/60">
          Each agent is a focused specialist with its own guardrails, handing off to the next in a
          single orchestrated pipeline.
        </p>
      </div>

      <motion.div
        variants={grid}
        initial="hidden"
        whileInView="show"
        viewport={onceView}
        className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3"
      >
        {AGENTS.map((a) => (
          <motion.div
            key={a.name}
            variants={card}
            className="sheen group relative overflow-hidden rounded-2xl glass p-6 transition-transform duration-300 hover:-translate-y-1"
          >
            <div className={cn("mb-4 inline-grid h-12 w-12 place-items-center rounded-xl bg-gradient-to-br text-white shadow-glow", a.accent)}>
              <a.icon className="h-6 w-6" />
            </div>
            <h3 className="font-display text-lg font-semibold">{a.name}</h3>
            <p className="mt-2 text-sm leading-relaxed text-white/60">{a.desc}</p>
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}

const onceView = { once: true, margin: "-80px" };
