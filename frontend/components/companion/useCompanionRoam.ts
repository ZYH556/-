"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface CompanionRoamOptions {
  /** false 时原地冻结（答题中 / 悬停 / 问候播放中），不自动走动。 */
  active: boolean;
  /** true 时走回右下角家位并停留（面板打开时）。 */
  goHome: boolean;
  /** 拖拽进行中：暂停自动走动，位置完全由 place() 驱动。 */
  dragging: boolean;
  petWidth: number;
  petHeight: number;
}

export interface CompanionRoamState {
  /** 距视口左缘 / 上缘的 px 偏移。 */
  x: number;
  y: number;
  /** 1 = 面朝左（精灵原始朝向），-1 = 面朝右。 */
  facing: 1 | -1;
  walking: boolean;
}

export interface CompanionRoamApi extends CompanionRoamState {
  /** 直接放置学伴（拖拽落点），位置会被夹回视口内并原地休息。 */
  place: (x: number, y: number) => void;
}

const EDGE = 16;
/** 顶部留白更大，避免盖住页头与导航。 */
const TOP_EDGE = 96;
const SPEED_PX_S = 76;
const TICK_MS = 50;
const REST_MIN_MS = 2600;
const REST_MAX_MS = 7000;
/** 小屏不自动漫游：避免学伴在移动端横穿内容、遮挡底部操作（仍可拖拽）。 */
const ROAM_MIN_VIEWPORT = 768;

interface Point {
  x: number;
  y: number;
}

function bounds(petWidth: number, petHeight: number): { max: Point; home: Point } {
  if (typeof window === "undefined") {
    return { max: { x: 0, y: 0 }, home: { x: 0, y: 0 } };
  }
  const max = {
    x: Math.max(EDGE, window.innerWidth - petWidth - EDGE),
    y: Math.max(TOP_EDGE, window.innerHeight - petHeight - EDGE),
  };
  return { max, home: { x: max.x, y: max.y } };
}

function clampPoint(point: Point, max: Point): Point {
  return {
    x: Math.min(Math.max(point.x, EDGE), max.x),
    y: Math.min(Math.max(point.y, TOP_EDGE), max.y),
  };
}

export function useCompanionRoam({
  active,
  goHome,
  dragging,
  petWidth,
  petHeight,
}: CompanionRoamOptions): CompanionRoamApi {
  const [state, setState] = useState<CompanionRoamState>(() => {
    const { home } = bounds(petWidth, petHeight);
    return { x: home.x, y: home.y, facing: 1, walking: false };
  });
  const target = useRef<Point>(bounds(petWidth, petHeight).home);
  const nextDecisionAt = useRef(0);
  const reducedMotion = useRef(false);

  useEffect(() => {
    reducedMotion.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const onResize = () => {
      const { max } = bounds(petWidth, petHeight);
      target.current = clampPoint(target.current, max);
      setState((s) => ({ ...s, ...clampPoint(s, max) }));
    };
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [petWidth, petHeight]);

  const place = useCallback(
    (x: number, y: number) => {
      const { max } = bounds(petWidth, petHeight);
      const spot = clampPoint({ x, y }, max);
      target.current = spot;
      nextDecisionAt.current = Date.now() + REST_MIN_MS;
      setState((s) => ({ ...s, ...spot, walking: false }));
    },
    [petWidth, petHeight],
  );

  useEffect(() => {
    if (!active || dragging || reducedMotion.current) return;
    const timer = setInterval(() => {
      const now = Date.now();
      const { max, home } = bounds(petWidth, petHeight);
      const roamAllowed = window.innerWidth >= ROAM_MIN_VIEWPORT;
      if (goHome) target.current = home;
      setState((prev) => {
        const dx = target.current.x - prev.x;
        const dy = target.current.y - prev.y;
        const distance = Math.hypot(dx, dy);
        if (distance > 4) {
          const step = (SPEED_PX_S * TICK_MS) / 1000;
          const ratio = Math.min(1, step / distance);
          const next = clampPoint({ x: prev.x + dx * ratio, y: prev.y + dy * ratio }, max);
          return {
            ...next,
            facing: Math.abs(dx) > 1 ? (dx < 0 ? 1 : -1) : prev.facing,
            walking: true,
          };
        }
        if (!goHome && roamAllowed && now >= nextDecisionAt.current) {
          // 到站休息后再决定下一段散步：55% 漫步到随机位置，45% 继续发呆。
          nextDecisionAt.current =
            now + REST_MIN_MS + Math.random() * (REST_MAX_MS - REST_MIN_MS);
          if (Math.random() < 0.55) {
            target.current = {
              x: EDGE + Math.random() * (max.x - EDGE),
              y: TOP_EDGE + Math.random() * (max.y - TOP_EDGE),
            };
          }
        }
        return prev.walking ? { ...prev, walking: false } : prev;
      });
    }, TICK_MS);
    return () => clearInterval(timer);
  }, [active, goHome, dragging, petWidth, petHeight]);

  return { ...state, place };
}
