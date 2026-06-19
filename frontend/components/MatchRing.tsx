"use client";

import { motion } from "framer-motion";

/** Circular score gauge (0..1) with a gradient stroke. */
export default function MatchRing({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(1, score));
  const r = 26;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - pct);
  const color = pct >= 0.75 ? "#a3e635" : pct >= 0.5 ? "#22d3ee" : "#d946ef";
  return (
    <div className="relative h-16 w-16">
      <svg viewBox="0 0 64 64" className="h-16 w-16 -rotate-90">
        <circle cx="32" cy="32" r={r} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="6" />
        <motion.circle
          cx="32"
          cy="32"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={c}
          initial={ringStart}
          animate={ringEnd(offset)}
          transition={ringTransition}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-sm font-bold">
        {Math.round(pct * 100)}
      </div>
    </div>
  );
}

const ringStart = { strokeDashoffset: 2 * Math.PI * 26 };
const ringEnd = (offset: number) => ({ strokeDashoffset: offset });
const ringTransition = { duration: 1, ease: "easeOut" };
