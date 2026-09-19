// Meetings API client (TASK-230..232).

import { ApiError, type TokenResponse } from "../lib/api";
export { ApiError };

const API_BASE = import.meta.env.PUBLIC_API_BASE ?? "/api/v1";

export type MeetingModality = "in_person" | "virtual" | "hybrid";
export type MeetingStatus = "scheduled" | "in_progress" | "finished" | "cancelled";

export interface Meeting {
  id: string;
  organization_id: string;
  title: string;
  description: string | null;
  starts_at: string;
  ends_at: string;
  location: string | null;
  modality: MeetingModality;
  status: MeetingStatus;
  created_at: string;
  updated_at: string;
}

export interface MeetingListResponse {
  items: Meeting[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface MeetingCreatePayload {
  title: string;
  description?: string;
  starts_at: string;
  ends_at: string;
  location?: string;
  modality?: MeetingModality;
}

export type MeetingUpdatePayload = Partial<MeetingCreatePayload> & { status?: MeetingStatus };

export interface Participant {
  id: string;
  meeting_id: string;
  user_id: string | null;
  external_email: string | null;
  role: string;
  created_at: string;
}

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

export async function listMeetings(
  token: string,
  params: { page?: number; page_size?: number; status?: string; q?: string } = {},
): Promise<MeetingListResponse> {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  if (params.status) qs.set("status", params.status);
  if (params.q) qs.set("q", params.q);
  const suffix = qs.size ? `?${qs}` : "";
  return request<MeetingListResponse>(`/meetings${suffix}`, token);
}

export async function getMeeting(token: string, id: string): Promise<Meeting> {
  return request<Meeting>(`/meetings/${id}`, token);
}

export async function createMeeting(
  token: string,
  payload: MeetingCreatePayload,
): Promise<Meeting> {
  return request<Meeting>("/meetings", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateMeeting(
  token: string,
  id: string,
  payload: MeetingUpdatePayload,
): Promise<Meeting> {
  return request<Meeting>(`/meetings/${id}`, token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function cancelMeeting(token: string, id: string): Promise<Meeting> {
  return request<Meeting>(`/meetings/${id}/cancel`, token, { method: "POST" });
}

export async function listParticipants(
  token: string,
  meetingId: string,
): Promise<{ items: Participant[]; total: number }> {
  return request(`/meetings/${meetingId}/participants`, token);
}

export async function addParticipant(
  token: string,
  meetingId: string,
  payload: { user_id?: string; external_email?: string; role?: string },
): Promise<Participant> {
  return request(`/meetings/${meetingId}/participants`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function removeParticipant(
  token: string,
  meetingId: string,
  participantId: string,
): Promise<void> {
  await request(`/meetings/${meetingId}/participants/${participantId}`, token, {
    method: "DELETE",
  });
}
