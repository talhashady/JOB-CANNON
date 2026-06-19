"use client";

/** Layered ambient background: aurora gradient + grid + noise. Pure CSS, cheap. */
export default function Background() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 bg-ink-950" />
      <div className="absolute inset-0 bg-aurora" />
      <div className="absolute inset-0 bg-grid bg-gridcell [mask-image:radial-gradient(70%_60%_at_50%_0%,#000_0%,transparent_75%)]" />
      <div className="absolute inset-0 noise opacity-60" />
      <div className="absolute -left-40 top-1/3 h-[28rem] w-[28rem] rounded-full bg-neon-violet/20 blur-[120px] animate-float" />
      <div className="absolute -right-32 top-10 h-[24rem] w-[24rem] rounded-full bg-neon-cyan/20 blur-[120px] animate-float [animation-delay:2s]" />
    </div>
  );
}
