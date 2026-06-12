import Link from "next/link";

/** 品牌像素角色标（manzdev 像素头像）：深蓝圆角底块承托，任意背景下清晰可辨。
 *  函数名沿用 NeuronMark 以保持调用处（AuthGate / HeroLanding / 页脚）零改动。 */
export function NeuronMark({ size = 28 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 160 160"
      aria-hidden="true"
      className="shrink-0"
    >
      <defs>
        <linearGradient id="brand-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#003a59" />
          <stop offset="1" stopColor="#001624" />
        </linearGradient>
      </defs>
      <rect width="160" height="160" rx="34" fill="url(#brand-bg)" />
      <g transform="translate(12.5 12.5)">
        <g transform="translate(-9.76 -4.25) scale(.97747)">
          <path
            d="M30.92 101.94h8.73v-8.2h-8.73V26.8h8.47v-8.47h8.73v-9h66.67v9.8h16.14v33.6h-8.2v100.8H30.66Z"
            fill="#fff"
            transform="scale(.96438)rotate(-6.25 160.33 72.15)"
          />
          <path
            d="M190.47 52.83V36.55h4.14v-4.01h4.01v-3.88h-4v-4.14h-4.01V.33h4.14v-4h4v-4.15h24.2v4.14h7.88v8.02h-4.01l.2 48.57Z"
            fill="#000"
            transform="scale(1.98375)rotate(-6.25 320.45 1596.32)"
          />
          <path
            d="M226.93 4.47h-8.13V.33h-16.03v8.02h-4.15v16.04h4.01v4h8.15v4.28h7.89v-4h-4.01v-4.28h8.15v8.28h4.14z"
            fill="#cc984f"
            transform="scale(1.98375)rotate(-6.25 320.45 1596.32)"
          />
          <path
            d="M218.67 4.34h-15.9v3.88h-4.15v12.16h4.01v4.14h20.2v4h4.12l-.01-24.18z"
            fill="#ffcc80"
            transform="scale(1.98375)rotate(-6.25 320.45 1596.32)"
          />
          <path
            d="M206.64 8.35h4.28v8.29h-4.28zM218.81 8.35h4.28v8.29h-4.28z"
            fill="#000"
            transform="scale(1.98375)rotate(-6.25 320.45 1596.32)"
          />
          <path
            d="M210.98 16.57h12.16v3.88h-12.16z"
            fill="#ebb267"
            transform="scale(1.98375)rotate(-6.25 320.45 1596.32)"
          />
          <path
            d="M218.8 4.34h8.03v4h-8.03z"
            fill="#ebb267"
            transform="scale(1.98375)rotate(-6.25 320.45 1596.32)"
          />
          <path
            d="M190.47 48.84h8.02v3.88h-8.02z"
            fill="#cc984f"
            transform="scale(1.98375)rotate(-6.25 320.45 1596.32)"
          />
          <path
            d="M206.72 52.82v-7.94l12.55.01v7.97z"
            fill="#0d2061"
            transform="scale(1.98375)rotate(-6.25 320.45 1596.32)"
          />
          <path
            d="M210.83 40.65h4.16v4.25h-4.16z"
            fill="#17ffff"
            transform="scale(1.98375)rotate(-6.25 320.45 1596.32)"
          />
          <path
            d="M215.11 48.95h4.16v3.89h-4.16z"
            fill="#17ffff"
            transform="scale(1.98375)rotate(-6.25 320.45 1596.32)"
          />
          <path
            d="M210.89 48.95h4.21v3.89h-4.21z"
            fill="#e65100"
            transform="scale(1.98375)rotate(-6.25 320.45 1596.32)"
          />
          <path
            d="M206.71 44.89h4.16v4.1h-4.16z"
            fill="#cc2554"
            transform="scale(1.98375)rotate(-6.25 320.45 1596.32)"
          />
        </g>
      </g>
    </svg>
  );
}

/** 像素角色 + ReflexLearn 字标组合。 */
export function BrandMark({
  size = 28,
  href = "/",
  withText = true,
}: {
  size?: number;
  href?: string | null;
  withText?: boolean;
}) {
  const inner = (
    <span className="inline-flex items-center gap-2.5 text-foreground">
      <NeuronMark size={size} />
      {withText && (
        <span
          className="text-2xl tracking-tight"
          style={{ fontFamily: "var(--font-display)" }}
        >
          ReflexLearn
        </span>
      )}
    </span>
  );
  if (!href) return inner;
  return (
    <Link href={href} className="transition-opacity hover:opacity-80">
      {inner}
    </Link>
  );
}
