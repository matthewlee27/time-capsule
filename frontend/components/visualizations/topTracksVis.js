"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { API_BASE } from "@/lib/api";
import { getConnectedUsername, getDateRange } from "@/lib/session";

const LIMIT = 15;

// Same reasoning as basicVis.js: sessionStorage doesn't change from outside
// this tab, so there's nothing to subscribe to — this just makes reading it
// hydration-safe (null on the server, the real value on the client) without
// an effect just to mirror it into state.
function subscribeNoop() {
  return () => {};
}

function getServerSnapshot() {
  return null;
}

export default function TopTracksVis() {
  const username = useSyncExternalStore(subscribeNoop, getConnectedUsername, getServerSnapshot);
  const [topTracks, setTopTracks] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!username) return;

    const dateRange = getDateRange();
    const params = new URLSearchParams({ limit: String(LIMIT) });
    if (dateRange?.from_date) params.set("from_date", dateRange.from_date);
    if (dateRange?.to_date) params.set("to_date", dateRange.to_date);

    fetch(`${API_BASE}/scrobbles/${username}/top-tracks?${params}`)
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Could not load top tracks");
        }
        return data;
      })
      .then((data) => setTopTracks(data.top_tracks))
      .catch((err) => setError(err.message));
  }, [username]);

  if (!username) return <p className="error">Not connected yet — go to home first.</p>;
  if (error) return <p className="error">{error}</p>;
  if (!topTracks) return <p>Loading…</p>;
  if (topTracks.length === 0) return <p>No listening history to show yet.</p>;

  return (
    <ol>
      {topTracks.map((t) => (
        <li key={`${t.artist}—${t.track}`}>
          {t.artist} — {t.track} ({t.play_count})
        </li>
      ))}
    </ol>
  );
}
