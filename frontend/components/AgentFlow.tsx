"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/cn";

const STEPS = [
  "Profile",
  "Scrape",
  "Verify",
  "Match",
  "Resume",
  "Cover",
  "Apply",
  "Track",
  "Skills",
];

/** Animated horizontal pipeline showing how far a run has progressed. */
export default function AgentFlow({ active }: { active: number }) {
  return (
    <div className="flex w-full items-center gap-1 overflow-x-auto py-2">
      {STEPS.map((s, i) => {
        const done = i < active;
        const current = i === active;
        return (
          <div key={s} className="flex flex-1 items-center gap-1">
            <div className="flex flex-col items-center gap-1.5">
              <motion.div
                animate={current ? pulse : still}
                className={cn(
                  "grid h-7 w-7 place-items-center rounded-full text-[10px] font-bold transition-colors",
                  done && "bg-neon-lime/90 text-ink-950",
                  current && "bg-gradient-to-br from-neon-violet to-neon-cyan text-white shadow-glow",
                  !done && !current && "glass text-white/40"
                )}
              >
                {done ? "\u2713" : i + 1}
              </motion.div>
              <span className={cn("text-[10px]", current ? "text-white" : "text-white/40")}>{s}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className="mb-4 h-px flex-1 bg-white/10">
                <div
                  className="h-px bg-gradient-to-r from-neon-violet to-neon-cyan transition-all duration-500"
                  style={done ? fullBar : emptyBar}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

const pulse = { scale: [1, 1.12, 1] };
const still = { scale: 1 };
const fullBar = { width: "100%" };
const emptyBar = { width: "0%" };
