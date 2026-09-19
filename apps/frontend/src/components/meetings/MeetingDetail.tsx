import { useEffect, useState } from "react";

import {
  addParticipant,
  ApiError,
  cancelMeeting,
  getMeeting,
  listParticipants,
  removeParticipant,
} from "../../lib/meetings";
import type { Meeting, Participant } from "../../lib/meetings";
import { getAccessToken } from "../../lib/session";

interface Props {
  token?: string;
  meetingId: string;
}

export function MeetingDetail({ token, meetingId }: Props) {
  const resolvedToken = token ?? getAccessToken() ?? "";
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [cancelConfirm, setCancelConfirm] = useState(false);

  useEffect(() => {
    let live = true;
    Promise.all([getMeeting(resolvedToken, meetingId), listParticipants(resolvedToken, meetingId)])
      .then(([m, p]) => {
        if (!live) return;
        setMeeting(m);
        setParticipants(p.items);
      })
      .catch((e: unknown) => {
        if (live) setError(e instanceof Error ? e.message : "Error");
      });
    return () => {
      live = false;
    };
  }, [resolvedToken, meetingId]);

  async function onAddEmail(e: React.FormEvent) {
    e.preventDefault();
    if (!email.includes("@")) {
      setError("Email inválido");
      return;
    }
    try {
      const p = await addParticipant(resolvedToken, meetingId, {
        external_email: email,
        role: "attendee",
      });
      setParticipants((prev) => [...prev, p]);
      setEmail("");
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al agregar");
    }
  }

  async function onRemove(id: string) {
    try {
      await removeParticipant(resolvedToken, meetingId, id);
      setParticipants((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al quitar");
    }
  }

  async function onCancel() {
    try {
      const updated = await cancelMeeting(resolvedToken, meetingId);
      setMeeting(updated);
      setCancelConfirm(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cancelar");
    }
  }

  if (error && !meeting) return <p role="alert">{error}</p>;
  if (!meeting) return <p>Cargando…</p>;

  return (
    <article aria-label="detalle-reunion">
      <h1>{meeting.title}</h1>
      <p>
        Estado: <strong>{meeting.status}</strong> ·{" "}
        {new Date(meeting.starts_at).toLocaleString("es-CO", { timeZone: "America/Bogota" })} —{" "}
        {new Date(meeting.ends_at).toLocaleTimeString("es-CO", { timeZone: "America/Bogota" })}
      </p>
      {meeting.description && <p>{meeting.description}</p>}
      {meeting.location && <p>Lugar: {meeting.location}</p>}
      <p>Modalidad: {meeting.modality}</p>

      {meeting.status !== "cancelled" && meeting.status !== "finished" && (
        <section>
          {!cancelConfirm ? (
            <button onClick={() => setCancelConfirm(true)}>Cancelar reunión</button>
          ) : (
            <div role="alertdialog" aria-label="confirmar-cancelacion">
              <p>¿Cancelar esta reunión?</p>
              <button onClick={onCancel}>Sí, cancelar</button>
              <button onClick={() => setCancelConfirm(false)}>Volver</button>
            </div>
          )}
        </section>
      )}

      <h2>Participantes</h2>
      <ul>
        {participants.map((p) => (
          <li key={p.id}>
            {p.external_email ?? `usuario ${p.user_id}`} — {p.role}{" "}
            <button onClick={() => onRemove(p.id)} aria-label={`quitar ${p.id}`}>
              Quitar
            </button>
          </li>
        ))}
      </ul>

      <form onSubmit={onAddEmail} aria-label="agregar-participante">
        <label htmlFor="p-email">Agregar invitado por email</label>
        <input
          id="p-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <button type="submit">Agregar</button>
      </form>

      {error && (
        <p role="alert" data-testid="detail-error">
          {error}
        </p>
      )}
    </article>
  );
}
