import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../../lib/api";
import { RegisterForm } from "./RegisterForm";

const validForm = {
  email: "ana@b.c",
  password: "super-secret-123",
  full_name: "Ana González",
  organization_name: "Torre Norte",
  organization_slug: "torre-norte",
};

vi.mock("../../lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../lib/api")>();
  return { ...original, register: vi.fn() };
});

function fill(screen_: typeof screen) {
  fireEvent.change(screen_.getByLabelText(/^email/i), {
    target: { value: validForm.email },
  });
  fireEvent.change(screen_.getByLabelText(/contraseña/i), {
    target: { value: validForm.password },
  });
  fireEvent.change(screen_.getByLabelText(/nombre completo/i), {
    target: { value: validForm.full_name },
  });
  fireEvent.change(screen_.getByLabelText(/^organización$/i), {
    target: { value: validForm.organization_name },
  });
  fireEvent.change(screen_.getByLabelText(/slug/i), {
    target: { value: validForm.organization_slug },
  });
}

describe("RegisterForm", () => {
  beforeEach(() => {
    vi.mocked(api.register).mockReset();
  });

  it("requires all fields", async () => {
    render(<RegisterForm />);
    fireEvent.click(screen.getByRole("button", { name: /crear cuenta/i }));
    expect(await screen.findByTestId("register-error")).toBeDefined();
    expect(api.register).not.toHaveBeenCalled();
  });

  it("rejects short passwords", async () => {
    render(<RegisterForm />);
    fill(screen);
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: "short" },
    });
    fireEvent.click(screen.getByRole("button", { name: /crear cuenta/i }));
    const alert = await screen.findByTestId("register-error");
    expect(alert.textContent).toMatch(/12 caracteres/);
  });

  it("rejects invalid organization slugs", async () => {
    render(<RegisterForm />);
    fill(screen);
    fireEvent.change(screen.getByLabelText(/slug/i), {
      target: { value: "Torre Norte!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /crear cuenta/i }));
    const alert = await screen.findByTestId("register-error");
    expect(alert.textContent).toMatch(/slug/i);
  });

  it("submits the full payload and calls onSuccess", async () => {
    const tokenResult = {
      access_token: "tok",
      token_type: "bearer",
      expires_in: 900,
      mfa_required: false,
      user: {
        id: "u1",
        email: validForm.email,
        full_name: validForm.full_name,
        is_active: true,
        mfa_enabled: false,
        permissions: [],
        tenant_id: "t1",
      },
    };
    vi.mocked(api.register).mockResolvedValue(tokenResult);
    const onSuccess = vi.fn();
    render(<RegisterForm onSuccess={onSuccess} />);
    fill(screen);
    fireEvent.click(screen.getByRole("button", { name: /crear cuenta/i }));
    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(tokenResult));
    expect(api.register).toHaveBeenCalledWith(validForm);
  });
});
