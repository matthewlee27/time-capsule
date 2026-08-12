"use client";

import { useState, useSyncExternalStore } from "react";
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

export default function AnalyzePage() {
  const status = useSyncExternalStore(subscribeNoop, getStatusSnapshot, getServerStatusSnapshot);
  const [visualType, setVisualType] = useState("basic");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [showDashboard, setShowDashboard] = useState(false);

  return (
    <>
      <p id="status">{status}</p>

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

      <Dropdown
        options={["basic", "topTracks", "liftedTopTracks"]}
        value={visualType}
        onChange={setVisualType}
      />
      <button id="visualizer-btn" onClick={() => setShowDashboard(true)}>
        Visualize!
      </button>

      {showDashboard && (
        <VisualDashboard visualType={visualType} fromDate={fromDate} toDate={toDate} />
      )}
    </>
  );
}
