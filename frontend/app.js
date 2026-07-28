const API_BASE = "/api";

const startBtn = document.getElementById("start-btn");
const usernameForm = document.getElementById("username-form");
const connectError = document.getElementById("connect-error");
const pullSection = document.getElementById("pull-section");
const connectedAs = document.getElementById("connected-as");
const pullBtn = document.getElementById("pull-btn");
const pullStatus = document.getElementById("pull-status");

let connectedUsername = null;

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

    pullStatus.textContent =
      `Pulled ${data.pulled_from_lastfm} scrobbles (${data.total_stored} stored total).`;
  } catch (err) {
    pullStatus.textContent = err.message;
  }
});
