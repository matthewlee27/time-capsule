import pytest

from backend.lastfm_client import HistoryHidden, LastFmClient, UserNotFound


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    """Stands in for requests.Session — returns one canned page per call,
    in order, regardless of the params passed."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append(params)
        return FakeResponse(self.pages[len(self.calls) - 1])


def make_track(artist, name, uts=None, nowplaying=False):
    track = {
        "artist": {"#text": artist},
        "name": name,
        "album": {"#text": "Some Album"},
        "mbid": "",
    }
    if nowplaying:
        track["@attr"] = {"nowplaying": "true"}
    else:
        track["date"] = {"uts": str(uts), "#text": "irrelevant"}
    return track


def test_fetch_recent_tracks_paginates_and_skips_nowplaying():
    page1 = {
        "recenttracks": {
            "track": [
                make_track("Artist A", "Song A", nowplaying=True),
                make_track("Artist B", "Song B", uts=900),
            ],
            "@attr": {"page": "1", "totalPages": "2"},
        }
    }
    page2 = {
        "recenttracks": {
            "track": [make_track("Artist C", "Song C", uts=800)],
            "@attr": {"page": "2", "totalPages": "2"},
        }
    }
    client = LastFmClient(api_key="fake", session=FakeSession([page1, page2]))

    tracks = list(client.fetch_recent_tracks("someuser"))

    assert [t["track"] for t in tracks] == ["Song B", "Song C"]
    assert all("played_at" in t for t in tracks)


def test_fetch_recent_tracks_passes_from_to():
    page = {
        "recenttracks": {
            "track": [],
            "@attr": {"page": "1", "totalPages": "1"},
        }
    }
    session = FakeSession([page])
    client = LastFmClient(api_key="fake", session=session)

    list(client.fetch_recent_tracks("someuser", from_ts=100, to_ts=200))

    assert session.calls[0]["from"] == 100
    assert session.calls[0]["to"] == 200


def test_validate_user_raises_for_unknown_user():
    session = FakeSession([{"error": 6, "message": "User not found"}])
    client = LastFmClient(api_key="fake", session=session)

    with pytest.raises(UserNotFound):
        client.validate_user("ghost")


def test_validate_user_raises_for_hidden_history():
    session = FakeSession([{"error": 17, "message": "hidden"}])
    client = LastFmClient(api_key="fake", session=session)

    with pytest.raises(HistoryHidden):
        client.validate_user("privateuser")
