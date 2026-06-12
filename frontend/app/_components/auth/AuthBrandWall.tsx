"use client";

import { useEffect, useState } from "react";
import { BrandMark } from "../BrandMark";

const HIGHLIGHTS = [
  "从目标、画像到路径，每一步都有清晰依据。",
  "课程、资源、错题和报告会回流成下一步建议。",
  "每一次学习都会沉淀成更贴近你的个人经验。",
];

/** 左侧品牌墙：夜空视频 + 中部学习系统主张 + 亮点轮播。 */
export function AuthBrandWall() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((i) => (i + 1) % HIGHLIGHTS.length);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="relative hidden overflow-hidden text-white lg:flex lg:w-[55%] lg:flex-col">
      <video
        className="absolute inset-0 h-full w-full object-cover"
        src="/hero-loop.mp4"
        autoPlay
        loop
        muted
        playsInline
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(135deg, rgba(0,30,46,0.55) 0%, rgba(0,30,46,0.15) 55%, rgba(0,30,46,0.6) 100%)",
        }}
      />

      <div className="relative p-10">
        <BrandMark size={30} />
      </div>

      <div className="relative flex flex-1 flex-col justify-start px-12 pt-[23vh]">
        <h2
          className="max-w-xl text-5xl leading-[1.12]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          让学习路线，
          <br />
          自我更新。
        </h2>
        <div className="mt-10 h-16 max-w-lg">
          {HIGHLIGHTS.map((text, i) => (
            <p
              key={text}
              className="absolute max-w-lg text-base leading-relaxed text-white/88 transition-opacity duration-700"
              style={{ opacity: i === index ? 1 : 0 }}
            >
              ✦ {text}
            </p>
          ))}
        </div>
        <div className="mt-6 flex gap-2">
          {HIGHLIGHTS.map((_, i) => (
            <span
              key={i}
              className="h-1 rounded-full transition-all duration-500"
              style={{
                width: i === index ? 24 : 10,
                background: i === index ? "#7dd3fc" : "rgba(255,255,255,0.3)",
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
