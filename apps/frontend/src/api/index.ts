import { api, ApiError } from '@/lib/api/client';
import type { MinuteResponse, MinuteListResponse, MinuteCreateRequest, MinuteUpdateRequest, MinuteVersionListResponse } from '@/types/minutes';

export const minutesApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    q?: string;
  }) => api.get<MinuteListResponse>('/meetings/:meetingId/minutes', params),

  get: (minuteId: string) => api.get<MinuteResponse>(`/minutes/${minuteId}`),

  create: (meetingId: string, data: MinuteCreateRequest) =>
    api.post<{ id: string }>(`/meetings/${meetingId}/minutes`, data),

  generate: (meetingId: string) =>
    api.post<{ id: string }>(`/meetings/${meetingId}/minutes/generate`, {}),

  update: (minuteId: string, data: MinuteUpdateRequest) =>
    api.patch<{ id: string }>(`/minutes/${minuteId}`, data),

  review: (minuteId: string) =>
    api.post<{ id: string }>(`/minutes/${minuteId}/review`, {}),

  approve: (minuteId: string) =>
    api.post<{ id: string }>(`/minutes/${minuteId}/approve`, {}),

  publish: (minuteId: string) =>
    api.post<{ id: string }>(`/minutes/${minuteId}/publish`, {}),

  archive: (minuteId: string) =>
    api.post<{ id: string }>(`/minutes/${minuteId}/archive`, {}),

  listVersions: (minuteId: string, params?: { page?: number; page_size?: number; search?: string }) =>
    api.get<MinuteVersionListResponse>(`/minutes/${minuteId}/versions`, params),

  delete: (minuteId: string) => api.delete<void>(`/minutes/${minuteId}`),
};

export const meetingsApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    q?: string;
  }) => api.get<{ items: any[]; total: number; page: number; page_size: number; pages: number }>('/meetings', params),

  get: (meetingId: string) => api.get<any>(`/meetings/${meetingId}`),

  create: (data: { title: string; description?: string; starts_at: string; ends_at: string; location?: string; modality?: string }) =>
    api.post<{ id: string }>('/meetings', data),

  update: (meetingId: string, data: Partial<{ title: string; description?: string; starts_at: string; ends_at: string; location?: string; modality?: string; status?: string }>) =>
    api.patch<{ id: string }>(`/meetings/${meetingId}`, data),

  cancel: (meetingId: string) =>
    api.post<{ id: string }>(`/meetings/${meetingId}/cancel`, {}),

  addParticipant: (meetingId: string, data: { user_id?: string; external_email?: string; role?: string }) =>
    api.post<{ id: string }>(`/meetings/${meetingId}/participants`, data),

  removeParticipant: (meetingId: string, participantId: string) =>
    api.delete(`/meetings/${meetingId}/participants/${participantId}`),
};

export const recordingsApi = {
  // TODO(#119): el backend no expone GET /recordings global; dashboard necesita listado global.
  list: (params?: { page?: number; page_size?: number; status?: string; q?: string }) =>
    api.get<{ items: any[]; total: number; page: number; page_size: number; pages: number }>('/recordings', params),

  listByMeeting: (meetingId: string) => api.get<any[]>(`/meetings/${meetingId}/recordings`),

  get: (recordingId: string) => api.get<any>(`/recordings/${recordingId}`),

  upload: (file: File, metadata: { title?: string; meeting_id?: string; [k: string]: any }) =>
    api.upload<any>('/recordings', file, Object.fromEntries(Object.entries(metadata).map(([k, v]) => [k, String(v)]))),

  download: (recordingId: string) =>
    api.getBlob(`/recordings/${recordingId}/content`),

  delete: (recordingId: string) => api.delete(`/recordings/${recordingId}`),
};

export const transcriptionsApi = {
  // TODO(#119): el backend no expone GET /transcriptions global; dashboard necesita listado global.
  list: (params?: { page?: number; page_size?: number }) =>
    api.get<{ items: any[]; total: number; page: number; page_size: number; pages: number }>('/transcriptions', params),

  listByMeeting: (meetingId: string) => api.get<any[]>(`/meetings/${meetingId}/transcriptions`),

  get: (transcriptionId: string) => api.get<any>(`/transcriptions/${transcriptionId}`),

  createDraft: (meetingId: string) =>
    api.post<{ id: string }>(`/meetings/${meetingId}/transcriptions`, {}),

  listRecordings: (recordingId: string) => api.get<any[]>(`/recordings/${recordingId}/transcriptions`),
};

export const documentsApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    type?: string;
    q?: string;
  }) => api.get<{ items: any[]; total: number; page: number; page_size: number; pages: number }>('/documents', params),

  get: (documentId: string) => api.get<any>(`/documents/${documentId}`),

  create: (data: { title: string; description?: string; type: string; meeting_id?: string }) =>
    api.post<{ id: string }>('/documents', data),

  update: (documentId: string, data: { title?: string; description?: string; meeting_id?: string }) =>
    api.patch<{ id: string }>(`/documents/${documentId}`, data),

  delete: (documentId: string) => api.delete(`/documents/${documentId}`),

  upload: (file: File, data: { title: string; type: string; meeting_id?: string; description?: string }) =>
    api.upload<any>('/documents/upload', file, data),

  download: (documentId: string, version?: number) =>
    api.getBlob(`/documents/${documentId}/content`, version !== undefined ? { version } : undefined),

  listVersions: (documentId: string, params?: { page?: number; page_size?: number }) =>
    api.get<{ items: any[]; total: number; page: number; page_size: number; pages: number }>(`/documents/${documentId}/versions`, params),

  createVersion: (documentId: string, data: {
    file_path: string;
    file_size: number;
    sha256: string;
    ocr_text?: string;
    ocr_confidence?: number;
    ocr_status?: string;
    pages?: number;
    metadata_json?: Record<string, any>;
  }) => api.post<any>(`/documents/${documentId}/versions`, data),

  triggerOcr: (documentId: string) => api.post<any>(`/documents/${documentId}/ocr`, {}),
};

export const jobsApi = {
  enqueueTranscription: (recordingId: string, meetingId?: string, language = 'es', diarize = true) =>
    api.post<{ job_id: string; status: string }>('/jobs/transcribe', {
      recording_id: recordingId,
      meeting_id: meetingId,
      language,
      diarize,
    }),

  enqueueOcr: (documentId: string) =>
    api.post<{ job_id: string; status: string }>('/jobs/ocr', { document_id: documentId }),

  enqueueAiProcessing: (meetingId: string, transcriptionId: string, documentIds?: string[]) =>
    api.post<{ job_id: string; status: string }>('/jobs/ai-process', {
      meeting_id: meetingId,
      transcription_id: transcriptionId,
      document_ids: documentIds,
    }),

  list: (params?: { page?: number; page_size?: number; status?: string; type?: string }) =>
    api.get<any>(`/jobs`, params),

  get: (jobId: string) => api.get<any>(`/jobs/${jobId}`),
};

export const organizationsApi = {
  list: (params?: { page?: number; page_size?: number; search?: string; status?: string }) =>
    api.get<any>(`/organizations/me/properties`, params),

  get: (organizationId: string) => api.get<any>(`/organizations/${organizationId}`),

  create: (data: { name: string; slug: string; description?: string }) =>
    api.post<any>(`/organizations`, data),

  update: (organizationId: string, data: { name?: string; description?: string }) =>
    api.patch<any>(`/organizations/${organizationId}`, data),

  delete: (organizationId: string) => api.delete(`/organizations/${organizationId}`),

  listProperties: (params?: { page?: number; page_size?: number }) =>
    api.get<any>(`/organizations/me/properties`, params),

  createProperty: (data: { name: string; code?: string; description?: string }) =>
    api.post<any>(`/organizations/me/properties`, data),

  updateProperty: (propertyId: string, data: { name?: string; code?: string; description?: string }) =>
    api.patch<any>(`/organizations/me/properties/${propertyId}`, data),

  deleteProperty: (propertyId: string) => api.delete(`/organizations/me/properties/${propertyId}`),

  listMemberships: (params?: { page?: number; page_size?: number }) =>
    api.get<any>(`/organizations/me/memberships`, params),

  createMembership: (data: { user_id: string; property_id?: string; role: string }) =>
    api.post<any>(`/organizations/me/memberships`, data),

  updateMembership: (membershipId: string, data: { role?: string; property_id?: string }) =>
    api.patch<any>(`/organizations/me/memberships/${membershipId}`, data),

  deleteMembership: (membershipId: string) => api.delete(`/organizations/me/memberships/${membershipId}`),
};

export const usersApi = {
  list: (params?: { page?: number; page_size?: number; search?: string; is_active?: boolean; role?: string }) =>
    api.get<any>(`/users`, params),

  getMe: () => api.get<any>(`/users/me`),

  updateMe: (data: { full_name?: string; avatar_url?: string }) =>
    api.patch<any>(`/users/me`, data),

  changePassword: (data: { current_password: string; new_password: string }) =>
    api.post(`/users/me/password`, data),

  get: (userId: string) => api.get<any>(`/users/${userId}`),

  update: (userId: string, data: { full_name?: string; email?: string; is_active?: boolean; role?: string }) =>
    api.patch<any>(`/users/${userId}`, data),

  delete: (userId: string) => api.delete(`/users/${userId}`),

  listSessions: (page = 1, pageSize = 20) =>
    api.get<any>(`/users/me/sessions`, { page, page_size: pageSize }),

  revokeSession: (sessionId: string) => api.delete(`/users/me/sessions/${sessionId}`),

  revokeAllSessions: () => api.post(`/auth/revoke`, {}),
};

export const authApi = {
  register: (data: { email: string; password: string; full_name: string; organization_name: string; organization_slug: string }) =>
    api.post<{ access_token: string; expires_in: number; user: any }>('/auth/register', data),

  login: (email: string, password: string) =>
    api.post<{ access_token: string; expires_in: number; user: any; mfa_required?: boolean; mfa_token?: string }>('/auth/login', { email, password }),

  refresh: () => api.post<{ access_token: string; expires_in: number; user: any }>('/auth/refresh', {}),

  revoke: () => api.post(`/auth/revoke`, {}),

  mfaSetup: () => api.post<{ secret: string; qr_code_uri: string; backup_codes: string[] }>('/auth/mfa/setup', {}),

  mfaVerify: (code: string) => api.post(`/auth/mfa/verify`, { code }),

  mfaDisable: (password: string) => api.post(`/auth/mfa/disable`, { password }),

  mfaChallenge: (code: string, mfaToken: string) =>
    api.post<{ access_token: string; expires_in: number; user: any }>('/auth/mfa/challenge', { code }, { Authorization: `Bearer ${mfaToken}` }),

  forgotPassword: (email: string) => api.post(`/auth/forgot-password`, { email }),

  resetPassword: (token: string, password: string) => api.post(`/auth/reset-password`, { token, password }),

  listSessions: (page = 1, pageSize = 20) => api.get<any>(`/users/me/sessions`, { page, page_size: pageSize }),

  revokeSession: (sessionId: string) => api.delete(`/users/me/sessions/${sessionId}`),

  revokeAllSessions: () => api.post(`/auth/revoke`, {}),
};

export const rbacApi = {
  listRoles: () => api.get<any>(`/rbac/roles`),

  createRole: (data: { name: string; display_name: string; description?: string; permission_ids: string[] }) =>
    api.post<any>(`/rbac/roles`, data),

  updateRole: (roleId: string, data: { display_name?: string; description?: string; permission_ids?: string[] }) =>
    api.patch<any>(`/rbac/roles/${roleId}`, data),

  deleteRole: (roleId: string) => api.delete(`/rbac/roles/${roleId}`),

  listPermissions: () => api.get<any>(`/rbac/permissions`),

  assignPermissions: (roleId: string, permissionNames: string[]) =>
    api.post<{ id: string }>(`/rbac/roles/${roleId}/permissions`, { permissions: permissionNames }),

  assignPermissionToRole: (roleId: string, permissionId: string) =>
    api.post<any>(`/rbac/roles/${roleId}/permissions`, { permission_id: permissionId }),

  revokePermissionFromRole: (roleId: string, permissionId: string) =>
    api.delete(`/rbac/roles/${roleId}/permissions/${permissionId}`),

  listUserRoles: (userId: string) => api.get<any>(`/rbac/users/${userId}/roles`),

  assignRoleToUser: (userId: string, roleId: string, organizationId: string) =>
    api.post<any>(`/rbac/users/${userId}/roles`, { role_id: roleId, organization_id: organizationId }),

  revokeRoleFromUser: (userId: string, roleId: string, organizationId: string) =>
    api.delete(`/rbac/users/${userId}/roles/${roleId}?organization_id=${organizationId}`),
};

export const auditApi = {
  list: (params?: { page?: number; page_size?: number; action?: string; resource?: string; actor_id?: string; start_date?: string; end_date?: string }) =>
    api.get<any>(`/audit`, params),

  get: (eventId: string) => api.get<any>(`/audit/${eventId}`),

  export: (params?: { format?: 'csv' | 'json'; start_date?: string; end_date?: string }) =>
    api.getBlob(`/audit/export`, params),
};

export const healthApi = {
  check: () => api.get<{ status: string }>('/health'),
};

export { ApiError } from '@/lib/api/client';