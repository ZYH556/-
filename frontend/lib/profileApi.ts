import { apiJson } from "@/lib/apiClient";
import type { ProfileSummary, ProfileTrend } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

export function getProfileSummary(token: string): Promise<ProfileSummary> {
  return apiJson<ProfileSummary>(`${API_BASE}/profile`, token);
}

export function getProfileHistory(token: string): Promise<ProfileTrend> {
  return apiJson<ProfileTrend>(`${API_BASE}/profile/history`, token);
}
