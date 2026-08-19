"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { API_BASE } from "@/lib/api";
import { getConnectedUsername } from "@/lib/session";
import DateRangePicker, { computeDateError } from "@/components/DateRangePicker";

const LIMIT = 30;
const ARTIST_CAP = 10;

function subscribeNoop() {
  return () => {};
}

function getServerUsernameSnapshot() {
  return null;
}

export default function CalibratePage() {
  const username = useSyncExternalStore(subscribeNoop, getConnectedUsername, getServerUsernameSnapshot);
  const [earliestDate, setEarliestDate] = useState("");
  const [latestDate, setLatestDate] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [tracks, setTracks] = useState(null);
  const [error, setError] = useState("");

  const dateError = computeDateError(fromDate, toDate, earliestDate, latestDate);

  useEffect(() => {
    if (!username || dateError) return;

    setTracks(null);
    setError("");

    const params = new URLSearchParams({ limit: String(LIMIT), artist_cap: String(ARTIST_CAP) });
    if (fromDate) params.set("from_date", fromDate);
    if (toDate) params.set("to_date", toDate);

    fetch(`${API_BASE}/scrobbles/${username}/top-tracks?${params}`)
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Could not load top tracks");
        }
        return data;
      })
      .then((data) => setTracks(data.top_tracks))
      .catch((err) => setError(err.message));
  }, [username, fromDate, toDate, dateError]);

  if (!username) {
    return <p className="error">Not connected yet — go to home first.</p>;
  }

  return (
    <>
      <p id="status">Connected as {username}</p>

      <DateRangePicker
        username={username}
        fromDate={fromDate}
        toDate={toDate}
        onChangeFrom={setFromDate}
        onChangeTo={setToDate}
        onRangeLoaded={(earliest, latest) => {
          setEarliestDate(earliest);
          setLatestDate(latest);
        }}
      />

      {error && <p className="error">{error}</p>}
      {!error && !dateError && !tracks && <p>Loading…</p>}
      {tracks && tracks.length === 0 && <p>No listening history in this range.</p>}
      {tracks && tracks.length > 0 && (
        <ol>
          {tracks.map((t) => (
            <li key={`${t.artist}—${t.track}`}>
              {t.artist} — {t.track} ({t.play_count})
            </li>
          ))}
        </ol>
      )}
    </>
  );
}
