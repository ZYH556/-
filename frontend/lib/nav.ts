export interface NavItem {
  id: string;
  label: string;
  href: string;
  description: string;
}

export const workspaceNavItems: NavItem[] = [
  { id: "today", label: "今日学习", href: "/today", description: "今天该学什么、从哪里开始" },
  { id: "profile", label: "学习画像", href: "/profile", description: "查看系统如何理解你的目标与薄弱点" },
  { id: "industry", label: "行业画像", href: "/industry", description: "查看目标岗位能力标准" },
  { id: "gap", label: "AI 差距分析", href: "/gap", description: "对比我的画像与行业画像" },
  { id: "chat", label: "AI 导师", href: "/chat", description: "1 对 1 对话：诊断、规划与资源生成" },
  { id: "coach", label: "智能辅导", href: "/coach", description: "一句话触发诊断、练习和视频推送" },
  { id: "mentors", label: "导师匹配", href: "/mentors", description: "匹配 AI 与人工导师" },
  { id: "spaces", label: "学习空间", href: "/spaces", description: "按目标组织个人学习资产" },
  { id: "plan", label: "学习路径", href: "/plan", description: "查看个性化路径与进度" },
  { id: "courses", label: "精品课程", href: "/courses", description: "围绕课程查看视频与学习资源" },
  { id: "resources", label: "资源库", href: "/resources", description: "管理已生成学习资源" },
  { id: "knowledge", label: "个人知识库", href: "/knowledge", description: "上传和管理私有资料" },
  { id: "mistakes", label: "错题本", href: "/mistakes", description: "沉淀错因并触发复习" },
  { id: "growth", label: "成长档案", href: "/growth", description: "能力随时间的变化与自进化轨迹" },
];

export const publicTracks: NavItem[] = [
  { id: "ai-programming", label: "AI / 编程", href: "/tracks/ai-programming", description: "机器学习、工程实践与作品集训练" },
  { id: "career", label: "求职能力", href: "/tracks/career", description: "面试、简历、项目表达与复盘" },
  { id: "cert", label: "考证备考", href: "/tracks/cert", description: "知识点图谱、刷题与错因闭环" },
];
