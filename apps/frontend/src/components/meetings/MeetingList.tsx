import { useEffect, useState } from "react";

import { listMeetings } from "../../lib/meetings";
import type { Meeting, MeetingListResponse } from "../../lib/meetings";
import { getAccessToken } from "../../lib/session";

interface Props {
  token?: string;
}

function StatusBadge({ status }: { status: Meeting["status"] }) {
  const label: Record<Meeting["status"], string> = {
    scheduled: "Programada",
    in_progress: "En curso",
    finished: "Finalizada",
    cancelled: "Cancelada",
  };
  return (
    <span data-testid="status-badge" data-status={status}>
      {label[status] ?? status}
    </span>
  );
}

export function MeetingList({ token }: Props) {
  const [resolvedToken] = useState(() => token ?? getAccessToken() ?? "");
  const [data, setData] = useState<MeetingListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");

  useEffect(() => {
    let cancelled = false;
    listMeetings(resolvedToken, { page, page_size: 20, q: q || undefined })
      .then((r) => {
        if (!cancelled) { setData(r); setError(null); }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Error inesperado");
      });
    return () => {
      cancelled = true;
    };
  }, [resolvedToken, page, q]);

  if (error) return <p role="alert" data-testid="list-error">{error}</p>;
  if (!data) return <p>Cargando reuniones…</p>;

  return (
    <section aria-label="Reuniones">
      <input
        aria-label="buscar"
        placeholder="Buscar por título…"
        value={q}
        onChange={(e) => {
          setPage(1);
          setQ(e.target.value);
        }}
      />
      {data.items.length === 0 ? (
        <p>No hay reuniones.</p>
      ) : (
        <ul>
          {data.items.map((m) => (
            <li key={m.id}>
              <a href={`/meetings/detail?id=${m.id}`}>{m.title}</a> <StatusBadge status={m.status} />{" "}
              {new Date(m.starts_at).toLocaleString("es-CO", {
                timeZone: "America/Bogota",
              })}
            </li>
          ))}
        </ul>
      )}
      <nav aria-label="paginación">
        {data.pages > 1 && Array.from({ length: data.pages }, (_, i) => i + 1).map((n) => (
          <button key={n} onClick={() => setPage(n)} aria-current={n === page}>
            {n}
          </button>
        ))}
      </nav>
    </section>
  );
}
