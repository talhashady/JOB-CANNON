"use client";

import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import { ArrowRight, Bot, ShieldCheck, Sparkles } from "lucide-react";

// 3D scene is client-only and heavy; load it lazily so first paint stays fast.
const Scene3D = dynamic(() => import("./Scene3D"), { ssr: false });

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0 },
};
const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12, delayChildren: 0.1 } },
};
const heroTransition = { duration: 0.7, ease: "easeOut" };

export default function Hero() {
  return (
    <section id="top" className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      {/* 3D layer */}
      <div className="absolute inset-0">
        <Scene3D />
      </div>
      {/* readability scrim */}
      <div className="absolute inset-0 bg-gradient-to-b from-ink-950/30 via-ink-950/10 to-ink-950" />

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="relative z-10 mx-auto max-w-3xl text-center"
      >
        <motion.div variants={fadeUp} transition={heroTransition} className="mb-6 flex justify-center">
          <span className="glass inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium text-white/80">
            <Sparkles className="h-3.5 w-3.5 text-neon-cyan" />
            Powered by 9 specialized AI agents
          </span>
        </motion.div>

        <motion.h1
          variants={fadeUp}
          transition={heroTransition}
          className="font-display text-5xl font-bold leading-[1.05] tracking-tight sm:text-6xl md:text-7xl"
        >
          Your career, <br />
          <span className="text-gradient animate-gradient-x">on autopilot.</span>
        </motion.h1>

        <motion.p
          variants={fadeUp}
          transition={heroTransition}
          className="mx-auto mt-6 max-w-xl text-balance text-lg text-white/70"
        >
          CareerOS scrapes real jobs, verifies them, matches them to your profile, tailors your
          resume &amp; cover letter, and preps you for interviews — all in one orchestrated flow.
        </motion.p>

        <motion.div variants={fadeUp} transition={heroTransition} className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <a href="#run" className="btn-glow">
            Run the pipeline <ArrowRight className="h-4 w-4" />
          </a>
          <a href="#agents" className="btn-ghost">
            <Bot className="h-4 w-4" /> Meet the agents
          </a>
        </motion.div>

        <motion.div variants={fadeUp} transition={heroTransition} className="mt-8 flex items-center justify-center gap-2 text-xs text-white/50">
          <ShieldCheck className="h-4 w-4 text-neon-lime" />
          PII-scrubbed · ATS-safe · dry-run by default
        </motion.div>
      </motion.div>

      {/* scroll hint */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2">
        <div className="h-10 w-6 rounded-full border border-white/20 p-1">
          <div className="mx-auto h-2 w-1 animate-float rounded-full bg-white/60" />
        </div>
      </div>
    </section>
  );
}
