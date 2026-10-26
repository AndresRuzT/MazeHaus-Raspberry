from __future__ import annotations

from fingermaze.input.filters import OneEuroFilter2D


def test_one_euro_filter_smoothing() -> None:
    filter2d = OneEuroFilter2D(min_cutoff=1.0, beta=0.01)

    t = 0.0
    # Provide noisy inputs around (100.0, 100.0)
    samples = [
        (100.0, 100.0),
        (102.0, 99.0),
        (98.0, 101.0),
        (101.0, 100.0),
        (99.0, 102.0),
    ]

    filtered_pts = []
    for x, y in samples:
        t += 0.033  # ~30 Hz
        fx, fy = filter2d.filter(x, y, t)
        filtered_pts.append((fx, fy))

    # The filtered values should stay near 100 with less deviation than raw noise
    last_fx, last_fy = filtered_pts[-1]
    assert abs(last_fx - 100.0) < 2.0
    assert abs(last_fy - 100.0) < 2.0


def test_one_euro_filter_reset() -> None:
    filter2d = OneEuroFilter2D()
    filter2d.filter(50.0, 50.0, 0.0)
    filter2d.reset()
    assert filter2d.filter_x.last_time is None
    assert filter2d.filter_y.last_time is None
