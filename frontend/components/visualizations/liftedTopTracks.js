"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { API_BASE } from "@/lib/api";
import { getConnectedUsername } from "@/lib/session";

const LIMIT = 15;

// Same reasoning as topTracksVis.js: sessionStorage doesn't change from
// outside this tab, so there's nothing to subscribe to — this just makes
// reading it hydration-safe (null on the server, the real value on the
// client) without an effect just to mirror it into state.
function subscribeNoop() {
  return () => {};
}

function getServerSnapshot() {
  return null;
}

export default function LiftedTopTracksVis({ fromDate, toDate }) {
  const username = useSyncExternalStore(subscribeNoop, getConnectedUsername, getServerSnapshot);
  const [liftedTracks, setLiftedTracks] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!username) return;

    const params = new URLSearchParams({ limit: String(LIMIT) });
    if (fromDate) params.set("from_date", fromDate);
    if (toDate) params.set("to_date", toDate);

    fetch(`${API_BASE}/scrobbles/${username}/lifted-top-tracks?${params}`)
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Could not load lifted top tracks");
        }
        return data;
      })
      .then((data) => setLiftedTracks(data.lifted_top_tracks))
      .catch((err) => setError(err.message));
  }, [username, fromDate, toDate]);

  if (!username) return <p className="error">Not connected yet — go to home first.</p>;
  if (error) return <p className="error">{error}</p>;
  if (!liftedTracks) return <p>Loading…</p>;
  if (liftedTracks.length === 0) {
    return <p>Nothing spiked in this range yet — try a narrower window or pull more history.</p>;
  }

  return (
    <ol>
      {liftedTracks.map((t) => (
        <li key={`${t.artist}—${t.track}`}>
          {t.artist} — {t.track} ({t.lift}x lift, {t.window_plays} plays in range)
        </li>
      ))}
    </ol>
  );
}
