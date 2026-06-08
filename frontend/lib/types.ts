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
  status: string;
  storyboard: string;
  video_url: string | null;
  error: string | null;
  created_at: number;
}
