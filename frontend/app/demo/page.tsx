"use client";

import Link from "next/link";
import { ArrowLeft, Rocket } from "lucide-react";
import Background from "@/components/Background";
import Navbar from "@/components/Navbar";
import PipelineRunner from "@/components/PipelineRunner";
import Footer from "@/components/Footer";

export default function DemoPage() {
  return (
    <main className="relative min-h-screen">
      <Background />
      <Navbar />

      <div className="mx-auto max-w-5xl px-4 pt-28">
        <div className="mb-6 flex items-center justify-between">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm text-white/60 transition-colors hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" /> Back to Home
          </Link>
          <span className="glass inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold text-neon-cyan">
            <Rocket className="h-3.5 w-3.5" /> Interactive Pipeline
          </span>
        </div>
      </div>

      <PipelineRunner />
      <Footer />
    </main>
  );
}
