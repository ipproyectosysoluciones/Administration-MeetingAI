import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../../lib/api";
import { LoginForm } from "./LoginForm";

const tokenResult: api.TokenResponse = {
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
    permissions: [],
    tenant_id: "t1",
  },
};

vi.mock("../../lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../lib/api")>();
  return { ...original, login: vi.fn() };
});

describe("LoginForm", () => {
  beforeEach(() => {
    vi.mocked(api.login).mockReset();
  });

  it("renders email/password fields and submit", () => {
    render(<LoginForm />);
    expect(screen.getByLabelText(/email/i)).toBeDefined();
    expect(screen.getByLabelText(/contraseña/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /ingresar/i })).toBeDefined();
  });

  it("blocks empty submit with a message", async () => {
    render(<LoginForm />);
    fireEvent.click(screen.getByRole("button", { name: /ingresar/i }));
    expect(await screen.findByTestId("login-error")).toBeDefined();
    expect(api.login).not.toHaveBeenCalled();
  });

  it("calls onSuccess on token response", async () => {
    vi.mocked(api.login).mockResolvedValue(tokenResult);
    const onSuccess = vi.fn();
    render(<LoginForm onSuccess={onSuccess} />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "a@b.c" },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: "secreto123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ingresar/i }));
    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(tokenResult));
  });

  it("switches to the MFA challenge step when required", async () => {
    vi.mocked(api.login).mockResolvedValue({
      mfa_required: true,
      mfa_token: "mtok",
      message: "MFA",
    });
    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "a@b.c" },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: "secreto123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ingresar/i }));
    expect(
      await screen.findByLabelText(/código de verificación/i),
    ).toBeDefined();
  });

  it("shows the server error message", async () => {
    vi.mocked(api.login).mockRejectedValue(
      new api.ApiError(401, "INVALID_CREDENTIALS", "Credenciales inválidas"),
    );
    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "a@b.c" },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: "secreto123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ingresar/i }));
    const alert = await screen.findByTestId("login-error");
    expect(alert.textContent).toBe("Credenciales inválidas");
  });
});
