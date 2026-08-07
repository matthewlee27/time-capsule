"use client";

import { useState } from "react";
import { API_BASE } from "@/lib/api";
import { setConnectedUsername } from "@/lib/session";

export default function ConnectForm({ onConnected }) {
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    const trimmed = username.trim();
    if (!trimmed) return;

    try {
      const res = await fetch(`${API_BASE}/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: trimmed }),
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Could not connect to that Last.fm account");
      }

      setConnectedUsername(data.username);
      onConnected(data.username);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form id="username-form" onSubmit={handleSubmit}>
      <label htmlFor="username">Your Last.fm username</label>
      <input
        type="text"
        id="username"
        name="username"
        required
        autoComplete="off"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />
      <button type="submit">Connect</button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
