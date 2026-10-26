"""Deterministic maze generator using explicit-stack recursive backtracker."""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass

from fingermaze.games.maze.domain.grid import DIRECTION_OFFSETS, OPPOSITE_WALL, MazeGrid, Wall


@dataclass(frozen=True)
class MazeDefinition:
    grid: MazeGrid
    start_cell: tuple[int, int]
    exit_cell: tuple[int, int]
    solution_path: list[tuple[int, int]]
    checkpoints: list[tuple[int, int]]
    seed: int


def generate_maze(cols: int, rows: int, seed: int | None = None) -> MazeDefinition:
    """Generate a deterministic perfect maze (fully connected, no loops)."""
    if seed is None:
        seed = random.randint(0, 2_147_483_647)

    rng = random.Random(seed)
    grid = MazeGrid.create_empty(cols, rows, Wall.ALL)

    start_cell = (0, 0)
    exit_cell = (cols - 1, rows - 1)

    # Iterative Depth-First Search / Recursive Backtracker with explicit stack
    visited = [False] * (cols * rows)
    stack: list[tuple[int, int]] = [start_cell]
    visited[grid.index(0, 0)] = True

    directions = [Wall.NORTH, Wall.EAST, Wall.SOUTH, Wall.WEST]

    while stack:
        col, row = stack[-1]

        # Find unvisited neighbours
        unvisited_neighbours: list[tuple[int, int, int]] = []
        for wall in directions:
            dx, dy = DIRECTION_OFFSETS[wall]
            ncol, nrow = col + dx, row + dy
            if grid.is_valid(ncol, nrow) and not visited[grid.index(ncol, nrow)]:
                unvisited_neighbours.append((ncol, nrow, wall))

        if unvisited_neighbours:
            # Pick a random unvisited neighbor
            ncol, nrow, wall = rng.choice(unvisited_neighbours)

            # Knock down the wall between current and neighbor
            grid.remove_wall(col, row, wall)
            grid.remove_wall(ncol, nrow, OPPOSITE_WALL[wall])

            visited[grid.index(ncol, nrow)] = True
            stack.append((ncol, nrow))
        else:
            stack.pop()

    # Solve the maze using BFS to find the canonical solution path
    solution_path = _find_shortest_path(grid, start_cell, exit_cell)

    # Place checkpoints along the solution path (every ~4-6 cells)
    checkpoints = _compute_checkpoints(solution_path)

    return MazeDefinition(
        grid=grid,
        start_cell=start_cell,
        exit_cell=exit_cell,
        solution_path=solution_path,
        checkpoints=checkpoints,
        seed=seed,
    )


def _find_shortest_path(
    grid: MazeGrid, start: tuple[int, int], target: tuple[int, int]
) -> list[tuple[int, int]]:
    """BFS to find the unique path in a perfect maze."""
    queue: deque[tuple[int, int]] = deque([start])
    parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}

    while queue:
        current = queue.popleft()
        if current == target:
            break

        c, r = current
        for wall in [Wall.NORTH, Wall.EAST, Wall.SOUTH, Wall.WEST]:
            if not grid.has_wall(c, r, wall):
                dx, dy = DIRECTION_OFFSETS[wall]
                neighbor = (c + dx, r + dy)
                if neighbor not in parent:
                    parent[neighbor] = current
                    queue.append(neighbor)

    # Reconstruct path
    path: list[tuple[int, int]] = []
    curr: tuple[int, int] | None = target
    while curr is not None:
        path.append(curr)
        curr = parent.get(curr)
    path.reverse()
    return path


def _compute_checkpoints(
    solution_path: list[tuple[int, int]], interval: int = 5
) -> list[tuple[int, int]]:
    """Select checkpoints evenly along the solution path."""
    if not solution_path:
        return []
    checkpoints: list[tuple[int, int]] = []
    for i in range(0, len(solution_path), interval):
        checkpoints.append(solution_path[i])
    if checkpoints and checkpoints[-1] != solution_path[-1]:
        checkpoints.append(solution_path[-1])
    return checkpoints
