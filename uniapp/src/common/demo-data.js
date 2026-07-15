const topics = [
  "Vue 3 组件通信",
  "Pinia 状态管理",
  "React Hooks 基础",
  "FastAPI 路由设计",
  "MySQL 索引优化",
  "数据结构与算法",
  "RAG 检索增强生成",
  "Agent 工具调用",
  "软件杯项目答辩",
  "前端工程化实践",
  "知识图谱构建",
  "错题归因复盘",
];

const formats = ["pdf", "docx", "md", "pptx", "txt"];

export const activeCourse = {
  subject: "计算机科学",
  grade: "大三",
  course: "Web 前端智能开发",
  target: "AI Agent 开发工程师",
  learner: "admin",
};

export const agentFlows = {
  today: [
    ["画像 Agent", "读取课程画像", "同步专业、年级、薄弱点"],
    ["规划 Agent", "生成今日任务", "选择 1 个主任务与 2 个资源"],
    ["资源 Agent", "准备推送", "等待学习者确认"],
  ],
  knowledge: [
    ["解析 Agent", "扫描知识文档", "236 份文档进入候选池"],
    ["检索 Agent", "持续调用资料", "按薄弱点检索课程资料"],
    ["图谱 Agent", "抽取概念关系", "生成知识点关联证据"],
  ],
  coach: [
    ["诊断 Agent", "理解一句话需求", "识别组件通信与状态管理"],
    ["错题 Agent", "关联薄弱点", "命中 Vue / Pinia / 算法"],
    ["视频 Agent", "推送资源", "生成短视频与专项练习"],
  ],
  course: [
    ["课程 Agent", "读取课程目录", "围绕一门课组织章节"],
    ["推荐 Agent", "匹配薄弱视频", "优先补齐 Pinia 与组件通信"],
    ["评论 Agent", "生成智能回复", "辅助课程讨论答疑"],
  ],
  profile: [
    ["画像 Agent", "汇总学习画像", "9 个维度完成更新"],
    ["行业 Agent", "读取岗位标准", "AI Agent 开发工程师"],
    ["差距 Agent", "生成建议", "输出能力差距与导师推荐"],
  ],
};

export const knowledgeDocs = Array.from({ length: 236 }, (_, index) => {
  const serial = String(index + 1).padStart(3, "0");
  return {
    id: `doc-${serial}`,
    title: `${topics[index % topics.length]} · 课程知识文档 ${serial}`,
    course: index % 3 === 0 ? "Web 前端智能开发" : index % 3 === 1 ? "AI Agent 实战" : "软件工程综合实践",
    format: formats[index % formats.length],
    visibility: index % 5 === 0 ? "班级共享" : "私有",
  };
});

export const userNeeds = Array.from({ length: 64 }, (_, index) => ({
  id: `need-${index + 1}`,
  text: `用户需求 ${index + 1}: ${topics[index % topics.length]} 学习支持`,
}));

export const weakPoints = ["组件通信", "Pinia", "React Hooks", "算法复杂度", "RAG 工具调用", "MySQL 索引"];

export const courses = [
  {
    id: "vue-state",
    title: "Vue 3 状态管理与组件通信",
    weakPoint: "组件传值、Pinia",
    minutes: 82,
    progress: 46,
    chapters: ["组件通信场景拆解", "Pinia 状态建模", "路由与状态联动", "项目改造练习"],
  },
  {
    id: "agent-rag",
    title: "RAG 与 Agent 工作流实战",
    weakPoint: "RAG、工具调用",
    minutes: 110,
    progress: 28,
    chapters: ["检索增强生成", "工具调用与状态机", "多 Agent 协作", "评测与可观测"],
  },
  {
    id: "java-basic",
    title: "Java 基础入门 - 从零到精通",
    weakPoint: "面向对象基础",
    minutes: 153,
    progress: 62,
    chapters: ["基础知识介绍", "核心概念详解", "实战案例分析", "项目实战演练"],
  },
];

export const capabilityGaps = [
  { label: "Agent 智能体开发能力", current: 30, target: 50, status: "重点提升" },
  { label: "AI 大模型应用能力", current: 35, target: 40, status: "补齐案例" },
  { label: "代码开发能力", current: 75, target: 80, status: "保持优势" },
  { label: "算法与数据结构", current: 50, target: 60, status: "专项练习" },
];

export const mentorCards = [
  { name: "AI 智能导师", title: "自适应智能教学", match: 83 },
  { name: "张教授", title: "guide · 初级导师", match: 51 },
  { name: "陈教授", title: "guide · 专家导师", match: 51 },
];
