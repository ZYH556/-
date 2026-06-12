export type TodayResourceKind =
  | "external_video"
  | "ai_document"
  | "quiz"
  | "official_doc"
  | "oer"
  | "user_upload";

export type TodayPathStatus = "done" | "current" | "next";

export interface TodayTask {
  title: string;
  reason: string;
  estimated_minutes: number;
  space_id: string;
  space_name: string;
  path_node: string;
  primary_action: string;
}

export interface TodayResource {
  id: string;
  type: TodayResourceKind;
  title: string;
  provider: string;
  source_label: string;
  estimated_minutes: number;
  reason: string;
  href: string;
  embed_url: string;
  usage_mode: string;
  source_policy: string;
}

export interface TodayLearningPathNode {
  id: string;
  title: string;
  status: TodayPathStatus;
  summary: string;
}

export interface TodayProfileSignal {
  label: string;
  value: string;
}

export interface TodayReviewItem {
  topic: string;
  reason: string;
  due_label: string;
}

export interface TodaySummary {
  user_id: string;
  greeting: string;
  current_goal: string;
  progress: number;
  main_task: TodayTask;
  path_nodes: TodayLearningPathNode[];
  path_recommendation: string;
  resources: TodayResource[];
  tutor_prompt: string;
  quick_actions: TodayProfileSignal[];
  profile_signals: TodayProfileSignal[];
  review_queue: TodayReviewItem[];
  degraded: string[];
}

export interface TodayTaskView {
  title: string;
  reason: string;
  estimatedMinutes: number;
  spaceId: string;
  spaceName: string;
  pathNode: string;
  primaryAction: string;
}

export interface TodayResourceView {
  id: string;
  type: TodayResourceKind;
  title: string;
  provider: string;
  sourceLabel: string;
  estimatedMinutes: number;
  reason: string;
  href: string;
}

export interface TodayReviewItemView {
  topic: string;
  reason: string;
  dueLabel: string;
}

export interface TodayQuickActionView {
  id: string;
  label: string;
  description: string;
  href: string;
  icon: "upload" | "mistake" | "practice" | "goal";
}

export interface TodaySummaryView {
  userId: string;
  greeting: string;
  currentGoal: string;
  progress: number;
  mainTask: TodayTaskView;
  pathNodes: TodayLearningPathNode[];
  pathRecommendation: string;
  resources: TodayResourceView[];
  tutorPrompt: string;
  quickActions: TodayQuickActionView[];
  profileSignals: TodayProfileSignal[];
  reviewQueue: TodayReviewItemView[];
  degraded: string[];
}
