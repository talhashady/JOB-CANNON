"use client";

import { Sparkles, Github } from "lucide-react";

export default function Footer() {
  return (
    <footer className="relative border-t border-white/10 px-4 py-12">
      <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-6 sm:flex-row">
        <div className="flex items-center gap-2 font-display text-lg font-bold">
          <span className="grid h-8 w-8 place-items-center rounded-xl bg-gradient-to-br from-neon-violet to-neon-cyan">
            <Sparkles className="h-4 w-4 text-white" />
          </span>
          <span className="text-gradient">CareerOS</span>
        </div>
        <p className="text-center text-sm text-white/40">
          Multi-agent career copilot · Built with Next.js, R3F &amp; FastAPI
        </p>
        <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 text-sm text-white/60 transition-colors hover:text-white"
        >
          <Github className="h-4 w-4" /> Source
        </a>
      </div>
    </footer>
  );
}
