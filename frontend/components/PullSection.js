"use client";

import { useState } from "react";
import { API_BASE } from "@/lib/api";
import { setLastPull } from "@/lib/session";

function formatPullStatus(data) {
  return (
    `Fetched ${data.pulled_from_lastfm} scrobbles — ${data.saved} new, ` +
    `${data.duplicates} already saved (${data.total_stored} stored total).`
  );
}

export default function PullSection({ username, initialStatus, onPulled }) {
  const [status, setStatus] = useState(initialStatus || "");

  async function handlePull() {
    setStatus("Pulling your scrobble history…");

    try {
      const res = await fetch(`${API_BASE}/pull`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, from_date: null, to_date: null }),
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Pull failed");
      }

      setLastPull(data);
      onPulled?.(data);
      setStatus(formatPullStatus(data));
    } catch (err) {
      setStatus(err.message);
    }
  }

  return (
    <section id="pull-section">
      <p id="connected-as">Connected as {username}</p>
      <button id="pull-btn" onClick={handlePull}>
        Pull my history
      </button>
      <p id="pull-status">{status}</p>
    </section>
  );
}
