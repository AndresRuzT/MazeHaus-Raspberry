"""Coordinate normalization and screen space mapping."""

from __future__ import annotations

from dataclasses import dataclass

from fingermaze.core.types import PlayerId, Point2D, Viewport


@dataclass
class ActiveRegion:
    min_x: float = 0.15
    max_x: float = 0.85
    min_y: float = 0.15
    max_y: float = 0.85

    def clamp_and_normalize(self, x: float, y: float) -> tuple[float, float]:
        """Normalize coordinates within active region to [0.0, 1.0]."""
        span_x = max(1e-4, self.max_x - self.min_x)
        span_y = max(1e-4, self.max_y - self.min_y)

        norm_x = (x - self.min_x) / span_x
        norm_y = (y - self.min_y) / span_y

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

    def map_to_viewport(
        self,
        norm_x: float,
        norm_y: float,
        player_id: PlayerId = PlayerId.PLAYER_1,
    ) -> Point2D:
        """Map camera-relative coordinates into pixel coordinates."""
        # Normalize through active region
        nx, ny = self.active_region.clamp_and_normalize(norm_x, norm_y)

        # Scale to viewport dimensions
        px = self.viewport.x + nx * self.viewport.width
        py = self.viewport.y + ny * self.viewport.height

        return Point2D(x=px, y=py)
