"use client";

import { useEffect, useState } from "react";
import { getConnectedUsername, getLastPull } from "@/lib/session";

export default function AnalyzePage() {
  const [status, setStatus] = useState("");

  useEffect(() => {
    const username = getConnectedUsername();

    if (username) {
      const lastPull = getLastPull();
      setStatus(
        lastPull
          ? `Connected as ${username} — ${lastPull.total_stored} scrobbles stored.`
          : `Connected as ${username} — no history pulled yet.`
      );
    } else {
      setStatus("Not connected yet — go to home first.");
    }
  }, []);

  return (
    <>
      <p id="status">{status}</p>
      <p>Nothing to analyze yet — the engines aren&apos;t wired up.</p>
    </>
  );
}
