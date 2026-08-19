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

      if (!res.ok || !res.body) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Pull failed");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalData = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let newlineIndex;
        while ((newlineIndex = buffer.indexOf("\n")) !== -1) {
          const line = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 1);
          if (!line.trim()) continue;

          const event = JSON.parse(line);
          if (event.type === "progress") {
            setStatus(event.message);
          } else if (event.type === "error") {
            throw new Error(event.detail || "Pull failed");
          } else if (event.type === "done") {
            finalData = event;
          }
        }
      }

      if (!finalData) {
        throw new Error("Pull failed");
      }

      setLastPull(finalData);
      onPulled?.(finalData);
      setStatus(formatPullStatus(finalData));
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
