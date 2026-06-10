export interface NavItem {
  id: string;
  label: string;
  href: string;
  description: string;
}

export const workspaceNavItems: NavItem[] = [
  { id: "spaces", label: "学习空间", href: "/spaces", description: "按目标组织个人学习资产" },
  { id: "chat", label: "对话工作区", href: "/chat", description: "发起多智能体协作生成资源" },
  { id: "plan", label: "学习路径", href: "/plan", description: "查看个性化路径与进度" },
  { id: "resources", label: "资源库", href: "/resources", description: "管理已生成学习资源" },
  { id: "knowledge", label: "个人知识库", href: "/knowledge", description: "上传和管理私有资料" },
  { id: "mistakes", label: "错题本", href: "/mistakes", description: "沉淀错因并触发复习" },
  { id: "growth", label: "成长档案", href: "/growth", description: "查看画像和自进化轨迹" },
];

export const publicTracks: NavItem[] = [
  { id: "ai-programming", label: "AI / 编程", href: "/tracks/ai-programming", description: "机器学习、工程实践与作品集训练" },
  { id: "career", label: "求职能力", href: "/tracks/career", description: "面试、简历、项目表达与复盘" },
  { id: "cert", label: "考证备考", href: "/tracks/cert", description: "知识点图谱、刷题与错因闭环" },
];
