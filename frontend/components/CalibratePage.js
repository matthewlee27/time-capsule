"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { API_BASE } from "@/lib/api";
import { getConnectedUsername } from "@/lib/session";
import DateRangePicker, { computeDateError } from "@/components/DateRangePicker";
import PreferenceSort from "@/components/PreferenceSort";

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
  const [ranking, setRanking] = useState(false);
  const [rankedTracks, setRankedTracks] = useState(null);
  const [saveError, setSaveError] = useState("");
  const [dirty, setDirty] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState(null);
  const [calibrating, setCalibrating] = useState(false);
  const [calibrateResult, setCalibrateResult] = useState(null);
  const [calibrateError, setCalibrateError] = useState("");

  const dateError = computeDateError(fromDate, toDate, earliestDate, latestDate);

  useEffect(() => {
    if (!username || dateError) return;

    setTracks(null);
    setError("");
    setRanking(false);
    setRankedTracks(null);
    setSaveError("");
    setDirty(false);
    setCalibrateResult(null);
    setCalibrateError("");

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

  function saveRanking(list) {
    setSaveError("");
    fetch(`${API_BASE}/scrobbles/${username}/ranking`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        from_date: fromDate || null,
        to_date: toDate || null,
        ranked_tracks: list.map((t) => ({ artist: t.artist, track: t.track })),
      }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || "Could not save ranking");
        }
        setDirty(false);
      })
      .catch((err) => setSaveError(err.message));
  }

  function runCalibration() {
    setCalibrating(true);
    setCalibrateError("");
    fetch(`${API_BASE}/scrobbles/${username}/calibrate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        from_date: fromDate || null,
        to_date: toDate || null,
      }),
    })
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Could not calibrate");
        }
        setCalibrateResult(data);
      })
      .catch((err) => setCalibrateError(err.message))
      .finally(() => setCalibrating(false));
  }

  function handleRankingComplete(sorted) {
    setRanking(false);
    setRankedTracks(sorted);
    saveRanking(sorted);
  }

  function handleDragOver(e, overIndex) {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === overIndex) return;
    const next = [...rankedTracks];
    const [moved] = next.splice(draggedIndex, 1);
    next.splice(overIndex, 0, moved);
    setRankedTracks(next);
    setDraggedIndex(overIndex);
    setDirty(true);
  }

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
      {tracks && tracks.length > 0 && !ranking && !rankedTracks && (
        <>
          <ol>
            {tracks.map((t) => (
              <li key={`${t.artist}—${t.track}`}>
                {t.artist} — {t.track} ({t.play_count})
              </li>
            ))}
          </ol>
          <button onClick={() => setRanking(true)}>Rank these by feel</button>
        </>
      )}

      {ranking && tracks && (
        <PreferenceSort items={tracks} onComplete={handleRankingComplete} />
      )}

      {rankedTracks && (
        <>
          <p>Your preferred order:</p>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
            {rankedTracks.map((t, i) => (
              <div
                key={`${t.artist}—${t.track}`}
                draggable
                onDragStart={() => setDraggedIndex(i)}
                onDragOver={(e) => handleDragOver(e, i)}
                onDragEnd={() => setDraggedIndex(null)}
                style={{
                  border: "1px solid rgba(128, 128, 128, 0.5)",
                  borderRadius: "4px",
                  padding: "0.35rem 0.6rem",
                  cursor: "grab",
                  opacity: draggedIndex === i ? 0.4 : 1,
                }}
              >
                {t.artist} — {t.track}
              </div>
            ))}
          </div>
          {saveError && <p className="error">{saveError}</p>}
          <button onClick={() => saveRanking(rankedTracks)} disabled={!dirty}>
            {dirty ? "Save order" : "Saved"}
          </button>
          <button
            onClick={() => {
              setRankedTracks(null);
              setCalibrateResult(null);
              setCalibrateError("");
            }}
          >
            Rank again
          </button>
          <button onClick={runCalibration} disabled={calibrating || dirty}>
            {calibrating ? "Calibrating…" : "Calibrate my taste"}
          </button>
          {calibrateError && <p className="error">{calibrateError}</p>}
          {calibrateResult && (
            <p>
              Fit quality: {Math.round(calibrateResult.correct_fraction * 100)}% of pairs matched your ranking
              (alpha {calibrateResult.alpha}, beta {calibrateResult.beta})
            </p>
          )}
        </>
      )}
    </>
  );
}
