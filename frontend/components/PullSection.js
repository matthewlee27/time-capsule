"use client";

import { useState } from "react";
import { API_BASE } from "@/lib/api";
import { setDateRange, setLastPull } from "@/lib/session";

function formatPullStatus(data) {
  return (
    `Fetched ${data.pulled_from_lastfm} scrobbles — ${data.saved} new, ` +
    `${data.duplicates} already saved (${data.total_stored} stored total).`
  );
}

export default function PullSection({ username, initialStatus, onPulled }) {
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [status, setStatus] = useState(initialStatus || "");

  async function handlePull() {
    setStatus("Pulling your scrobble history…");

    try {
      const res = await fetch(`${API_BASE}/pull`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          from_date: fromDate || null,
          to_date: toDate || null,
        }),
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Pull failed");
      }

      setLastPull(data);
      setDateRange({ from_date: fromDate || null, to_date: toDate || null });
      onPulled?.(data);
      setStatus(formatPullStatus(data));
    } catch (err) {
      setStatus(err.message);
    }
  }

  return (
    <section id="pull-section">
      <p id="connected-as">Connected as {username}</p>

      <label htmlFor="from-date">From (optional)</label>
      <input
        type="date"
        id="from-date"
        value={fromDate}
        onChange={(e) => setFromDate(e.target.value)}
      />

      <label htmlFor="to-date">To (optional)</label>
      <input
        type="date"
        id="to-date"
        value={toDate}
        onChange={(e) => setToDate(e.target.value)}
      />

      <button id="pull-btn" onClick={handlePull}>
        Pull my history
      </button>
      <p id="pull-status">{status}</p>
    </section>
  );
}
