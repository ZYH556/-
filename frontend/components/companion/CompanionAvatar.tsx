"use client";

import { useEffect, useRef, useState } from "react";

import { PET_MOODS, PET_SHEET, PET_SLEEP_AFTER_MS, type PetMood } from "./sprites";

interface CompanionAvatarProps {
  /** 外部驱动的动画情绪；idle 时组件内部会在长时间无交互后自动入睡。 */
  mood: PetMood;
  /** 显示宽度（px），高度按帧比例自动换算。 */
  size?: number;
  /** true 时水平镜像（精灵原始朝左，向右移动时翻面）。 */
  flip?: boolean;
  className?: string;
}

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(query.matches);
    const onChange = (event: MediaQueryListEvent) => setReduced(event.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  return reduced;
}

export function CompanionAvatar({
  mood,
  size = 84,
  flip = false,
  className = "",
}: CompanionAvatarProps) {
  const [frame, setFrame] = useState(0);
  const [dozing, setDozing] = useState(false);
  const sleepTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reducedMotion = usePrefersReducedMotion();

  const effectiveMood: PetMood = mood === "idle" && dozing ? "sleep" : mood;
  const spec = PET_MOODS[effectiveMood];

  useEffect(() => {
    if (mood !== "idle") {
      setDozing(false);
      if (sleepTimer.current) clearTimeout(sleepTimer.current);
      return;
    }
    sleepTimer.current = setTimeout(() => setDozing(true), PET_SLEEP_AFTER_MS);
    return () => {
      if (sleepTimer.current) clearTimeout(sleepTimer.current);
    };
  }, [mood]);

  useEffect(() => {
    setFrame(0);
    if (reducedMotion) return;
    const interval = setInterval(() => {
      setFrame((value) => (value + 1) % spec.frames);
    }, Math.round(1000 / spec.fps));
    return () => clearInterval(interval);
  }, [spec, reducedMotion]);

  const height = Math.round((size * PET_SHEET.frameHeight) / PET_SHEET.frameWidth);
  return (
    <span
      role="img"
      aria-label="AI 学伴牛牛"
      className={`pointer-events-none block select-none ${className}`}
      style={{
        width: size,
        height,
        backgroundImage: `url(${PET_SHEET.src})`,
        backgroundRepeat: "no-repeat",
        backgroundSize: `${size * PET_SHEET.cols}px ${height * PET_SHEET.rows}px`,
        backgroundPosition: `-${frame * size}px -${spec.row * height}px`,
        transform: flip ? "scaleX(-1)" : undefined,
      }}
    />
  );
}
