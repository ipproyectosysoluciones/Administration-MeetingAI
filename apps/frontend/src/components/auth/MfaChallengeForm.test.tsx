import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../../lib/api";
import { MfaChallengeForm } from "./MfaChallengeForm";

vi.mock("../../lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../lib/api")>();
  return { ...original, mfaChallenge: vi.fn() };
});

describe("MfaChallengeForm", () => {
  beforeEach(() => {
    vi.mocked(api.mfaChallenge).mockReset();
  });

  it("rejects non-6-digit codes", async () => {
    render(<MfaChallengeForm mfaToken="mtok" />);
    fireEvent.change(screen.getByLabelText(/código/i), { target: { value: "12" } });
    fireEvent.click(screen.getByRole("button", { name: /verificar/i }));
    expect(await screen.findByTestId("mfa-error")).toBeDefined();
    expect(api.mfaChallenge).not.toHaveBeenCalled();
  });

  it("submits the code with the mfa token", async () => {
    vi.mocked(api.mfaChallenge).mockResolvedValue({
      access_token: "tok",
      token_type: "bearer",
      expires_in: 900,
      mfa_required: false,
      user: {
        id: "u1",
        email: "a@b.c",
        full_name: null,
        is_active: true,
        mfa_enabled: true,
        permissions: [],
        tenant_id: "t1",
      },
    });
    const onSuccess = vi.fn();
    render(<MfaChallengeForm mfaToken="mtok" onSuccess={onSuccess} />);
    fireEvent.change(screen.getByLabelText(/código/i), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: /verificar/i }));
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    expect(api.mfaChallenge).toHaveBeenCalledWith("mtok", "123456");
  });
});
