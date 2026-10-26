from __future__ import annotations

from fingermaze.games.maze.domain.collision import MazeCollisionDetector, MazeLayout
from fingermaze.games.maze.domain.grid import MazeGrid, Wall


def test_collision_with_outer_wall() -> None:
    grid = MazeGrid.create_empty(cols=4, rows=4, initial_wall_state=0)
    layout = MazeLayout(
        origin_x=0.0,
        origin_y=0.0,
        cell_width=100.0,
        cell_height=100.0,
        wall_thickness=4.0,
        cursor_radius=10.0,
    )
    detector = MazeCollisionDetector(grid, layout)

    # Point right at the left boundary (x=2) should collide because threshold is 10 + 2 = 12
    assert detector.check_wall_collision((50.0, 50.0), (5.0, 50.0)) is True

    # Center movement should not collide
    assert detector.check_wall_collision((50.0, 50.0), (60.0, 50.0)) is False


def test_collision_with_internal_wall() -> None:
    grid = MazeGrid.create_empty(cols=2, rows=1, initial_wall_state=0)
    # Add a wall between cell (0, 0) and cell (1, 0)
    grid.add_wall(0, 0, Wall.EAST)
    grid.add_wall(1, 0, Wall.WEST)

    layout = MazeLayout(
        origin_x=0.0,
        origin_y=0.0,
        cell_width=100.0,
        cell_height=100.0,
        wall_thickness=4.0,
        cursor_radius=10.0,
    )
    detector = MazeCollisionDetector(grid, layout)

    # Moving across the wall at x=100 from (50, 50) to (150, 50) must collide
    assert detector.check_wall_collision((50.0, 50.0), (150.0, 50.0)) is True

    # Moving vertically inside cell (0, 0) must not collide
    assert detector.check_wall_collision((50.0, 40.0), (50.0, 60.0)) is False
