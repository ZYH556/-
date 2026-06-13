import { apiJson } from "@/lib/apiClient";
import type { LearningResource } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

export type StudyStatus = "unread" | "in_progress" | "done" | "reviewed";

export interface ResourceDetail {
  resource: LearningResource;
  content: string;
  study_status: StudyStatus;
  status_updated_at: number | null;
  goal_id: string;
  goal_title: string;
  related_open_mistakes: number;
  degraded: string[];
}

export interface StudyStatusResult {
  resource_id: string;
  study_status: StudyStatus;
  status_updated_at: number;
  degraded: string[];
}

export function getResourceDetail(token: string, resourceId: string): Promise<ResourceDetail> {
  return apiJson<ResourceDetail>(
    `${API_BASE}/resources/${encodeURIComponent(resourceId)}/detail`,
    token,
  );
}

export function updateResourceStatus(
  token: string,
  resourceId: string,
  status: StudyStatus,
): Promise<StudyStatusResult> {
  return apiJson<StudyStatusResult>(
    `${API_BASE}/resources/${encodeURIComponent(resourceId)}/status`,
    token,
    { method: "PATCH", body: JSON.stringify({ status }) },
  );
}
