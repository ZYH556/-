import Link from "next/link";

/** 神经元星芒品牌标：中心思维节点 + 外围智能体节点（导航 / 登录页 / 页脚复用）。 */
export function NeuronMark({ size = 28 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      aria-hidden="true"
      className="shrink-0"
    >
      <g stroke="currentColor" strokeOpacity="0.5" strokeWidth="4" strokeLinecap="round">
        <line x1="50" y1="50" x2="50" y2="12" />
        <line x1="50" y1="50" x2="86" y2="35" />
        <line x1="50" y1="50" x2="77" y2="81" />
        <line x1="50" y1="50" x2="23" y2="81" />
        <line x1="50" y1="50" x2="14" y2="35" />
      </g>
      <g stroke="#7dd3fc" strokeOpacity="0.4" strokeWidth="2.6" fill="none">
        <path d="M50 12 Q76 14 86 35" />
        <path d="M23 81 Q50 94 77 81" />
        <path d="M14 35 Q9 60 23 81" />
      </g>
      <circle cx="50" cy="50" r="9" fill="currentColor" />
      <circle cx="50" cy="12" r="6" fill="#7dd3fc" />
      <circle cx="86" cy="35" r="5.4" fill="#c4b5fd" />
      <circle cx="77" cy="81" r="6" fill="#7dd3fc" />
      <circle cx="23" cy="81" r="5.4" fill="#c4b5fd" />
      <circle cx="14" cy="35" r="6" fill="#7dd3fc" />
    </svg>
  );
}

/** 星芒 + ReflexLearn 字标组合。 */
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
