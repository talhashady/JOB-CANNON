"use client";

import { motion } from "framer-motion";
import { FileSearch, Wand2, Send } from "lucide-react";

const STEPS = [
  {
    icon: FileSearch,
    title: "1 · Discover & verify",
    body: "We pull live listings from the boards you pick, then strip duplicates, expired posts, and sketchy companies.",
  },
  {
    icon: Wand2,
    title: "2 · Match & tailor",
    body: "Weighted scoring ranks the best fits, then your resume and cover letter are rewritten for each role — ATS-safe, never fabricated.",
  },
  {
    icon: Send,
    title: "3 · Apply & grow",
    body: "Applications are prepared (dry-run by default), tracked end to end, and paired with a skill roadmap plus mock interview questions.",
  },
];

const card = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};
const grid = { hidden: {}, show: { transition: { staggerChildren: 0.12 } } };
const onceView = { once: true, margin: "-80px" };

export default function HowItWorks() {
  return (
    <section id="how" className="relative mx-auto max-w-6xl px-4 py-28">
      <div className="mb-14 text-center">
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-neon-violet">How it works</p>
        <h2 className="font-display text-4xl font-bold sm:text-5xl">From CV to callback</h2>
      </div>
      <motion.div
        variants={grid}
        initial="hidden"
        whileInView="show"
        viewport={onceView}
        className="grid gap-6 md:grid-cols-3"
      >
        {STEPS.map((s) => (
          <motion.div key={s.title} variants={card} className="sheen relative rounded-2xl glass p-7">
            <div className="mb-5 inline-grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-neon-violet/30 to-neon-cyan/30 ring-1 ring-white/10">
              <s.icon className="h-7 w-7 text-white" />
            </div>
            <h3 className="font-display text-xl font-semibold">{s.title}</h3>
            <p className="mt-3 text-sm leading-relaxed text-white/60">{s.body}</p>
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}
