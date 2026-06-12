import {
  BookOpen,
  Clapperboard,
  Code2,
  FileText,
  ListChecks,
  MessagesSquare,
  Network,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

export interface ResourceMeta {
  label: string;
  icon: LucideIcon;
  chipClass: string;
}

const META: Record<string, ResourceMeta> = {
  doc: { label: "学习文档", icon: FileText, chipClass: "bg-sky-100 text-sky-800" },
  mindmap: { label: "思维导图", icon: Network, chipClass: "bg-emerald-100 text-emerald-800" },
  code: { label: "代码练习", icon: Code2, chipClass: "bg-slate-200 text-slate-800" },
  quiz: { label: "练习题", icon: ListChecks, chipClass: "bg-violet-100 text-violet-800" },
  reading: { label: "拓展阅读", icon: BookOpen, chipClass: "bg-amber-100 text-amber-800" },
  video: { label: "视频脚本", icon: Clapperboard, chipClass: "bg-rose-100 text-rose-800" },
  debate: { label: "辩论实录", icon: MessagesSquare, chipClass: "bg-indigo-100 text-indigo-800" },
};

export function resourceMeta(type: string): ResourceMeta {
  return (
    META[type] ?? {
      label: type || "资源",
      icon: Sparkles,
      chipClass: "bg-slate-100 text-slate-700",
    }
  );
}
