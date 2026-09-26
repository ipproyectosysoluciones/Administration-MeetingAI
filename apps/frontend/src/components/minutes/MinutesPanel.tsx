import { useEffect, useState } from "react";

import {
  ApiError,
  approveMinute,
  archiveMinute,
  createMinuteDraft,
  listMinutes,
  publishMinute,
  reviewMinute,
} from "../../lib/minutes";
import type { Minute, MinuteStatus } from "../../lib/minutes";
import { getAccessToken } from "../../lib/session";

interface Props {
  token?: string;
  meetingId: string;
}

const NEXT_ACTION: Partial<Record<MinuteStatus, { label: string; run: (t: string, id: string) => Promise<Minute> }>> = {
  draft: { label: "Enviar a revisión", run: (t, id) => reviewMinute(t, id) },
  review: { label: "Aprobar", run: (t, id) => approveMinute(t, id) },
  approved: { label: "Publicar", run: (t, id) => publishMinute(t, id) },
  published: { label: "Archivar", run: (t, id) => archiveMinute(t, id) },
};

function statusLabel(status: MinuteStatus): string {
  const map: Record<MinuteStatus, string> = {
    draft: "Borrador",
    review: "En revisión",
    approved: "Aprobada",
    published: "Publicada",
    archived: "Archivada",
  };
  return map[status];
}

export function MinutesPanel({ token, meetingId }: Props) {
  const resolvedToken = token ?? getAccessToken() ?? "";
  const [minutes, setMinutes] = useState<Minute[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [creating, setCreating] = useState(false);

  const refresh = async () => {
    try {
      const resp = await listMinutes(resolvedToken, meetingId);
      setMinutes(resp.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar actas");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let live = true;
    listMinutes(resolvedToken, meetingId)
      .then((resp) => {
        if (live) setMinutes(resp.items);
      })
      .catch((e: unknown) => {
        if (live) setError(e instanceof Error ? e.message : "Error");
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [resolvedToken, meetingId]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      setError("El título es obligatorio");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      await createMinuteDraft(resolvedToken, meetingId, { title, content });
      setTitle("");
      setContent("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al crear el borrador");
    } finally {
      setCreating(false);
    }
  }

  async function onTransition(minute: Minute) {
    const action = NEXT_ACTION[minute.status];
    if (!action) return;
    setError(null);
    try {
      await action.run(resolvedToken, minute.id);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cambiar el estado");
    }
  }

  if (loading) return <p>Cargando…</p>;

  return (
    <section aria-label="actas">
      <h2>Actas</h2>

      <form onSubmit={onCreate} aria-label="crear-acta">
        <h3>Nuevo borrador</h3>
        <label htmlFor="m-title">Título</label>
        <input
          id="m-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <label htmlFor="m-content">Contenido</label>
        <textarea
          id="m-content"
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />
        <button type="submit" disabled={creating}>
          {creating ? "Creando…" : "Crear borrador"}
        </button>
      </form>

      {error && (
        <p role="alert" data-testid="minutes-error">
          {error}
        </p>
      )}

      {minutes.length === 0 ? (
        <p>Aún no hay actas para esta reunión.</p>
      ) : (
        <ul aria-label="lista-actas">
          {minutes.map((m) => {
            const action = NEXT_ACTION[m.status];
            const isDraft = m.status === "draft";
            return (
              <li key={m.id} data-status={m.status}>
                <strong>{m.title}</strong>{" "}
                <span data-testid={`status-${m.id}`}>
                  {statusLabel(m.status)}
                </span>{" "}
                {isDraft && <em>(borrador)</em>}
                <p>Versión {m.version}</p>
                {m.content && <p>{m.content.slice(0, 200)}</p>}
                {action && (
                  <button type="button" onClick={() => onTransition(m)}>
                    {action.label}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
