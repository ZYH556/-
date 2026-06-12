import { apiJson } from "@/lib/apiClient";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

export interface ResourceDiscoveryRequest {
  goal: string;
  weak_points: string[];
  providers: Array<"bilibili" | "official_doc" | "oer">;
  limit: number;
}

export interface ResourceCandidate {
  resource_id: string;
  type: string;
  title: string;
  content_preview: string;
  provider: string;
  source_label: string;
  href: string;
  embed_url: string;
  usage_mode: string;
  source_policy: string;
  estimated_minutes: number;
  reason: string;
  matched_goal: string;
  matched_weak_points: string[];
  rank_score: number;
}

export interface ResourceDiscoveryResult {
  items: ResourceCandidate[];
  query: {
    goal: string;
    weak_points: string[];
    providers: Array<"bilibili" | "official_doc" | "oer">;
  };
  degraded: string[];
}

export function discoverResources(
  token: string,
  request: ResourceDiscoveryRequest,
): Promise<ResourceDiscoveryResult> {
  return apiJson<ResourceDiscoveryResult>(`${API_BASE}/resources/discover`, token, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export interface SaveResourceResult {
  resource_id: string;
  saved: boolean;
  duplicate: boolean;
  degraded: string[];
}

/* 候选资源一键入库：candidate_id 作幂等键，重复保存后端返回 duplicate 不重复插 */
export function saveCandidate(
  token: string,
  candidate: ResourceCandidate,
): Promise<SaveResourceResult> {
  return apiJson<SaveResourceResult>(`${API_BASE}/resources/save`, token, {
    method: "POST",
    body: JSON.stringify({
      candidate_id: candidate.resource_id,
      type: candidate.type,
      title: candidate.title,
      provider: candidate.provider,
      source_label: candidate.source_label,
      href: candidate.href,
      embed_url: candidate.embed_url,
      usage_mode: candidate.usage_mode,
      source_policy: candidate.source_policy,
      estimated_minutes: candidate.estimated_minutes,
      reason: candidate.reason,
      content_preview: candidate.content_preview,
      concept: candidate.matched_weak_points[0] ?? candidate.matched_goal,
    }),
  });
}
