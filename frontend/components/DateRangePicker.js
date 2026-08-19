"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

export function computeDateError(fromDate, toDate, earliestDate, latestDate) {
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

// Fetches the connected user's earliest/latest scrobble dates and renders
// the from/to inputs bounded by them. Defaults fromDate/toDate to the full
// span once loaded, without clobbering a value the caller already set.
export default function DateRangePicker({
  username,
  fromDate,
  toDate,
  onChangeFrom,
  onChangeTo,
  onRangeLoaded,
}) {
  const [earliestDate, setEarliestDate] = useState("");
  const [latestDate, setLatestDate] = useState("");

  useEffect(() => {
    if (!username) return;

    fetch(`${API_BASE}/scrobbles/${username}/date-range`)
      .then((res) => res.json())
      .then((data) => {
        if (!data.earliest || !data.latest) return;
        setEarliestDate(data.earliest);
        setLatestDate(data.latest);
        if (!fromDate) onChangeFrom(data.earliest);
        if (!toDate) onChangeTo(data.latest);
        onRangeLoaded?.(data.earliest, data.latest);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [username]);

  const dateError = computeDateError(fromDate, toDate, earliestDate, latestDate);

  return (
    <>
      <label htmlFor="from-date">From</label>
      <input
        type="date"
        id="from-date"
        value={fromDate}
        min={earliestDate || undefined}
        max={toDate || latestDate || undefined}
        onChange={(e) => onChangeFrom(e.target.value)}
      />

      <label htmlFor="to-date">To</label>
      <input
        type="date"
        id="to-date"
        value={toDate}
        min={fromDate || earliestDate || undefined}
        max={latestDate || undefined}
        onChange={(e) => onChangeTo(e.target.value)}
      />

      {dateError && <p className="error">{dateError}</p>}
    </>
  );
}
