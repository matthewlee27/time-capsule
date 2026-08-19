"""Fits LIFT_ALPHA/LIFT_BETA (see propLiftEngine.py) from a user's declared
best-to-worst track ranking (PreferenceSort.js / CalibratePage.js, stored via
storage.save_track_ranking).

score = S^alpha / (O+eps)^beta is order-preserving under log: with
x = log(S), y = log(O+eps), z(alpha, beta) = alpha*x - beta*y ranks tracks
identically to score (log is monotonic, score is always > 0), and z is
linear in (alpha, beta) -- fitting reduces to choosing (alpha, beta) that
best reproduces the declared order under z_i - z_j.

Loss: pairwise hinge with a fixed margin over every pair implied by the
user's total order (not just adjacent pairs) -- convex in (alpha, beta);
the margin pins the scale from below so there's no unregularized runaway
toward larger (alpha, beta) the way an unmargined logistic/RankNet loss
would have (no L2 / unit-norm needed).

Optimizer: simulated annealing over a small bounded (alpha, beta) box.
Overkill for a convex 2D problem, but ~30 items / ~435 pairs is cheap
enough to run synchronously inside a request handler, and SA needs no
gradient assumptions if the loss ever stops being convex.
"""

import math
import random
from typing import Dict, List, Tuple

from backend.engines.propLiftEngine import DayCounts, LIFT_EPSILON, _prefix_sums, _range_sum

HINGE_MARGIN = 0.1  # fixed hinge margin -- NOT a fit parameter, mirrors the
                     # fixed-constant style of LIFT_ALPHA/LIFT_BETA/LIFT_EPSILON

ALPHA_BOUNDS = (0.01, 5.0)  # must stay > 0 to keep "reward in-window volume" semantics
BETA_BOUNDS = (0.01, 5.0)   # must stay > 0 to keep "penalize out-of-window volume" semantics

SA_ITERATIONS = 3000     # ~30 items -> pairs are O(1) each once z is precomputed;
                          # 3000 * (~30 + ~435) ops is well under a second in pure Python
SA_INITIAL_TEMP = 1.0
SA_COOLING_RATE = 0.998  # geometric decay; temp_final ~= 1.0 * 0.998**3000 ~= 0.0025,
                          # i.e. effectively greedy by the last iterations
SA_STEP_SCALE = 0.5      # stdev (in alpha/beta units) of the Gaussian proposal at
                          # temp == SA_INITIAL_TEMP; scaled down by temp/SA_INITIAL_TEMP
                          # each iteration so late-stage proposals get progressively
                          # finer, standard combined step+temperature annealing
SA_SEED = 20260812       # fixed seed (propLiftEngine's "8/12" tuning date) so the same
                          # ranking + history always fits the same (alpha, beta)


def build_log_features(
    song_series: Dict[Tuple[str, str], DayCounts],
    window_start: int,
    window_end: int,
    ranked_tracks: List[Tuple[str, str]],
) -> Tuple[List[float], List[float], List[Tuple[str, str]]]:
    """Builds x_i = log(window_plays_i), y_i = log(out_of_window_plays_i + LIFT_EPSILON)
    for each (artist, track) in ranked_tracks (best to worst), preserving order.

    Tracks with window_plays == 0, or missing from song_series entirely, are
    skipped (log(0) is undefined). This shouldn't happen for a ranking whose
    candidates came from storage.get_top_tracks over this exact window --
    every ranked track has window_plays >= 1 by construction -- but scrobbles
    can be deleted/re-pulled between when a ranking was saved and when
    /calibrate runs, so this guards stale data rather than the normal case.

    Returns (x, y, kept_tracks); kept_tracks is ranked_tracks with any
    skipped entries removed, order preserved. Callers must build pairs from
    len(kept_tracks), not len(ranked_tracks).
    """
    x: List[float] = []
    y: List[float] = []
    kept: List[Tuple[str, str]] = []

    for artist, track in ranked_tracks:
        day_counts = song_series.get((artist, track))
        if not day_counts:
            continue

        prefix = _prefix_sums(day_counts)
        total_plays = prefix[-1]
        window_plays = _range_sum(day_counts, prefix, window_start, window_end)
        if window_plays <= 0:
            continue

        out_of_window_plays = total_plays - window_plays
        x.append(math.log(window_plays))
        y.append(math.log(out_of_window_plays + LIFT_EPSILON))
        kept.append((artist, track))

    return x, y, kept


def build_pairs(n: int) -> List[Tuple[int, int]]:
    """All C(n,2) index pairs (i, j), i < j, over a best-to-worst-ordered
    list of n items -- every pair the user's total order implies a
    preference for (i over j), not just adjacent pairs."""
    return [(i, j) for i in range(n) for j in range(i + 1, n)]


def hinge_loss(
    alpha: float, beta: float, x: List[float], y: List[float], pairs: List[Tuple[int, int]]
) -> float:
    """g(alpha, beta) = sum_{(i,j) in pairs} max(0, HINGE_MARGIN - (z_i - z_j)),
    z_i = alpha*x_i - beta*y_i. 0 iff every pair is separated correctly by
    at least the margin."""
    z = [alpha * xi - beta * yi for xi, yi in zip(x, y)]
    return sum(max(0.0, HINGE_MARGIN - (z[i] - z[j])) for i, j in pairs)


def _clamp(value: float, bounds: Tuple[float, float]) -> float:
    lo, hi = bounds
    return max(lo, min(hi, value))


def fit_lift_params(
    x: List[float],
    y: List[float],
    pairs: List[Tuple[int, int]],
    seed: int = SA_SEED,
) -> Dict:
    """Simulated-annealing search over ALPHA_BOUNDS x BETA_BOUNDS minimizing
    hinge_loss. Returns {"alpha": float, "beta": float, "loss": float,
    "pairs_evaluated": int, "correct_fraction": Optional[float]}."""
    rng = random.Random(seed)

    alpha = rng.uniform(*ALPHA_BOUNDS)
    beta = rng.uniform(*BETA_BOUNDS)
    loss = hinge_loss(alpha, beta, x, y, pairs)

    best_alpha, best_beta, best_loss = alpha, beta, loss
    temp = SA_INITIAL_TEMP

    for _ in range(SA_ITERATIONS):
        step = SA_STEP_SCALE * (temp / SA_INITIAL_TEMP)
        candidate_alpha = _clamp(rng.gauss(alpha, step), ALPHA_BOUNDS)
        candidate_beta = _clamp(rng.gauss(beta, step), BETA_BOUNDS)
        candidate_loss = hinge_loss(candidate_alpha, candidate_beta, x, y, pairs)

        delta = candidate_loss - loss
        if delta <= 0 or rng.random() < math.exp(-delta / temp):
            alpha, beta, loss = candidate_alpha, candidate_beta, candidate_loss
            if loss < best_loss:
                best_alpha, best_beta, best_loss = alpha, beta, loss

        temp *= SA_COOLING_RATE

    z = [best_alpha * xi - best_beta * yi for xi, yi in zip(x, y)]
    correct = sum(1 for i, j in pairs if z[i] > z[j])
    correct_fraction = correct / len(pairs) if pairs else None

    return {
        "alpha": best_alpha,
        "beta": best_beta,
        "loss": best_loss,
        "pairs_evaluated": len(pairs),
        "correct_fraction": correct_fraction,
    }
