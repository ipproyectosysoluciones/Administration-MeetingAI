const API_BASE = import.meta.env.PUBLIC_API_BASE ?? "/api/v1";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  mfa_enabled: boolean;
  permissions: string[];
  tenant_id: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
  mfa_required: boolean;
}

export interface MfaPending {
  mfa_required: true;
  mfa_token: string;
  message: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  organization_name: string;
  organization_slug: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  accessToken?: string,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string>) ?? {}),
  };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const resp = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
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
      /* non-JSON error body */
    }
    throw new ApiError(resp.status, code, message);
  }
  return (await resp.json()) as T;
}

export type LoginResult = TokenResponse | MfaPending;

export async function register(payload: RegisterPayload): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function login(payload: LoginPayload): Promise<LoginResult> {
  return request<LoginResult>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function isMfaPending(result: LoginResult): result is MfaPending {
  return "mfa_required" in result && result.mfa_required === true && "mfa_token" in result;
}

export async function mfaChallenge(mfaToken: string, code: string): Promise<TokenResponse> {
  return request<TokenResponse>(
    "/auth/mfa/challenge",
    { method: "POST", body: JSON.stringify({ code }) },
    mfaToken,
  );
}
