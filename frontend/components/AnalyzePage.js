"use client";

import { useState, useSyncExternalStore } from "react";
import { getConnectedUsername, getLastPull } from "@/lib/session";
import VisualDashboard from "@/components/visualDashboard";
import Dropdown from "@/components/Basics";
import DateRangePicker, { computeDateError } from "@/components/DateRangePicker";

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

  const dateError = computeDateError(fromDate, toDate, earliestDate, latestDate);

  return (
    <>
      <p id="status">{status}</p>

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
