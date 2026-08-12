"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import * as d3 from "d3";
import { API_BASE } from "@/lib/api";
import { getConnectedUsername } from "@/lib/session";

const WIDTH = 640;
const HEIGHT = 320;
const MARGIN = { top: 16, right: 16, bottom: 40, left: 40 };

// sessionStorage never changes from outside this tab, so there's nothing to
// subscribe to — this just makes getConnectedUsername() safe to read during
// render (hydration-safe: returns null on the server, the real value on the
// client) without needing an effect just to mirror it into state.
function subscribeNoop() {
  return () => {};
}

function getServerSnapshot() {
  return null;
}

export default function Basic({ fromDate, toDate }) {
  const svgRef = useRef(null);
  const username = useSyncExternalStore(subscribeNoop, getConnectedUsername, getServerSnapshot);
  const [dailyCounts, setDailyCounts] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!username) return;

    const params = new URLSearchParams();
    if (fromDate) params.set("from_date", fromDate);
    if (toDate) params.set("to_date", toDate);

    fetch(`${API_BASE}/scrobbles/${username}/daily-counts?${params}`)
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Could not load listening history");
        }
        return data;
      })
      .then((data) => setDailyCounts(data.daily_counts))
      .catch((err) => setError(err.message));
  }, [username, fromDate, toDate]);

  useEffect(() => {
    if (!dailyCounts || dailyCounts.length === 0 || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const innerWidth = WIDTH - MARGIN.left - MARGIN.right;
    const innerHeight = HEIGHT - MARGIN.top - MARGIN.bottom;

    const x = d3
      .scaleBand()
      .domain(dailyCounts.map((d) => d.date))
      .range([0, innerWidth])
      .padding(0.2);

    const y = d3
      .scaleLinear()
      .domain([0, d3.max(dailyCounts, (d) => d.count)])
      .nice()
      .range([innerHeight, 0]);

    const g = svg
      .attr("width", WIDTH)
      .attr("height", HEIGHT)
      .append("g")
      .attr("transform", `translate(${MARGIN.left},${MARGIN.top})`);

    const tickEvery = Math.ceil(dailyCounts.length / 10);

    g.append("g")
      .attr("transform", `translate(0,${innerHeight})`)
      .call(
        d3.axisBottom(x).tickValues(x.domain().filter((_, i) => i % tickEvery === 0))
      )
      .selectAll("text")
      .attr("transform", "rotate(-40)")
      .style("text-anchor", "end");

    g.append("g").call(d3.axisLeft(y).ticks(5));

    g.selectAll("rect")
      .data(dailyCounts)
      .join("rect")
      .attr("x", (d) => x(d.date))
      .attr("y", (d) => y(d.count))
      .attr("width", x.bandwidth())
      .attr("height", (d) => innerHeight - y(d.count))
      .attr("fill", "currentColor");
  }, [dailyCounts]);

  if (!username) return <p className="error">Not connected yet — go to home first.</p>;
  if (error) return <p className="error">{error}</p>;
  if (!dailyCounts) return <p>Loading…</p>;
  if (dailyCounts.length === 0) return <p>No listening history to visualize yet.</p>;

  return <svg ref={svgRef} />;
}
