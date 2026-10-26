from __future__ import annotations

from collections import deque

from fingermaze.games.maze.domain.generator import generate_maze
from fingermaze.games.maze.domain.grid import DIRECTION_OFFSETS, Wall


def test_maze_determinism() -> None:
    seed = 42
    maze_1 = generate_maze(cols=10, rows=10, seed=seed)
    maze_2 = generate_maze(cols=10, rows=10, seed=seed)

    assert maze_1.grid.cells == maze_2.grid.cells
    assert maze_1.start_cell == maze_2.start_cell
    assert maze_1.exit_cell == maze_2.exit_cell
    assert maze_1.solution_path == maze_2.solution_path
    assert maze_1.checkpoints == maze_2.checkpoints


def test_maze_fully_connected() -> None:
    cols, rows = 12, 8
    maze = generate_maze(cols=cols, rows=rows, seed=1234)
    grid = maze.grid

    # BFS from (0,0) to verify all cells are reachable
    visited = set()
    queue = deque([(0, 0)])
    visited.add((0, 0))

    while queue:
        col, row = queue.popleft()
        for wall in [Wall.NORTH, Wall.EAST, Wall.SOUTH, Wall.WEST]:
            if not grid.has_wall(col, row, wall):
                dx, dy = DIRECTION_OFFSETS[wall]
                neighbor = (col + dx, row + dy)
                if neighbor not in visited and grid.is_valid(*neighbor):
                    visited.add(neighbor)
                    queue.append(neighbor)

    assert len(visited) == cols * rows


def test_solution_path_reaches_exit() -> None:
    maze = generate_maze(cols=15, rows=10, seed=999)
    assert len(maze.solution_path) > 0
    assert maze.solution_path[0] == maze.start_cell
    assert maze.solution_path[-1] == maze.exit_cell
    assert len(maze.checkpoints) >= 2
