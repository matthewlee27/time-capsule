"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { API_BASE } from "@/lib/api";
import { getConnectedUsername, getLastPull } from "@/lib/session";
import VisualDashboard from "@/components/visualDashboard";
import Dropdown from "@/components/Basics";

// Same reasoning as basic.js: sessionStorage doesn't change from outside
// this tab, so there's nothing to subscribe to — this just makes reading it
// hydration-safe (null on the server, the real value on the client) without
// an effect just to mirror it into state.
function subscribeNoop() {
  return () => {};
}

function getServerStatusSnapshot() {
  return "";
}

function getServerUsernameSnapshot() {
  return null;
}

function getStatusSnapshot() {
  const username = getConnectedUsername();
  if (!username) {
    return "Not connected yet — go to home first.";
  }
  const lastPull = getLastPull();
  return lastPull
    ? `Connected as ${username} — ${lastPull.total_stored} scrobbles stored.`
    : `Connected as ${username} — no history pulled yet.`;
}

function computeDateError(fromDate, toDate, earliestDate, latestDate) {
  if (fromDate && earliestDate && fromDate < earliestDate) {
    return `"From" can't be before ${earliestDate}, your earliest scrobble.`;
  }
  if (toDate && latestDate && toDate > latestDate) {
    return `"To" can't be after ${latestDate}, your latest scrobble.`;
  }
  if (fromDate && toDate && fromDate > toDate) {
    return `"From" must be before "To".`;
  }
  return "";
}

export default function AnalyzePage() {
  const status = useSyncExternalStore(subscribeNoop, getStatusSnapshot, getServerStatusSnapshot);
  const username = useSyncExternalStore(
    subscribeNoop,
    getConnectedUsername,
    getServerUsernameSnapshot
  );
  const [visualType, setVisualType] = useState("basic");
  const [earliestDate, setEarliestDate] = useState("");
  const [latestDate, setLatestDate] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [showDashboard, setShowDashboard] = useState(false);

  useEffect(() => {
    if (!username) return;

    fetch(`${API_BASE}/scrobbles/${username}/date-range`)
      .then((res) => res.json())
      .then((data) => {
        if (!data.earliest || !data.latest) return;
        setEarliestDate(data.earliest);
        setLatestDate(data.latest);
        setFromDate(data.earliest);
        setToDate(data.latest);
      });
  }, [username]);

  const dateError = computeDateError(fromDate, toDate, earliestDate, latestDate);

  return (
    <>
      <p id="status">{status}</p>

      <label htmlFor="from-date">From</label>
      <input
        type="date"
        id="from-date"
        value={fromDate}
        min={earliestDate || undefined}
        max={toDate || latestDate || undefined}
        onChange={(e) => setFromDate(e.target.value)}
      />

      <label htmlFor="to-date">To</label>
      <input
        type="date"
        id="to-date"
        value={toDate}
        min={fromDate || earliestDate || undefined}
        max={latestDate || undefined}
        onChange={(e) => setToDate(e.target.value)}
      />

      {dateError && <p className="error">{dateError}</p>}

      <Dropdown
        options={["basic", "topTracks", "liftedTopTracks"]}
        value={visualType}
        onChange={setVisualType}
      />
      <button id="visualizer-btn" onClick={() => setShowDashboard(true)} disabled={!!dateError}>
        Visualize!
      </button>

      {showDashboard && !dateError && (
        <VisualDashboard visualType={visualType} fromDate={fromDate} toDate={toDate} />
      )}
    </>
  );
}
