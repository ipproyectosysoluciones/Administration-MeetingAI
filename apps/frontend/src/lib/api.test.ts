import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, isMfaPending, login, mfaChallenge, register } from "../lib/api";

const okJson = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

const tokenBody = {
  access_token: "tok",
  token_type: "bearer",
  expires_in: 900,
  mfa_required: false,
  user: {
    id: "u1",
    email: "a@b.c",
    full_name: "Ana",
    is_active: true,
    mfa_enabled: false,
    permissions: ["audit.read"],
    tenant_id: "t1",
  },
};

describe("api client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("login posts credentials and returns tokens", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(okJson(tokenBody));
    const result = await login({ email: "a@b.c", password: "secret" });
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/auth/login",
      expect.objectContaining({ method: "POST", credentials: "include" }),
    );
    expect(result).toMatchObject({ access_token: "tok" });
    expect(isMfaPending(result)).toBe(false);
  });

  it("login may return an MFA challenge", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      okJson({ mfa_required: true, mfa_token: "mtok", message: "MFA" }),
    );
    const result = await login({ email: "a@b.c", password: "secret" });
    expect(isMfaPending(result)).toBe(true);
    if (isMfaPending(result)) expect(result.mfa_token).toBe("mtok");
  });

  it("mfaChallenge sends the code with the mfa bearer token", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(okJson(tokenBody));
    await mfaChallenge("mtok", "123456");
    const [, init] = vi.mocked(fetch).mock.calls[0]!;
    expect((init!.headers as Record<string, string>).Authorization).toBe("Bearer mtok");
    expect(init!.body).toBe(JSON.stringify({ code: "123456" }));
  });

  it("maps backend errors to ApiError with code and message", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      okJson({ code: "INVALID_CREDENTIALS", message: "Invalid email or password" }, 401),
    );
    await expect(login({ email: "a@b.c", password: "x" })).rejects.toMatchObject({
      name: "ApiError",
      status: 401,
      code: "INVALID_CREDENTIALS",
      message: "Invalid email or password",
    } satisfies Partial<ApiError>);
  });

  it("register posts the full onboarding payload", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(okJson(tokenBody, 201));
    await register({
      email: "a@b.c",
      password: "secret-pass-123",
      full_name: "Ana",
      organization_name: "Org",
      organization_slug: "org-slug",
    });
    const [url, init] = vi.mocked(fetch).mock.calls[0]!;
    expect(url).toBe("/api/v1/auth/register");
    expect(JSON.parse(init!.body as string)).toMatchObject({ organization_slug: "org-slug" });
  });
});
