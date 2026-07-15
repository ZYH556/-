import type { LucideIcon } from "lucide-react";
import {
  BookOpenCheck,
  Bot,
  BrainCircuit,
  ChartNoAxesColumnIncreasing,
  ClipboardCheck,
  Code2,
  FileText,
  GraduationCap,
  Handshake,
  LibraryBig,
  MessageSquareText,
  Network,
  PlayCircle,
  Route,
  ShieldCheck,
  Sparkles,
  UserRoundCheck,
  UsersRound,
  Video,
} from "lucide-react";

export type AgentStatus = "done" | "running" | "waiting";

export interface DemoAgentStep {
  agent: string;
  task: string;
  detail: string;
  status: AgentStatus;
}

export interface RoleView {
  role: string;
  title: string;
  responsibility: string;
  actions: string[];
}

export interface CourseCategory {
  id: string;
  title: string;
  count: number;
  icon: LucideIcon;
}

export interface DemoCourse {
  id: string;
  title: string;
  course: string;
  level: string;
  minutes: number;
  rating: number;
  weakPoint: string;
  reason: string;
  chapters: { title: string; duration: string }[];
}

export interface IndustryCapability {
  title: string;
  current: number;
  target: number;
  status: "advantage" | "focus" | "baseline";
  advice: string;
}

export const activeCourse = {
  subject: "计算机科学",
  grade: "大三",
  course: "Web 前端智能开发",
  target: "AI Agent 开发工程师",
  learner: "admin",
};

export const roleViews: RoleView[] = [
  {
    role: "student",
    title: "学生端",
    responsibility: "一句话提出目标、查看画像、学习路径、资源和视频推荐。",
    actions: ["生成今日任务", "推送薄弱点视频", "提交错题与评论"],
  },
  {
    role: "teacher",
    title: "导师端",
    responsibility: "查看班级薄弱点、介入高风险学习者、确认 AI 资源质量。",
    actions: ["查看辅导报告", "批注学习建议", "回复课程讨论"],
  },
  {
    role: "evaluator",
    title: "评审端",
    responsibility: "追踪 Agent 调用过程、资源质量、知识图谱和学习闭环证据。",
    actions: ["查看差距报告", "审查调用链", "导出过程证据"],
  },
  {
    role: "admin",
    title: "管理员端",
    responsibility: "配置课程、角色权限、资源来源、模型网关和安全策略。",
    actions: ["管理课程库", "配置 Agent", "查看运行状态"],
  },
];

export const courseCategories: CourseCategory[] = [
  { id: "java", title: "JavaEE", count: 128, icon: Code2 },
  { id: "python", title: "Python + 大数据", count: 96, icon: ChartNoAxesColumnIncreasing },
  { id: "frontend", title: "前端开发", count: 85, icon: LibraryBig },
  { id: "linux", title: "Linux 云计算", count: 64, icon: Network },
  { id: "database", title: "数据库", count: 50, icon: ShieldCheck },
  { id: "ai-agent", title: "AI Agent", count: 42, icon: Bot },
];

export const demoCourses: DemoCourse[] = [
  {
    id: "java-basic",
    title: "Java 基础入门 - 从零到精通",
    course: "JavaEE",
    level: "基础",
    minutes: 153,
    rating: 4.8,
    weakPoint: "面向对象基础",
    reason: "最近错题暴露出类、对象、封装概念不稳，适合先用短视频补齐。",
    chapters: [
      { title: "第一章：基础知识介绍", duration: "15:23" },
      { title: "第二章：核心概念详解", duration: "23:45" },
      { title: "第三章：实战案例分析", duration: "31:20" },
      { title: "第四章：高频技巧应用", duration: "28:56" },
      { title: "第五章：项目实战演练", duration: "45:12" },
    ],
  },
  {
    id: "vue-state",
    title: "Vue 3 状态管理与组件通信",
    course: "前端开发",
    level: "进阶",
    minutes: 82,
    rating: 4.7,
    weakPoint: "组件传值、Pinia",
    reason: "学习画像显示你偏视觉学习，但在组件通信和状态分层上还缺案例。",
    chapters: [
      { title: "组件通信场景拆解", duration: "12:18" },
      { title: "Pinia 状态建模", duration: "18:40" },
      { title: "路由与状态联动", duration: "21:06" },
      { title: "项目改造练习", duration: "30:16" },
    ],
  },
  {
    id: "agent-rag",
    title: "RAG 与 Agent 工作流实战",
    course: "AI Agent",
    level: "综合",
    minutes: 110,
    rating: 4.9,
    weakPoint: "RAG、工具调用",
    reason: "目标岗位要求能解释 Agent 调用链，这门课可直接补项目表达。",
    chapters: [
      { title: "RAG 检索增强生成", duration: "22:10" },
      { title: "工具调用与状态机", duration: "26:35" },
      { title: "多 Agent 协作", duration: "28:42" },
      { title: "评测与可观测", duration: "32:33" },
    ],
  },
];

export const industryCapabilities: IndustryCapability[] = [
  {
    title: "行业应用业务方案能力",
    current: 65,
    target: 70,
    status: "baseline",
    advice: "建议通过小型项目实践，学习如何将业务需求转化为技术方案。",
  },
  {
    title: "Agent 智能体开发能力",
    current: 30,
    target: 50,
    status: "focus",
    advice: "建议从基础概念入手，学习 LangGraph、工具调用和可观测链路。",
  },
  {
    title: "AI 大模型应用能力",
    current: 35,
    target: 40,
    status: "baseline",
    advice: "建议学习大模型基本原理，并尝试将其应用于具体场景。",
  },
  {
    title: "代码开发能力",
    current: 75,
    target: 80,
    status: "advantage",
    advice: "继续提升代码质量，学习更高级的前端工程和测试工具。",
  },
  {
    title: "系统架构能力",
    current: 60,
    target: 60,
    status: "baseline",
    advice: "建议深入学习系统分层、接口边界和部署可观测。",
  },
  {
    title: "算法与数据结构",
    current: 50,
    target: 60,
    status: "focus",
    advice: "建议通过刷题平台提升算法能力，同时学习常用数据结构的应用场景。",
  },
];

export const mentorCards = [
  {
    name: "AI 智能导师",
    title: "自适应智能教学",
    match: 83,
    strengths: ["24/7 在线", "薄弱点追踪", "即时资源生成"],
    reason: "最适合快速诊断薄弱环节并生成视频、练习和路径。",
  },
  {
    name: "张教授",
    title: "guide · 初级导师",
    match: 51,
    strengths: ["基础答疑", "课程节奏把控", "学习计划复盘"],
    reason: "适合巩固基础课程概念。",
  },
  {
    name: "陈教授",
    title: "guide · 专家导师",
    match: 51,
    strengths: ["项目指导", "职业规划", "面试表达"],
    reason: "适合阶段性项目复盘与就业方向建议。",
  },
];

export const pageAgentFlows: Record<string, DemoAgentStep[]> = {
  today: [
    { agent: "画像 Agent", task: "读取课程画像", detail: "同步 Web 前端智能开发画像", status: "done" },
    { agent: "规划 Agent", task: "拆解今日任务", detail: "选择 1 个薄弱点与 2 个资源", status: "running" },
    { agent: "资源 Agent", task: "准备推送", detail: "等待学习者确认", status: "waiting" },
  ],
  profile: [
    { agent: "画像 Agent", task: "汇总维度", detail: "专业、年级、知识基础、学习风格", status: "done" },
    { agent: "证据 Agent", task: "关联错题", detail: "识别 React 基础、算法、数据结构", status: "done" },
    { agent: "建议 Agent", task: "生成建议", detail: "输出可执行补强动作", status: "running" },
  ],
  plan: [
    { agent: "路径 Agent", task: "选择画像", detail: "计算机科学 · 大三", status: "done" },
    { agent: "课程 Agent", task: "绑定课程", detail: "Web 前端智能开发", status: "done" },
    { agent: "重排 Agent", task: "智能规划", detail: "按薄弱点优先重排章节", status: "running" },
  ],
  resources: [
    { agent: "文档 Agent", task: "生成讲解", detail: "课程文档与知识点说明", status: "done" },
    { agent: "题库 Agent", task: "生成练习", detail: "匹配薄弱点题型", status: "done" },
    { agent: "视频 Agent", task: "推荐视频", detail: "等待一键推送", status: "running" },
  ],
  "resource-detail": [
    { agent: "资源 Agent", task: "读取资源详情", detail: "同步来源、概念和学习状态", status: "done" },
    { agent: "路径 Agent", task: "检查路径关联", detail: "判断是否可加入当前学习节点", status: "running" },
    { agent: "复盘 Agent", task: "关联错题证据", detail: "提示同概念待复习内容", status: "waiting" },
  ],
  knowledge: [
    { agent: "解析 Agent", task: "等待资料上传", detail: "支持 md / pdf / docx 等课程资料", status: "done" },
    { agent: "检索 Agent", task: "构建私有知识库", detail: "分块、向量化并写入资料索引", status: "running" },
    { agent: "图谱 Agent", task: "抽取概念关系", detail: "可选生成课程知识图谱", status: "waiting" },
  ],
  mistakes: [
    { agent: "错因 Agent", task: "读取错题记录", detail: "识别概念、答案差异与错误类型", status: "done" },
    { agent: "反思 Agent", task: "生成归因", detail: "输出薄弱标签和复习计划", status: "running" },
    { agent: "补救 Agent", task: "联动路径资源", detail: "把错题补救插入学习路径", status: "waiting" },
  ],
  spaces: [
    { agent: "空间 Agent", task: "读取学习目标", detail: "汇总目标、课程和学习资产", status: "done" },
    { agent: "路径 Agent", task: "同步推进状态", detail: "跟踪当前节点与完成进度", status: "running" },
    { agent: "资源 Agent", task: "归档生成内容", detail: "将资料、视频和练习归入空间", status: "waiting" },
  ],
  growth: [
    { agent: "画像 Agent", task: "读取成长快照", detail: "对比薄弱点、目标和能力变化", status: "done" },
    { agent: "证据 Agent", task: "汇总过程记录", detail: "整理对话、资源和路径推进证据", status: "done" },
    { agent: "训练 Agent", task: "准备样本导出", detail: "生成可脱敏的 LoRA 训练样本", status: "running" },
  ],
  chat: [
    { agent: "意图 Agent", task: "解析一句话", detail: "识别生成、推荐、诊断动作", status: "done" },
    { agent: "工具 Agent", task: "调用学习工具", detail: "课程库、错题本、画像库", status: "running" },
    { agent: "导师 Agent", task: "生成答复", detail: "输出下一步行动", status: "waiting" },
  ],
  courses: [
    { agent: "课程 Agent", task: "读取课程库", detail: "按学科与薄弱点过滤", status: "done" },
    { agent: "推荐 Agent", task: "匹配视频", detail: "优先推荐薄弱知识点", status: "running" },
    { agent: "评论 Agent", task: "准备答疑", detail: "课程评论可自动回复", status: "waiting" },
  ],
  industry: [
    { agent: "行业 Agent", task: "读取岗位标准", detail: "AI Agent 开发工程师", status: "done" },
    { agent: "能力 Agent", task: "映射能力项", detail: "业务、Agent、大模型、代码", status: "done" },
    { agent: "建议 Agent", task: "输出画像", detail: "生成就业能力画像", status: "running" },
  ],
  gap: [
    { agent: "画像 Agent", task: "读取我的画像", detail: "9 个学习画像维度", status: "done" },
    { agent: "行业 Agent", task: "读取标准画像", detail: "岗位能力目标", status: "done" },
    { agent: "差距 Agent", task: "对比分析", detail: "生成薄弱能力与建议", status: "running" },
  ],
  mentors: [
    { agent: "匹配 Agent", task: "读取目标学生", detail: "计算机科学 · 大三", status: "done" },
    { agent: "导师 Agent", task: "计算匹配度", detail: "学习风格、薄弱点、课程方向", status: "running" },
    { agent: "调度 Agent", task: "生成辅导入口", detail: "安排 AI 与人工导师", status: "waiting" },
  ],
  coach: [
    { agent: "诊断 Agent", task: "生成追问", detail: "3-5 个定位问题", status: "done" },
    { agent: "错题 Agent", task: "分析薄弱点", detail: "React 基础、fastApi、算法", status: "running" },
    { agent: "视频 Agent", task: "推送资源", detail: "一句话生成薄弱点视频", status: "waiting" },
  ],
};

export const agentIconMap: Record<AgentStatus, LucideIcon> = {
  done: ClipboardCheck,
  running: Sparkles,
  waiting: MessageSquareText,
};

export const featureGaps = [
  { icon: GraduationCap, label: "围绕一门课", done: true, note: "已补课程中心与课程播放页" },
  { icon: UsersRound, label: "分角色", done: true, note: "学生、导师、评审、管理员视图" },
  { icon: BrainCircuit, label: "Agent 调用过程", done: true, note: "每个新增页面显示调用链" },
  { icon: PlayCircle, label: "一句话推送视频", done: true, note: "输入动作后生成薄弱点视频推荐" },
  { icon: Handshake, label: "导师匹配", done: true, note: "按目标画像展示匹配度" },
  { icon: FileText, label: "差距报告", done: true, note: "与岗位标准能力对比" },
];

export const quickToolActions = [
  { label: "查看掌握度热力图", target: "/profile" },
  { label: "生成专项练习", target: "/resources" },
  { label: "推荐关联资源", target: "/courses" },
  { label: "标记易错点", target: "/mistakes" },
  { label: "开启 AI 视频面试辅导", target: "/coach" },
];

export const recommendedVideo = {
  icon: Video,
  title: "Vue 3 组件通信与 Pinia 状态管理",
  source: "根据薄弱点：组件传值、Pinia、Vue 进阶部分",
  duration: "18 分钟",
  action: "已生成推送卡片",
};

export const oneSentenceAgentSteps = [
  { label: "意图识别", detail: "识别为薄弱点视频推送任务" },
  { label: "画像匹配", detail: "读取组件通信、Pinia 等薄弱标签" },
  { label: "视频筛选", detail: "选择 18 分钟短视频并绑定课程" },
];
