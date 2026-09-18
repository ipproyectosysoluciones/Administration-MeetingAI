import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError, mfaChallenge } from "../../lib/api";
import type { TokenResponse } from "../../lib/api";

interface MfaChallengeFormProps {
  mfaToken: string;
  onSuccess?: (result: TokenResponse) => void;
}

export function MfaChallengeForm({
  mfaToken,
  onSuccess,
}: MfaChallengeFormProps) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!/^\d{6}$/.test(code)) {
      setError("El código debe tener 6 dígitos");
      return;
    }
    setLoading(true);
    try {
      const result = await mfaChallenge(mfaToken, code);
      onSuccess?.(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error de conexión");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} aria-label="mfa-challenge" noValidate>
      <p>Ingresá el código de tu aplicación autenticadora.</p>
      <div>
        <label htmlFor="mfa-code">Código de verificación</label>
        <input
          id="mfa-code"
          inputMode="numeric"
          pattern="\d{6}"
          maxLength={6}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          autoComplete="one-time-code"
          required
        />
      </div>
      {error && (
        <p role="alert" data-testid="mfa-error">
          {error}
        </p>
      )}
      <button type="submit" disabled={loading}>
        {loading ? "Verificando…" : "Verificar"}
      </button>
    </form>
  );
}
