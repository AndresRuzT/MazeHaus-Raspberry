"""Coordinate normalization and screen space mapping with dynamic center calibration."""

from __future__ import annotations

from dataclasses import dataclass

from fingermaze.core.types import PlayerId, Point2D, Viewport


@dataclass
class ActiveRegion:
    center_x: float = 0.5
    center_y: float = 0.5
    span_x: float = 0.60
    span_y: float = 0.50
    min_x: float | None = None
    max_x: float | None = None
    min_y: float | None = None
    max_y: float | None = None

    def __post_init__(self) -> None:
        if self.min_x is not None and self.max_x is not None:
            self.span_x = max(1e-4, self.max_x - self.min_x)
            self.center_x = (self.min_x + self.max_x) / 2.0
        if self.min_y is not None and self.max_y is not None:
            self.span_y = max(1e-4, self.max_y - self.min_y)
            self.center_y = (self.min_y + self.max_y) / 2.0

    def clamp_and_normalize(self, x: float, y: float) -> tuple[float, float]:
        """Normalize coordinates centered around natural resting center to [0.0, 1.0]."""
        half_x = max(1e-4, self.span_x / 2.0)
        half_y = max(1e-4, self.span_y / 2.0)

        dx = x - self.center_x
        dy = y - self.center_y

        norm_x = 0.5 + (dx / (2.0 * half_x))
        norm_y = 0.5 + (dy / (2.0 * half_y))

        clamped_x = max(0.0, min(1.0, norm_x))
        clamped_y = max(0.0, min(1.0, norm_y))
        return (clamped_x, clamped_y)


class CoordinateMapper:
    """Maps normalized landmark coordinates into target screen/viewport space."""

    def __init__(
        self,
        viewport: Viewport,
        active_region: ActiveRegion | None = None,
    ) -> None:
        self.viewport = viewport
        self.active_region = active_region or ActiveRegion()

    def calibrate_center(self, norm_x: float, norm_y: float) -> None:
        """Set the natural resting center of the player's hand."""
        self.active_region.center_x = max(0.2, min(0.8, norm_x))
        self.active_region.center_y = max(0.2, min(0.8, norm_y))

    def map_to_viewport(
        self,
        norm_x: float,
        norm_y: float,
        player_id: PlayerId = PlayerId.PLAYER_1,
    ) -> Point2D:
        """Map camera-relative coordinates into pixel coordinates."""
        nx, ny = self.active_region.clamp_and_normalize(norm_x, norm_y)

        px = self.viewport.x + nx * self.viewport.width
        py = self.viewport.y + ny * self.viewport.height

        return Point2D(x=px, y=py)
