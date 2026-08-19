import pytest

from backend import storage


@pytest.fixture
def conn(tmp_path):
    return storage.connect(tmp_path / "test.db")


def test_upsert_user_is_idempotent(conn):
    id1 = storage.upsert_user(conn, "alice")
    id2 = storage.upsert_user(conn, "alice")
    assert id1 == id2


def test_save_scrobbles_dedupes_on_repull(conn):
    user_id = storage.upsert_user(conn, "alice")
    tracks = [
        {"artist": "A", "track": "Song", "album": None, "mbid": None, "played_at": 100},
    ]
    storage.save_scrobbles(conn, user_id, tracks)
    storage.save_scrobbles(conn, user_id, tracks)  # simulates an overlapping re-pull

    assert storage.scrobble_count(conn, user_id) == 1


def test_save_scrobbles_reports_saved_vs_duplicates(conn):
    user_id = storage.upsert_user(conn, "alice")
    first_batch = [
        {"artist": "A", "track": "Song 1", "album": None, "mbid": None, "played_at": 100},
        {"artist": "A", "track": "Song 2", "album": None, "mbid": None, "played_at": 200},
    ]
    result = storage.save_scrobbles(conn, user_id, first_batch)
    assert result == {"saved": 2, "duplicates": 0}

    # overlapping re-pull: Song 1 repeats, Song 3 is new
    second_batch = first_batch[:1] + [
        {"artist": "A", "track": "Song 3", "album": None, "mbid": None, "played_at": 300},
    ]
    result = storage.save_scrobbles(conn, user_id, second_batch)
    assert result == {"saved": 1, "duplicates": 1}


def test_get_scrobbles_orders_newest_first(conn):
    user_id = storage.upsert_user(conn, "alice")
    storage.save_scrobbles(
        conn,
        user_id,
        [
            {"artist": "A", "track": "Old", "album": None, "mbid": None, "played_at": 100},
            {"artist": "A", "track": "New", "album": None, "mbid": None, "played_at": 200},
        ],
    )

    rows = storage.get_scrobbles(conn, user_id)

    assert [r["track"] for r in rows] == ["New", "Old"]


def test_get_top_tracks_artist_cap_limits_per_artist(conn):
    user_id = storage.upsert_user(conn, "alice")
    # Distinct play counts per track so ranking is unambiguous: A dominates
    # (3 songs, all outranking B/C) unless the cap kicks in.
    play_counts = {
        ("A", "A0"): 10, ("A", "A1"): 9, ("A", "A2"): 8,
        ("B", "B0"): 7, ("B", "B1"): 6,
        ("C", "C0"): 5,
    }
    tracks = [
        {"artist": artist, "track": track, "album": None, "mbid": None, "played_at": t}
        for (artist, track), count in play_counts.items()
        for t in range(count)
    ]
    storage.save_scrobbles(conn, user_id, tracks)

    uncapped = storage.get_top_tracks(conn, user_id, limit=3)
    assert [(t["artist"], t["track"]) for t in uncapped] == [
        ("A", "A0"), ("A", "A1"), ("A", "A2"),
    ]

    capped = storage.get_top_tracks(conn, user_id, limit=3, artist_cap=1)
    assert [(t["artist"], t["track"]) for t in capped] == [
        ("A", "A0"), ("B", "B0"), ("C", "C0"),
    ]


def test_track_ranking_round_trips(conn):
    user_id = storage.upsert_user(conn, "alice")
    ranked = [{"artist": "A", "track": "Best"}, {"artist": "B", "track": "Worst"}]

    storage.save_track_ranking(conn, user_id, 100, 200, ranked)
    result = storage.get_track_ranking(conn, user_id, 100, 200)

    assert [(r["artist"], r["track"], r["rank"]) for r in result] == [
        ("A", "Best", 0), ("B", "Worst", 1),
    ]


def test_get_track_ranking_empty_for_unsaved_range(conn):
    user_id = storage.upsert_user(conn, "alice")
    assert storage.get_track_ranking(conn, user_id, None, None) == []


def test_user_lift_params_round_trip(conn):
    user_id = storage.upsert_user(conn, "alice")
    storage.save_user_lift_params(conn, user_id, 100, 200, alpha=1.8, beta=0.4, loss=0.02)

    result = storage.get_user_lift_params(conn, user_id)

    assert result["alpha"] == 1.8
    assert result["beta"] == 0.4
    assert result["loss"] == 0.02


def test_get_user_lift_params_returns_most_recent_fit_across_ranges(conn):
    user_id = storage.upsert_user(conn, "alice")
    storage.save_user_lift_params(conn, user_id, 100, 200, alpha=1.0, beta=1.0)
    storage.save_user_lift_params(conn, user_id, None, None, alpha=2.0, beta=0.5)

    result = storage.get_user_lift_params(conn, user_id)

    assert (result["alpha"], result["beta"]) == (2.0, 0.5)


def test_save_user_lift_params_replaces_for_same_range(conn):
    user_id = storage.upsert_user(conn, "alice")
    storage.save_user_lift_params(conn, user_id, 100, 200, alpha=1.0, beta=1.0)
    storage.save_user_lift_params(conn, user_id, 100, 200, alpha=2.0, beta=0.5)

    row_count = conn.execute(
        "SELECT COUNT(*) FROM user_lift_params WHERE user_id = ?", (user_id,)
    ).fetchone()[0]

    assert row_count == 1
    result = storage.get_user_lift_params(conn, user_id)
    assert (result["alpha"], result["beta"]) == (2.0, 0.5)
