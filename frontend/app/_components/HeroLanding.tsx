"use client";

import Link from "next/link";

const NAV_LINKS = [
  { label: "Home", href: "/", active: true },
  { label: "Workspace", href: "/chat", active: false },
  { label: "Spaces", href: "/spaces", active: false },
  { label: "Tracks", href: "/tracks/ai-programming", active: false },
  { label: "Design", href: "/design", active: false },
];

const HERO_VIDEO_SRC = "/hero-loop.mp4";

export default function HeroLanding() {
  return (
    <div
      className="relative min-h-screen overflow-hidden bg-background text-foreground"
      style={{ fontFamily: "var(--font-body)" }}
    >
      <video
        className="absolute inset-0 z-0 h-full w-full object-cover"
        src={HERO_VIDEO_SRC}
        autoPlay
        loop
        muted
        playsInline
      />

      <nav className="relative z-10 mx-auto flex max-w-7xl flex-row items-center justify-between px-8 py-6">
        <Link
          href="/"
          className="text-3xl tracking-tight text-foreground"
          style={{ fontFamily: "'Instrument Serif', serif" }}
        >
          ReflexLearn<sup className="text-xs">®</sup>
        </Link>

        <div className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`text-sm transition-colors ${
                link.active
                  ? "text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>

        <Link
          href="/chat"
          className="liquid-glass rounded-full px-6 py-2.5 text-sm text-foreground transition-transform hover:scale-[1.03]"
        >
          Begin Journey
        </Link>
      </nav>

      <section className="relative z-10 flex flex-col items-center px-6 pt-32 pb-40 py-[90px] text-center">
        <h1
          className="animate-fade-rise max-w-7xl text-5xl font-normal leading-[0.95] tracking-[-2.46px] sm:text-7xl md:text-8xl"
          style={{ fontFamily: "'Instrument Serif', serif" }}
        >
          Where <em className="not-italic text-muted-foreground">dreams</em> rise{" "}
          <em className="not-italic text-muted-foreground">through the silence.</em>
        </h1>

        <p className="animate-fade-rise-delay mt-8 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
          We&apos;re designing tools for deep thinkers, bold creators, and quiet rebels.
          Amid the chaos, we build digital spaces for sharp focus and inspired work.
        </p>

        <Link
          href="/chat"
          className="liquid-glass animate-fade-rise-delay-2 mt-12 cursor-pointer rounded-full px-14 py-5 text-base text-foreground transition-transform hover:scale-[1.03]"
        >
          Begin Journey
        </Link>
      </section>
    </div>
  );
}
