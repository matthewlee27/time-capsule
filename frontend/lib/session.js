// Client-side session state, shared between the home and analyze pages.
// sessionStorage (not localStorage) on purpose — this should clear when
// the tab closes, not linger indefinitely on someone's machine.

const STORAGE_KEYS = {
  username: "timeCapsule.username",
  lastPull: "timeCapsule.lastPull",
  dateRange: "timeCapsule.dateRange",
};

export function getConnectedUsername() {
  return sessionStorage.getItem(STORAGE_KEYS.username);
}

export function setConnectedUsername(username) {
  sessionStorage.setItem(STORAGE_KEYS.username, username);
}

export function clearConnectedUsername() {
  sessionStorage.removeItem(STORAGE_KEYS.username);
  sessionStorage.removeItem(STORAGE_KEYS.lastPull);
  sessionStorage.removeItem(STORAGE_KEYS.dateRange);
}

export function getLastPull() {
  const raw = sessionStorage.getItem(STORAGE_KEYS.lastPull);
  return raw ? JSON.parse(raw) : null;
}

export function setLastPull(summary) {
  sessionStorage.setItem(STORAGE_KEYS.lastPull, JSON.stringify(summary));
}

export function getDateRange() {
  const raw = sessionStorage.getItem(STORAGE_KEYS.dateRange);
  return raw ? JSON.parse(raw) : null;
}

export function setDateRange(range) {
  sessionStorage.setItem(STORAGE_KEYS.dateRange, JSON.stringify(range));
}
