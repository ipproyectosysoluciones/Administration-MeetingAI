import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError, createMeeting } from "../../lib/meetings";
import type { Meeting, MeetingCreatePayload } from "../../lib/meetings";
import { getAccessToken } from "../../lib/session";

interface Props {
  token?: string;
  onCreated?: (meeting: Meeting) => void;
}

export function MeetingCreateForm({ token, onCreated }: Props) {
  const [form, setForm] = useState<MeetingCreatePayload>({
    title: "",
    description: "",
    starts_at: "",
    ends_at: "",
    location: "",
    modality: "in_person",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const update =
    (field: keyof MeetingCreatePayload) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm((prev) => ({ ...prev, [field]: e.target.value }));

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!form.title.trim() || !form.starts_at || !form.ends_at) {
      setError("Título, inicio y fin son obligatorios");
      return;
    }
    if (new Date(form.ends_at) <= new Date(form.starts_at)) {
      setError("El fin debe ser después del inicio");
      return;
    }
    setLoading(true);
    try {
      const effectiveToken = token ?? getAccessToken() ?? "";
      const created = await createMeeting(effectiveToken, {
        ...form,
        description: form.description || undefined,
        location: form.location || undefined,
        starts_at: new Date(form.starts_at).toISOString(),
        ends_at: new Date(form.ends_at).toISOString(),
      });
      onCreated?.(created);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al crear la reunión");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} aria-label="crear-reunion" noValidate>
      <div>
        <label htmlFor="m-title">Título</label>
        <input id="m-title" value={form.title} onChange={update("title")} required />
      </div>
      <div>
        <label htmlFor="m-desc">Descripción</label>
        <textarea id="m-desc" value={form.description} onChange={update("description")} />
      </div>
      <div>
        <label htmlFor="m-start">Inicio</label>
        <input
          id="m-start"
          type="datetime-local"
          value={form.starts_at}
          onChange={update("starts_at")}
          required
        />
      </div>
      <div>
        <label htmlFor="m-end">Fin</label>
        <input
          id="m-end"
          type="datetime-local"
          value={form.ends_at}
          onChange={update("ends_at")}
          required
        />
      </div>
      <div>
        <label htmlFor="m-location">Lugar</label>
        <input id="m-location" value={form.location} onChange={update("location")} />
      </div>
      <div>
        <label htmlFor="m-modality">Modalidad</label>
        <select id="m-modality" value={form.modality} onChange={update("modality")}>
          <option value="in_person">Presencial</option>
          <option value="virtual">Virtual</option>
          <option value="hybrid">Híbrido</option>
        </select>
      </div>
      {error && (
        <p role="alert" data-testid="create-error">
          {error}
        </p>
      )}
      <button type="submit" disabled={loading}>
        {loading ? "Creando…" : "Crear reunión"}
      </button>
    </form>
  );
}
