"""Thin wrapper around Last.fm's user.getrecenttracks — the default,
no-OAuth data source described in plan.md's "Last.fm Data Access" section.
"""

import time
from typing import Dict, Iterator, Optional

import requests

API_BASE = "https://ws.audioscrobbler.com/2.0/"
PAGE_LIMIT = 200
RATE_LIMIT_DELAY = 0.25  # stay well under Last.fm's 5 req/sec/IP cap

ERROR_USER_NOT_FOUND = 6
ERROR_HIDDEN_HISTORY = 17


class LastFmError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(f"Last.fm error {code}: {message}")
        self.code = code


class UserNotFound(LastFmError):
    pass


class HistoryHidden(LastFmError):
    pass


class LastFmClient:
    def __init__(self, api_key: str, session: Optional[requests.Session] = None):
        if not api_key:
            raise ValueError("LASTFM_API_KEY is not set")
        self.api_key = api_key
        self.session = session or requests.Session()

    def _get(self, **params) -> dict:
        params.setdefault("api_key", self.api_key)
        params.setdefault("format", "json")
        resp = self.session.get(API_BASE, params=params, timeout=10)
        data = resp.json()
        if "error" in data:
            code, message = data["error"], data.get("message", "")
            if code == ERROR_USER_NOT_FOUND:
                raise UserNotFound(code, message)
            if code == ERROR_HIDDEN_HISTORY:
                raise HistoryHidden(code, message)
            raise LastFmError(code, message)
        return data

    def validate_user(self, username: str) -> None:
        """Raises UserNotFound / HistoryHidden if the username can't be used
        as a data source. Cheap (limit=1) — just checks the account is real
        and public."""
        self._get(method="user.getrecenttracks", user=username, limit=1)

    def fetch_recent_tracks(
        self,
        username: str,
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
    ) -> Iterator[Dict]:
        """Yields scrobble rows across the full paginated range, optionally
        bounded by from_ts/to_ts (UNIX seconds) — this is what lets an
        engine like plumb_and_dump query an arbitrary day/month, which
        Spotify's API can't do. Skips the "now playing" entry, which has
        no timestamp."""
        page = 1
        total_pages = 1
        while page <= total_pages:
            params = {"method": "user.getrecenttracks", "user": username,
                      "limit": PAGE_LIMIT, "page": page}
            if from_ts:
                params["from"] = from_ts
            if to_ts:
                params["to"] = to_ts

            data = self._get(**params)
            recent = data["recenttracks"]
            total_pages = int(recent["@attr"]["totalPages"])

            for track in recent.get("track", []):
                if track.get("@attr", {}).get("nowplaying") == "true":
                    continue
                date = track.get("date")
                if not date:
                    continue
                yield {
                    "artist": track["artist"]["#text"],
                    "track": track["name"],
                    "album": (track.get("album") or {}).get("#text") or None,
                    "mbid": track.get("mbid") or None,
                    "played_at": int(date["uts"]),
                }

            page += 1
            if page <= total_pages:
                time.sleep(RATE_LIMIT_DELAY)
