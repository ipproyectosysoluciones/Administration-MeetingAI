// Minutes API client (MIN-104).

import { ApiError } from "../lib/api";
export { ApiError };

export type MinuteStatus = "draft" | "review" | "approved" | "published" | "archived";

export interface Minute {
  id: string;
  meeting_id: string;
  tenant_id: string;
  title: string;
  content: string;
  version: number;
  status: MinuteStatus;
  created_by: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  approved_by: string | null;
  approved_at: string | null;
  published_by: string | null;
  published_at: string | null;
  archived_at: string | null;
  ai_provider: string | null;
  ai_model: string | null;
  ai_request_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface MinuteListResponse {
  items: Minute[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface MinuteCreatePayload {
  title: string;
  content?: string;
  ai_provider?: string;
  ai_model?: string;
  ai_request_id?: string;
}

const API_BASE = import.meta.env.PUBLIC_API_BASE ?? "/api/v1";

async function request<T>(
  path: string,
  accessToken: string,
  init: RequestInit = {},
): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
      ...(init.headers as Record<string, string>),
    },
    credentials: "include",
  });
  if (!resp.ok) {
    let code = "UNKNOWN_ERROR";
    let message = `HTTP ${resp.status}`;
    try {
      const body = (await resp.json()) as { code?: string; message?: string };
      if (body.code) code = body.code;
      if (body.message) message = body.message;
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(resp.status, code, message);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export async function listMinutes(
  token: string,
  meetingId: string,
  params: { page?: number; page_size?: number } = {},
): Promise<MinuteListResponse> {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  const suffix = qs.size ? `?${qs}` : "";
  return request<MinuteListResponse>(`/meetings/${meetingId}/minutes${suffix}`, token);
}

export async function getMinute(token: string, id: string): Promise<Minute> {
  return request<Minute>(`/minutes/${id}`, token);
}

export async function createMinuteDraft(
  token: string,
  meetingId: string,
  payload: MinuteCreatePayload,
): Promise<Minute> {
  return request<Minute>(`/meetings/${meetingId}/minutes`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function reviewMinute(token: string, id: string): Promise<Minute> {
  return request<Minute>(`/minutes/${id}/review`, token, { method: "POST" });
}

export async function approveMinute(token: string, id: string): Promise<Minute> {
  return request<Minute>(`/minutes/${id}/approve`, token, { method: "POST" });
}

export async function publishMinute(token: string, id: string): Promise<Minute> {
  return request<Minute>(`/minutes/${id}/publish`, token, { method: "POST" });
}

export async function archiveMinute(token: string, id: string): Promise<Minute> {
  return request<Minute>(`/minutes/${id}/archive`, token, { method: "POST" });
}
