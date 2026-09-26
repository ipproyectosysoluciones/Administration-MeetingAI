import { useMemo } from "react";

import { MinutesPanel } from "./MinutesPanel";

export function MinutesPanelLoader() {
  const meetingId = useMemo(() => {
    if (typeof window === "undefined") return "";
    return new URLSearchParams(window.location.search).get("meeting_id") ?? "";
  }, []);

  if (!meetingId) {
    return <p role="alert">Reunión no especificada</p>;
  }
  return <MinutesPanel meetingId={meetingId} />;
}
