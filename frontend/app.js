const API_BASE = "/api";

const startBtn = document.getElementById("start-btn");
const usernameForm = document.getElementById("username-form");
const connectError = document.getElementById("connect-error");
const pullSection = document.getElementById("pull-section");
const connectedAs = document.getElementById("connected-as");
const pullBtn = document.getElementById("pull-btn");
const pullStatus = document.getElementById("pull-status");

let connectedUsername = getConnectedUsername();

if (connectedUsername) {
  startBtn.classList.add("hidden");
  usernameForm.classList.add("hidden");
  pullSection.classList.remove("hidden");
  connectedAs.textContent = `Connected as ${connectedUsername}`;

  const lastPull = getLastPull();
  if (lastPull) {
    pullStatus.textContent =
      `Fetched ${lastPull.pulled_from_lastfm} scrobbles — ${lastPull.saved} new, ` +
      `${lastPull.duplicates} already saved (${lastPull.total_stored} stored total).`;
  }
}

startBtn.addEventListener("click", () => {
  startBtn.classList.add("hidden");
  usernameForm.classList.remove("hidden");
});

usernameForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  connectError.classList.add("hidden");

  const username = document.getElementById("username").value.trim();
  if (!username) return;

  try {
    const res = await fetch(`${API_BASE}/connect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username }),
    });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Could not connect to that Last.fm account");
    }

    connectedUsername = data.username;
    setConnectedUsername(connectedUsername);
    connectedAs.textContent = `Connected as ${connectedUsername}`;
    usernameForm.classList.add("hidden");
    pullSection.classList.remove("hidden");
  } catch (err) {
    connectError.textContent = err.message;
    connectError.classList.remove("hidden");
  }
});

pullBtn.addEventListener("click", async () => {
  pullStatus.textContent = "Pulling your scrobble history…";

  const fromDate = document.getElementById("from-date").value || null;
  const toDate = document.getElementById("to-date").value || null;

  try {
    const res = await fetch(`${API_BASE}/pull`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: connectedUsername,
        from_date: fromDate,
        to_date: toDate,
      }),
    });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Pull failed");
    }

    setLastPull(data);
    pullStatus.textContent =
      `Fetched ${data.pulled_from_lastfm} scrobbles — ${data.saved} new, ` +
      `${data.duplicates} already saved (${data.total_stored} stored total).`;
  } catch (err) {
    pullStatus.textContent = err.message;
  }
});
