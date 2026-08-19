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

## as of 8/12 --> these parameters work really well

LIFT_ALPHA = 1.4   # higher = rewards in-window volume more aggressively
LIFT_BETA = 0.6    # higher = penalizes out-of-window volume more aggressively
LIFT_EPSILON = 1.0  # smoothing so a song with zero out-of-window plays stays finite

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
    alpha: float = LIFT_ALPHA,
    beta: float = LIFT_BETA,
) -> List[Dict]:
    """Ranks songs by score_i = S_i^alpha / (O_i + LIFT_EPSILON)^beta,
    where S_i is in-window plays and O_i is out-of-window plays for that song.
    alpha controls how hard in-window volume is rewarded; beta controls how
    hard out-of-window volume is penalized — both default to the global
    LIFT_ALPHA/LIFT_BETA constants but can be overridden with a per-user fit
    from propLiftEngineParams.fit_lift_params.

    min_window_plays filters out songs that barely cleared the window at all,
    independent of how the score above ranks them.
    """
    results = []
    for (artist, track), day_counts in song_series.items():
        prefix = _prefix_sums(day_counts)
        total_plays = prefix[-1]
        window_plays = _range_sum(day_counts, prefix, window_start, window_end)

        if window_plays < min_window_plays:
            continue

        out_of_window_plays = total_plays - window_plays
        score = (window_plays ** alpha) / ((out_of_window_plays + LIFT_EPSILON) ** beta)

        results.append(
            {
                "artist": artist,
                "track": track,
                "window_plays": window_plays,
                "total_plays": total_plays,
                "lift": round(score, 3),
            }
        )

    results.sort(key=lambda r: (r["lift"], r["window_plays"]), reverse=True)
    return results[:limit]
