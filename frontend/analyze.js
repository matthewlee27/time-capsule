const status = document.getElementById("status");
const username = getConnectedUsername();

if (username) {
  const lastPull = getLastPull();
  status.textContent = lastPull
    ? `Connected as ${username} — ${lastPull.total_stored} scrobbles stored.`
    : `Connected as ${username} — no history pulled yet.`;
} else {
  status.textContent = "Not connected yet — go to home first.";
}
