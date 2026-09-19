// Minimal browser session store for access tokens (bounded MVP: login-first UX).
// Uses localStorage; httpOnly refresh cookie is handled server-side.

const KEY = "reunionai.access_token";

export function getAccessToken(): string | null {
  if (typeof localStorage === "undefined") return null;
  return localStorage.getItem(KEY);
}

export function setAccessToken(token: string): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(KEY, token);
}

export function clearAccessToken(): void {
  if (typeof localStorage === "undefined") return;
  localStorage.removeItem(KEY);
}
