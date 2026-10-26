"""Continuous collision detection between pointer and maze cell walls."""

from __future__ import annotations

import math
from dataclasses import dataclass

from fingermaze.games.maze.domain.grid import MazeGrid, Wall


@dataclass(frozen=True)
class MazeLayout:
    origin_x: float
    origin_y: float
    cell_width: float
    cell_height: float
    wall_thickness: float
    cursor_radius: float

    def cell_to_pixel_center(self, col: int, row: int) -> tuple[float, float]:
        cx = self.origin_x + (col + 0.5) * self.cell_width
        cy = self.origin_y + (row + 0.5) * self.cell_height
        return (cx, cy)

    def pixel_to_cell(self, x: float, y: float) -> tuple[int, int]:
        col = int((x - self.origin_x) // self.cell_width)
        row = int((y - self.origin_y) // self.cell_height)
        return (col, row)


def _distance_point_to_segment(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> float:
    """Compute the shortest Euclidean distance from a point to a line segment."""
    dx = x2 - x1
    dy = y2 - y1
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq == 0:
        return math.hypot(px - x1, py - y1)

    # Project point onto segment, clamping t to [0, 1]
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / seg_len_sq))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


class MazeCollisionDetector:
    """Detects collisions between moving pointers and maze walls."""

    def __init__(self, grid: MazeGrid, layout: MazeLayout) -> None:
        self.grid = grid
        self.layout = layout

    def check_wall_collision(
        self,
        p_from: tuple[float, float],
        p_to: tuple[float, float],
    ) -> bool:
        """Check if moving from p_from to p_to collides with any maze wall.

        Uses continuous sampling along the trajectory to prevent tunneling.
        """
        x1, y1 = p_from
        x2, y2 = p_to
        dist = math.hypot(x2 - x1, y2 - y1)

        radius = self.layout.cursor_radius
        threshold = radius + (self.layout.wall_thickness / 2.0)

        # Number of samples along trajectory
        step_size = max(2.0, radius / 2.0)
        num_steps = max(1, int(math.ceil(dist / step_size)))

        for i in range(num_steps + 1):
            alpha = i / num_steps
            sample_x = x1 + alpha * (x2 - x1)
            sample_y = y1 + alpha * (y2 - y1)

            if self._point_collides_with_walls(sample_x, sample_y, threshold):
                return True

        return False

    def _point_collides_with_walls(self, px: float, py: float, threshold: float) -> bool:
        layout = self.layout
        grid = self.grid

        # Check bounds with outer arena
        min_x = layout.origin_x
        min_y = layout.origin_y
        max_x = layout.origin_x + grid.cols * layout.cell_width
        max_y = layout.origin_y + grid.rows * layout.cell_height

        if (
            px < min_x + threshold
            or px > max_x - threshold
            or py < min_y + threshold
            or py > max_y - threshold
        ):
            # Collided with outer boundary
            return True

        # Find neighboring cells around point
        col, row = layout.pixel_to_cell(px, py)

        # Check cells in a 3x3 neighborhood around the point
        for c in range(max(0, col - 1), min(grid.cols, col + 2)):
            for r in range(max(0, row - 1), min(grid.rows, row + 2)):
                cell_x1 = layout.origin_x + c * layout.cell_width
                cell_y1 = layout.origin_y + r * layout.cell_height
                cell_x2 = cell_x1 + layout.cell_width
                cell_y2 = cell_y1 + layout.cell_height

                walls = grid.get_walls(c, r)

                # North wall
                if walls & Wall.NORTH:
                    d = _distance_point_to_segment(px, py, cell_x1, cell_y1, cell_x2, cell_y1)
                    if d < threshold:
                        return True

                # South wall
                if walls & Wall.SOUTH:
                    d = _distance_point_to_segment(px, py, cell_x1, cell_y2, cell_x2, cell_y2)
                    if d < threshold:
                        return True

                # West wall
                if walls & Wall.WEST:
                    d = _distance_point_to_segment(px, py, cell_x1, cell_y1, cell_x1, cell_y2)
                    if d < threshold:
                        return True

                # East wall
                if walls & Wall.EAST:
                    d = _distance_point_to_segment(px, py, cell_x2, cell_y1, cell_x2, cell_y2)
                    if d < threshold:
                        return True

        return False
