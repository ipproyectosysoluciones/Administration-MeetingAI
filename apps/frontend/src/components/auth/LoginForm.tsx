import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError, isMfaPending, login } from "../../lib/api";
import type { TokenResponse } from "../../lib/api";
import { MfaChallengeForm } from "./MfaChallengeForm";

interface LoginFormProps {
  onSuccess?: (result: TokenResponse) => void;
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [mfaToken, setMfaToken] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!email || !password) {
      setError("Email y contraseña son obligatorios");
      return;
    }
    setLoading(true);
    try {
      const result = await login({ email, password });
      if (isMfaPending(result)) {
        setMfaToken(result.mfa_token);
      } else {
        onSuccess?.(result);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error de conexión");
    } finally {
      setLoading(false);
    }
  }

  if (mfaToken) {
    return <MfaChallengeForm mfaToken={mfaToken} onSuccess={onSuccess} />;
  }

  return (
    <form onSubmit={handleSubmit} aria-label="login" noValidate>
      <div>
        <label htmlFor="login-email">Email</label>
        <input
          id="login-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          required
        />
      </div>
      <div>
        <label htmlFor="login-password">Contraseña</label>
        <input
          id="login-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
      </div>
      {error && (
        <p role="alert" data-testid="login-error">
          {error}
        </p>
      )}
      <button type="submit" disabled={loading}>
        {loading ? "Ingresando…" : "Ingresar"}
      </button>
    </form>
  );
}
