"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  MapPin,
  Building2,
  ChevronDown,
  FileText,
  PenLine,
  GraduationCap,
  CheckCircle2,
  ExternalLink,
} from "lucide-react";
import type { Recommendation } from "@/lib/types";
import { cn } from "@/lib/cn";
import MatchRing from "./MatchRing";

const TABS = [
  { key: "resume", label: "Resume", icon: FileText },
  { key: "cover", label: "Cover Letter", icon: PenLine },
  { key: "skills", label: "Skills & Interview", icon: GraduationCap },
] as const;

type TabKey = (typeof TABS)[number]["key"];

const enter = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

export default function JobResultCard({ rec, index }: { rec: Recommendation; index: number }) {
  const [open, setOpen] = useState(index === 0);
  const [tab, setTab] = useState<TabKey>("resume");
  const { job, match, resume, cover_letter, skill_gap, interview_prep, application } = rec;

  return (
    <motion.div variants={enter} className="sheen overflow-hidden rounded-2xl glass-strong">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-4 p-5 text-left"
      >
        <MatchRing score={match.score} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate font-display text-lg font-semibold">{job.title}</h3>
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
            {application && (
              <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-white/70">
                {application.status.replace(/_/g, " ")}
              </span>
            )}
          </div>
        </div>
        <ChevronDown className={cn("h-5 w-5 shrink-0 text-white/50 transition-transform", open && "rotate-180")} />
      </button>

      {open && (
        <div className="border-t border-white/10 p-5">
          <p className="mb-4 text-sm text-white/70">{match.rationale}</p>

          <div className="mb-5 flex flex-wrap gap-2">
            {match.matched_skills.map((s) => (
              <span key={s} className="rounded-full bg-neon-lime/15 px-3 py-1 text-xs font-medium text-neon-lime">
                {s}
              </span>
            ))}
            {match.missing_skills.map((s) => (
              <span key={s} className="rounded-full bg-white/5 px-3 py-1 text-xs font-medium text-white/50 line-through decoration-white/30">
                {s}
              </span>
            ))}
          </div>

          <div className="mb-4 flex gap-2">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-semibold transition-colors",
                  tab === t.key ? "bg-white/10 text-white" : "text-white/50 hover:text-white"
                )}
              >
                <t.icon className="h-3.5 w-3.5" /> {t.label}
              </button>
            ))}
          </div>

          <div className="rounded-xl bg-ink-950/60 p-4 text-sm leading-relaxed text-white/80">
            {tab === "resume" && <pre className="whitespace-pre-wrap font-sans">{resume.plain_text}</pre>}
            {tab === "cover" && <pre className="whitespace-pre-wrap font-sans">{cover_letter.body}</pre>}
            {tab === "skills" && (
              <div className="space-y-4">
                <div>
                  <h4 className="mb-2 font-semibold text-white">Learning roadmap</h4>
                  <ul className="list-inside list-disc space-y-1 text-white/70">
                    {(skill_gap.roadmap as unknown[]).map((r, i) => (
                      <li key={i}>{typeof r === "string" ? r : `${(r as any).skill} \u2014 ${(r as any).resource}`}</li>
                    ))}
                    {skill_gap.roadmap.length === 0 && <li>No major gaps — you're a strong fit.</li>}
                  </ul>
                </div>
                <div>
                  <h4 className="mb-2 font-semibold text-white">Mock interview questions</h4>
                  <ol className="list-inside list-decimal space-y-1 text-white/70">
                    {interview_prep.questions.map((q, i) => (
                      <li key={i}>{q}</li>
                    ))}
                  </ol>
                </div>
              </div>
            )}
          </div>

          {job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-neon-cyan hover:underline"
            >
              View original posting <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
        </div>
      )}
    </motion.div>
  );
}
