import Link from "next/link";
import { ArrowRight, Rocket, Sparkles } from "lucide-react";
import Background from "@/components/Background";
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import HowItWorks from "@/components/HowItWorks";
import AgentsShowcase from "@/components/AgentsShowcase";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <main className="relative">
      <Background />
      <Navbar />
      <Hero />
      <HowItWorks />
      <AgentsShowcase />

      {/* Dedicated Demo CTA Section */}
      <section className="relative mx-auto max-w-5xl px-4 py-24 text-center">
        <div className="glass-strong relative overflow-hidden rounded-3xl p-10 sm:p-16 shadow-glow">
          <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-neon-violet/20 blur-3xl" />
          <div className="absolute -bottom-20 -left-20 h-64 w-64 rounded-full bg-neon-cyan/20 blur-3xl" />

          <div className="relative z-10 mx-auto max-w-2xl">
            <span className="mb-4 inline-flex items-center gap-2 rounded-full border border-neon-cyan/30 bg-neon-cyan/10 px-4 py-1.5 text-xs font-semibold text-neon-cyan">
              <Sparkles className="h-3.5 w-3.5" /> Ready to automate your job search?
            </span>
            <h2 className="mt-4 font-display text-4xl font-bold sm:text-5xl">
              Experience <span className="text-gradient">JOB CANNON</span> in Action
            </h2>
            <p className="mt-4 text-white/70 text-base sm:text-lg">
              Upload your resume or enter your criteria to watch nine autonomous AI agents scrape, match, and tailor applications live.
            </p>
            <div className="mt-8 flex justify-center">
              <Link href="/demo" className="btn-glow inline-flex items-center gap-2.5 px-8 py-4 text-base font-semibold">
                <Rocket className="h-5 w-5 text-neon-cyan" /> Launch Live Demo <ArrowRight className="h-5 w-5" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </main>
  );
}
