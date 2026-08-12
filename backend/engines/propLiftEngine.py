"""Proportional-lift engine: ranks a user's tracks by how much more often
they were played inside a date window than that song's own all-time rate
would predict — surfaces tracks that spiked, not just ones with the most
total plays.

Uses the sparse per-song structure from algorithms.md: each song is a
sorted (day, count) array with a parallel prefix-sum array, so a window's
play count is two binary searches plus a prefix-sum diff instead of a scan
over the full history.
"""

import bisect
from typing import Dict, List, Tuple

DayCounts = List[Tuple[int, int]]  # sorted (day_ordinal, count) pairs


def _prefix_sums(day_counts: DayCounts) -> List[int]:
    prefix = [0] * (len(day_counts) + 1)
    for i, (_, count) in enumerate(day_counts):
        prefix[i + 1] = prefix[i] + count
    return prefix


def _range_sum(day_counts: DayCounts, prefix: List[int], a: int, b: int) -> int:
    days = [d for d, _ in day_counts]
    lo = bisect.bisect_left(days, a)
    hi = bisect.bisect_right(days, b)
    return prefix[hi] - prefix[lo]


def compute_lift(
    song_series: Dict[Tuple[str, str], DayCounts],
    span_start: int,
    span_end: int,
    window_start: int,
    window_end: int,
    limit: int = 15,
    min_window_plays: int = 5,
) -> List[Dict]:
    """Ranks songs by (plays-per-day inside the window) vs. (plays-per-day
    across the song's whole history). A lift of 2.0 means the song was
    played roughly twice as often, per day, during the window as it
    typically is.

    +1 smoothing on both rates keeps a song with a single lucky play from
    reporting infinite lift, and min_window_plays filters out songs that
    only cleared that smoothing by having near-zero real plays.
    """
    span_days = max(span_end - span_start + 1, 1)
    window_days = max(window_end - window_start + 1, 1)

    results = []
    for (artist, track), day_counts in song_series.items():
        prefix = _prefix_sums(day_counts)
        total_plays = prefix[-1]
        window_plays = _range_sum(day_counts, prefix, window_start, window_end)

        if window_plays < min_window_plays:
            continue

        baseline_rate = (total_plays + 1) / span_days
        window_rate = (window_plays + 1) / window_days
        lift = window_rate / baseline_rate

        results.append(
            {
                "artist": artist,
                "track": track,
                "window_plays": window_plays,
                "total_plays": total_plays,
                "lift": round(lift, 3),
            }
        )

    results.sort(key=lambda r: (r["lift"], r["window_plays"]), reverse=True)
    return results[:limit]
