import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError, register } from "../../lib/api";
import type { TokenResponse } from "../../lib/api";

interface RegisterFormProps {
  onSuccess?: (result: TokenResponse) => void;
}

const SLUG_RE = /^[a-z0-9-]+$/;

export function RegisterForm({ onSuccess }: RegisterFormProps) {
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    organization_name: "",
    organization_slug: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function update(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((prev) => ({ ...prev, [field]: e.target.value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (Object.values(form).some((v) => !v.trim())) {
      setError("Todos los campos son obligatorios");
      return;
    }
    if (form.password.length < 12) {
      setError("La contraseña debe tener al menos 12 caracteres");
      return;
    }
    if (!SLUG_RE.test(form.organization_slug)) {
      setError("El slug de la organización solo admite minúsculas, números y guiones");
      return;
    }
    setLoading(true);
    try {
      const result = await register(form);
      onSuccess?.(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error de conexión");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} aria-label="register" noValidate>
      <div>
        <label htmlFor="reg-email">Email</label>
        <input
          id="reg-email"
          type="email"
          value={form.email}
          onChange={update("email")}
          autoComplete="email"
          required
        />
      </div>
      <div>
        <label htmlFor="reg-password">Contraseña</label>
        <input
          id="reg-password"
          type="password"
          value={form.password}
          onChange={update("password")}
          autoComplete="new-password"
          required
        />
      </div>
      <div>
        <label htmlFor="reg-name">Nombre completo</label>
        <input
          id="reg-name"
          value={form.full_name}
          onChange={update("full_name")}
          autoComplete="name"
          required
        />
      </div>
      <div>
        <label htmlFor="reg-org">Organización</label>
        <input
          id="reg-org"
          value={form.organization_name}
          onChange={update("organization_name")}
          required
        />
      </div>
      <div>
        <label htmlFor="reg-slug">Slug de la organización</label>
        <input
          id="reg-slug"
          value={form.organization_slug}
          onChange={update("organization_slug")}
          required
        />
      </div>
      {error && (
        <p role="alert" data-testid="register-error">
          {error}
        </p>
      )}
      <button type="submit" disabled={loading}>
        {loading ? "Creando…" : "Crear cuenta"}
      </button>
    </form>
  );
}
