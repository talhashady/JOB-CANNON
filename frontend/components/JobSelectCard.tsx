"use client";

import { motion } from "framer-motion";
import {
  MapPin,
  Building2,
  CheckCircle2,
  ExternalLink,
  Check,
} from "lucide-react";
import type { DiscoveryMatch } from "@/lib/types";
import { cn } from "@/lib/cn";
import MatchRing from "./MatchRing";

const enter = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

interface JobSelectCardProps {
  matchItem: DiscoveryMatch;
  selected: boolean;
  onToggle: () => void;
  index: number;
}

export default function JobSelectCard({
  matchItem,
  selected,
  onToggle,
}: JobSelectCardProps) {
  const { job, match } = matchItem;

  return (
    <motion.div
      variants={enter}
      onClick={onToggle}
      className={cn(
        "group relative cursor-pointer overflow-hidden rounded-2xl p-5 transition-all border",
        selected
          ? "border-neon-cyan/60 bg-ink-900/90 shadow-glow"
          : "border-white/10 bg-ink-950/40 hover:border-white/20 hover:bg-ink-950/60"
      )}
    >
      <div className="flex items-start gap-4">
        {/* Checkbox */}
        <div
          className={cn(
            "mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg border transition-all",
            selected
              ? "border-neon-cyan bg-neon-cyan text-ink-950"
              : "border-white/30 bg-white/5 group-hover:border-white/50"
          )}
        >
          {selected && <Check className="h-4 w-4 stroke-[3]" />}
        </div>

        {/* Score Ring */}
        <MatchRing score={match.score} />

        {/* Content */}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate font-display text-lg font-semibold text-white">
              {job.title}
            </h3>
            {job.verified && (
              <span className="inline-flex items-center gap-1 rounded-full bg-neon-lime/15 px-2 py-0.5 text-[10px] font-semibold text-neon-lime">
                <CheckCircle2 className="h-3 w-3" /> Verified
              </span>
            )}
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-white/60">
            <span className="inline-flex items-center gap-1">
              <Building2 className="h-3.5 w-3.5" /> {job.company}
            </span>
            {job.location && (
              <span className="inline-flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5" /> {job.location}
              </span>
            )}
            {job.source && (
              <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-white/60">
                {job.source}
              </span>
            )}
          </div>

          {/* Rationale */}
          <p className="mt-2 text-xs text-white/70">{match.rationale}</p>

          {/* Skills Badges */}
          <div className="mt-3 flex flex-wrap gap-1.5">
            {match.matched_skills.map((s) => (
              <span
                key={s}
                className="rounded-full bg-neon-lime/15 px-2.5 py-0.5 text-[11px] font-medium text-neon-lime"
              >
                {s}
              </span>
            ))}
            {match.missing_skills.map((s) => (
              <span
                key={s}
                className="rounded-full bg-white/5 px-2.5 py-0.5 text-[11px] font-medium text-white/40 line-through decoration-white/30"
              >
                {s}
              </span>
            ))}
          </div>

          {/* Original Link */}
          {job.url && (
            <div className="mt-3">
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="inline-flex items-center gap-1 text-xs font-semibold text-neon-cyan hover:underline"
              >
                View posting <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
