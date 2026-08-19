import math

from backend.engines import propLiftEngineParams as params


def test_build_log_features_skips_zero_and_missing_tracks():
    song_series = {
        ("A", "Has plays"): [(1, 5), (10, 3)],
        ("B", "Zero in window"): [(1, 4)],  # all plays outside [5, 20]
    }
    ranked_tracks = [("A", "Has plays"), ("B", "Zero in window"), ("C", "Missing")]

    x, y, kept = params.build_log_features(song_series, window_start=5, window_end=20, ranked_tracks=ranked_tracks)

    assert kept == [("A", "Has plays")]
    assert len(x) == len(y) == 1
    assert x[0] == math.log(3)  # window_plays = 3 (the day-10 count)
    assert y[0] == math.log(5 + 1)  # out_of_window_plays = 5, + LIFT_EPSILON (1.0)


def test_build_pairs_produces_all_combinations():
    pairs = params.build_pairs(4)
    assert len(pairs) == 6
    assert pairs == [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    assert all(i < j for i, j in pairs)


def test_hinge_loss_zero_when_perfectly_separated():
    # x favors index 0 over 1 by a wide margin; y is flat, so any alpha, beta > 0
    # separates z_0 > z_1 by more than HINGE_MARGIN.
    x = [10.0, 0.0]
    y = [0.0, 0.0]
    pairs = [(0, 1)]

    assert params.hinge_loss(1.0, 1.0, x, y, pairs) == 0.0


def test_hinge_loss_positive_when_order_violated():
    x = [0.0, 10.0]  # index 1 actually has the higher x, but pair says 0 should beat 1
    y = [0.0, 0.0]
    pairs = [(0, 1)]

    assert params.hinge_loss(1.0, 1.0, x, y, pairs) > 0.0


def test_fit_lift_params_recovers_known_direction_on_separable_data():
    # Construct x/y so that the true ranking is reproduced by alpha=2, beta=1,
    # with a comfortable margin, then check the fit finds a low-loss, correct solution.
    true_alpha, true_beta = 2.0, 1.0
    raw = [(3.0, 0.5), (2.0, 0.3), (2.5, 1.5), (1.0, 0.2), (0.5, 0.1)]
    z_true = [true_alpha * xi - true_beta * yi for xi, yi in raw]
    order = sorted(range(len(raw)), key=lambda i: z_true[i], reverse=True)
    x = [raw[i][0] for i in order]
    y = [raw[i][1] for i in order]

    pairs = params.build_pairs(len(x))
    fit = params.fit_lift_params(x, y, pairs)

    assert fit["pairs_evaluated"] == len(pairs)
    assert fit["correct_fraction"] == 1.0
    assert fit["loss"] < 1e-6
