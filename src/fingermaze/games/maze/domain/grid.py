"""Maze grid structure and wall bitmask representation."""

from __future__ import annotations

from dataclasses import dataclass


class Wall:
    NORTH = 1 << 0  # 1
    EAST = 1 << 1  # 2
    SOUTH = 1 << 2  # 4
    WEST = 1 << 3  # 8
    ALL = NORTH | EAST | SOUTH | WEST  # 15


OPPOSITE_WALL = {
    Wall.NORTH: Wall.SOUTH,
    Wall.SOUTH: Wall.NORTH,
    Wall.EAST: Wall.WEST,
    Wall.WEST: Wall.EAST,
}

DIRECTION_OFFSETS = {
    Wall.NORTH: (0, -1),
    Wall.SOUTH: (0, 1),
    Wall.EAST: (1, 0),
    Wall.WEST: (-1, 0),
}


@dataclass
class MazeGrid:
    cols: int
    rows: int
    cells: list[int]  # 1D array of bitmasks of size cols * rows

    @classmethod
    def create_empty(cls, cols: int, rows: int, initial_wall_state: int = Wall.ALL) -> MazeGrid:
        """Create a grid where every cell initially has all walls closed."""
        return cls(cols=cols, rows=rows, cells=[initial_wall_state] * (cols * rows))

    def index(self, col: int, row: int) -> int:
        return row * self.cols + col

    def is_valid(self, col: int, row: int) -> bool:
        return 0 <= col < self.cols and 0 <= row < self.rows

    def get_walls(self, col: int, row: int) -> int:
        if not self.is_valid(col, row):
            return Wall.ALL
        return self.cells[self.index(col, row)]

    def has_wall(self, col: int, row: int, wall: int) -> bool:
        return bool(self.get_walls(col, row) & wall)

    def remove_wall(self, col: int, row: int, wall: int) -> None:
        if self.is_valid(col, row):
            self.cells[self.index(col, row)] &= ~wall

    def add_wall(self, col: int, row: int, wall: int) -> None:
        if self.is_valid(col, row):
            self.cells[self.index(col, row)] |= wall
