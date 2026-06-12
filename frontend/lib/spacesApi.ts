import { apiJson } from "@/lib/apiClient";
import type { SpaceDetail } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

export function getSpaceDetail(token: string, spaceId: string): Promise<SpaceDetail> {
  return apiJson<SpaceDetail>(`${API_BASE}/spaces/${spaceId}/detail`, token);
}
