import {
  BookOpenText,
  ClipboardCheck,
  Code2,
  FileText,
  MessagesSquare,
  Network,
  PlaySquare,
  UploadCloud,
  type LucideIcon,
} from "lucide-react";

export type ResourceView = {
  label: string;
  action: string;
  icon: LucideIcon;
  tone: string;
};

const RESOURCE_VIEW: Record<string, ResourceView> = {
  external_video: {
    label: "外部视频",
    action: "观看",
    icon: PlaySquare,
    tone: "bg-rose-50 text-rose-700",
  },
  official_doc: {
    label: "官方资料",
    action: "打开来源",
    icon: BookOpenText,
    tone: "bg-emerald-50 text-emerald-700",
  },
  oer: {
    label: "开放课程",
    action: "打开课程",
    icon: BookOpenText,
    tone: "bg-indigo-50 text-indigo-700",
  },
  ai_document: {
    label: "AI 讲解文档",
    action: "阅读",
    icon: FileText,
    tone: "bg-cyan-50 text-cyan-700",
  },
  quiz: {
    label: "针对练习",
    action: "开始练习",
    icon: ClipboardCheck,
    tone: "bg-amber-50 text-amber-700",
  },
  user_upload: {
    label: "个人资料",
    action: "查看资料",
    icon: UploadCloud,
    tone: "bg-slate-100 text-slate-700",
  },
  code: { label: "代码案例", action: "查看", icon: Code2, tone: "bg-violet-50 text-violet-700" },
  reading: { label: "阅读材料", action: "阅读", icon: BookOpenText, tone: "bg-indigo-50 text-indigo-700" },
  doc: { label: "讲解文档", action: "阅读", icon: FileText, tone: "bg-cyan-50 text-cyan-700" },
  video: { label: "视频资源", action: "观看", icon: PlaySquare, tone: "bg-rose-50 text-rose-700" },
  mindmap: { label: "思维导图", action: "查看", icon: Network, tone: "bg-emerald-50 text-emerald-700" },
  debate: { label: "观点辨析", action: "查看", icon: MessagesSquare, tone: "bg-amber-50 text-amber-700" },
};

export function viewForResource(type: string): ResourceView {
  return (
    RESOURCE_VIEW[type] ?? {
      label: "学习资源",
      action: "查看",
      icon: FileText,
      tone: "bg-slate-100 text-slate-700",
    }
  );
}

export function isExternalHref(href: string): boolean {
  return href.startsWith("http://") || href.startsWith("https://");
}
