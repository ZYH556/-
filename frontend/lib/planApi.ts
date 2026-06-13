import { apiJson } from "@/lib/apiClient";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

export type PlanItemStatus = "not_started" | "in_progress" | "done";

export interface PathOpResult {
  ok: boolean;
  item_id: number;
  mastery_status: string;
  goal_progress: number;
  done_items: number;
  total_items: number;
  degraded: string[];
}

export function updatePlanItemStatus(
  token: string,
  itemId: number,
  status: PlanItemStatus,
): Promise<PathOpResult> {
  return apiJson<PathOpResult>(`${API_BASE}/plan/items/${itemId}/status`, token, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function insertRemedialItem(
  token: string,
  afterItemId: number,
  concept: string,
  objective = "",
): Promise<PathOpResult> {
  return apiJson<PathOpResult>(`${API_BASE}/plan/items/insert`, token, {
    method: "POST",
    body: JSON.stringify({
      after_item_id: afterItemId,
      concept,
      objective,
    }),
  });
}
