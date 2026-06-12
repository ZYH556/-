export type LearningResourceKind =
  | "external_video"
  | "official_doc"
  | "oer"
  | "ai_document"
  | "quiz"
  | "user_upload"
  | "doc"
  | "reading"
  | "video"
  | "code"
  | "mindmap"
  | "debate";

export interface LearningResource {
  resource_id: string;
  type: LearningResourceKind | string;
  title: string;
  content_preview: string;
  visibility: string;
  provider: string;
  source_label: string;
  href: string;
  embed_url: string;
  usage_mode: string;
  source_policy: string;
  estimated_minutes: number;
  reason: string;
}
