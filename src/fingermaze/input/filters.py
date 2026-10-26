"""One Euro Filter with noise deadband for jitter-free cursor tracking.

Reference: Casiez et al., '1 € Filter: A Simple Speed-based Low-pass Filter
for Noisy Input in Human-Computer Interaction', CHI 2012.
"""

from __future__ import annotations

import math


class LowPassFilter:
    """Standard first-order low-pass filter."""

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha
        self.y: float | None = None

    def filter(self, value: float, alpha: float | None = None) -> float:
        if alpha is not None:
            self.alpha = alpha
        if self.y is None:
            self.y = value
        else:
            self.y = self.alpha * value + (1.0 - self.alpha) * self.y
        return self.y

    def reset(self) -> None:
        self.y = None


class OneEuroFilter:
    """Adaptive low-pass filter that dynamically adjusts cutoff frequency."""

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.05,
        d_cutoff: float = 1.0,
    ) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff

        self.x_filter = LowPassFilter()
        self.dx_filter = LowPassFilter()
        self.last_time: float | None = None

    def _alpha(self, cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x: float, timestamp: float) -> float:
        if self.last_time is None:
            self.last_time = timestamp
            return self.x_filter.filter(x, alpha=1.0)

        dt = timestamp - self.last_time
        self.last_time = timestamp

        if dt <= 1e-6:
            dt = 1e-6

        prev_x = self.x_filter.y if self.x_filter.y is not None else x
        dx = (x - prev_x) / dt
        edx = self.dx_filter.filter(dx, alpha=self._alpha(self.d_cutoff, dt))

        cutoff = self.min_cutoff + self.beta * abs(edx)
        return self.x_filter.filter(x, alpha=self._alpha(cutoff, dt))

    def reset(self) -> None:
        self.x_filter.reset()
        self.dx_filter.reset()
        self.last_time = None


class OneEuroFilter2D:
    """2D adaptive filter with noise deadband to eliminate stationary tremor."""

    def __init__(
        self,
        min_cutoff: float = 0.8,
        beta: float = 0.35,
        d_cutoff: float = 1.0,
        deadband: float = 3.5,
    ) -> None:
        self.filter_x = OneEuroFilter(min_cutoff=min_cutoff, beta=beta, d_cutoff=d_cutoff)
        self.filter_y = OneEuroFilter(min_cutoff=min_cutoff, beta=beta, d_cutoff=d_cutoff)
        self.deadband = deadband
        self.last_stable_x: float | None = None
        self.last_stable_y: float | None = None

    def filter(self, x: float, y: float, timestamp: float) -> tuple[float, float]:
        # 1. Apply One Euro adaptive low-pass filter
        fx = self.filter_x.filter(x, timestamp)
        fy = self.filter_y.filter(y, timestamp)

        # 2. Apply deadband: if motion is tiny involuntary tremor, freeze at last stable position
        if self.last_stable_x is None or self.last_stable_y is None:
            self.last_stable_x = fx
            self.last_stable_y = fy
            return (fx, fy)

        dist = math.hypot(fx - self.last_stable_x, fy - self.last_stable_y)
        if dist < self.deadband:
            return (self.last_stable_x, self.last_stable_y)

        self.last_stable_x = fx
        self.last_stable_y = fy
        return (fx, fy)

    def reset(self) -> None:
        self.filter_x.reset()
        self.filter_y.reset()
        self.last_stable_x = None
        self.last_stable_y = None
