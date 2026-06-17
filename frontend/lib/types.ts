export type ResourceType =
  | "doc"
  | "quiz"
  | "mindmap"
  | "code"
  | "reading"
  | "video"
  | "debate";

export interface ResourceCard {
  type: ResourceType;
  task_id: string;
  content: string;
  streaming?: boolean; // 流式增量进行中（PERF-A），末帧 resource_card 落定后转 false
}

export interface ResourceDelta {
  task_id: string;
  type?: ResourceType;
  delta: string;
  reset?: boolean; // 新一轮生成开始：清空该 task 已累积的增量
}

export interface AgentStep {
  step: string;
  detail?: string;
  message?: string;
}

export interface DebatePosition {
  perspective?: string;
  claim?: string;
  evidence_summary?: string;
  confidence?: number;
}

export interface DebateRound {
  round: number;
  positions: DebatePosition[];
}

export interface JudgeVerdict {
  winner_position: string;
  reasoning: string;
  confidence: number;
}

export interface LearningPathStep {
  sequence: number;
  task_id: string;
  resource_type: string;
  concept?: string;
  objective?: string;
  rationale?: string;
  difficulty?: number;
  depends_on?: string[];
}

export interface LearningPath {
  steps: LearningPathStep[];
  summary?: string;
  strategy?: string;
}

export type UserRole = "student" | "teacher" | "admin" | "evaluator";

export interface CurrentUser {
  user_id: string;
  tenant_id: string;
  role: UserRole;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: CurrentUser;
}

export interface SSEMessage {
  event: string;
  data: unknown;
}

export interface IngestResult {
  doc_id: string;
  title: string;
  format: string;
  chunks: number;
  embedded: number;
  qdrant_written: number;
  pg_written: boolean;
  contextual: boolean;
  graph: string;
  graph_concepts: number;
  graph_relations: number;
  degraded: string[];
  status: string;
}

export interface VideoJob {
  job_id: string;
  user_id?: string;
  tenant_id?: string;
  status: string;
  storyboard: string;
  video_url: string | null;
  error: string | null;
  created_at: number;
}

export interface MistakeItem {
  mistake_id: string;
  question: string;
  answer: string;
  expected: string;
  concept: string;
  status: string;
  analysis?: Record<string, unknown>;
  created_at: number;
  degraded: string[];
}

export interface MistakeReflection {
  mistake_id: string;
  category: string;
  cause: string;
  evidence: string[];
  remedial_goal: string;
  difficulty: number;
}

export interface MistakeReview {
  mistake_id: string;
  cause: string;
  weakness_tags: string[];
  review_plan: string[];
  refine_hint: string;
  recommended_resource_types: string[];
}

export interface MistakePlan {
  mistake_id: string;
  remedial_goal: string;
  steps: LearningPathStep[];
  summary: string;
  strategy: string;
}

export interface MistakeResource {
  resource_id: string;
  mistake_id: string;
  type: string;
  title: string;
  content: string;
}

export interface CollaborationTraceEvent {
  trace_id: string;
  session_id: string;
  node: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: number;
}

export interface TrainingMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface LoraSampleMetadata {
  sample_id: string;
  session_id: string;
  source_trace_ids: string[];
  nodes: string[];
  user_hash: string;
  tenant_hash: string;
  sanitized: boolean;
  created_at: number;
}

export interface LoraSftSample {
  messages: TrainingMessage[];
  metadata: LoraSampleMetadata;
}

export interface LoraExportRecord {
  file_path: string;
  sample_count: number;
  created_at: number;
  sanitized: boolean;
}

export interface LoraExportResult {
  sample_count: number;
  filtered_count: number;
  file_path: string;
  latest_file_path: string;
  sanitized: boolean;
  items: LoraSftSample[];
}

export interface LearningSpace {
  space_id: string;
  title: string;
  status: string;
}

export interface SpacePathStep {
  sequence: number;
  task_ref: string;
  resource_type: string;
  concept: string;
  objective: string;
  rationale: string;
  difficulty: number;
  mastery_status: string;
}

export interface SpaceResource {
  resource_id: string;
  type: string;
  title: string;
  concept: string;
  content: string;
  quality_score?: number | null;
}

export interface SpaceDetail {
  space_id: string;
  user_id: string;
  tenant_id: string;
  title: string;
  course: string;
  status: string;
  progress: number;
  path_summary: string;
  path_strategy: string;
  steps: SpacePathStep[];
  resources: SpaceResource[];
  degraded: string[];
}

export interface MistakeStats {
  total: number;
  open: number;
  top_concepts: string[];
}

export interface StudyStats {
  total: number;
  in_progress: number;
  done: number;
  reviewed: number;
}

export interface ProfileSummary {
  user_id: string;
  goal: string;
  knowledge_base: Record<string, number>;
  weak_points: string[];
  cognitive_style: string;
  preferences: Record<string, unknown>;
  progress: number;
  mistake_stats: MistakeStats;
  study_stats: StudyStats;
  spaces_count: number;
  resources_count: number;
  source: string;
  degraded: string[];
}

export interface ProfileHistorySnapshot {
  version: number;
  created_at: number;
  goal: string;
  progress: number;
  weak_points: string[];
  knowledge_base: Record<string, number>;
  completed_resources: number;
}

export interface ProfileTrend {
  items: ProfileHistorySnapshot[];
  start_progress: number;
  latest_progress: number;
  progress_delta: number;
  resolved_weak_points: string[];
  new_weak_points: string[];
  mastery_delta: Record<string, number>;
  degraded: string[];
}

export interface TutorReply {
  answer: string;
  degraded: boolean;
  blocked: boolean;
  reasons: string[];
}

export interface KnowledgeDocument {
  doc_id: string;
  title: string;
  visibility: string;
  course_id: string;
  format: string;
}

export type {
  TodayLearningPathNode,
  TodayPathStatus,
  TodayProfileSignal,
  TodayQuickActionView,
  TodayResource,
  TodayResourceKind,
  TodayResourceView,
  TodayReviewItem,
  TodayReviewItemView,
  TodaySummary,
  TodaySummaryView,
  TodayTask,
  TodayTaskView,
} from "./todayTypes";

export type { LearningResource, LearningResourceKind } from "./resourceTypes";
