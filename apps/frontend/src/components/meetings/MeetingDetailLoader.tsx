import { useMemo } from "react";

import { MeetingDetail } from "./MeetingDetail";

export function MeetingDetailLoader() {
  const meetingId = useMemo(() => {
    if (typeof window === "undefined") return "";
    return new URLSearchParams(window.location.search).get("id") ?? "";
  }, []);

  if (!meetingId) {
    return <p role="alert">Reunión no especificada</p>;
  }
  return <MeetingDetail meetingId={meetingId} />;
}
