"""Player progression, scoring, checkpoints, and penalties."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto

from fingermaze.games.maze.domain.collision import MazeLayout
from fingermaze.games.maze.domain.generator import MazeDefinition


class GameStatus(Enum):
    NOT_STARTED = auto()
    WAITING_FOR_TOUCH = auto()
    PLAYING = auto()
    PENALTY_STUN = auto()
    FINISHED = auto()
    PAUSED = auto()


@dataclass
class PlayerGameState:
    maze_def: MazeDefinition
    layout: MazeLayout
    wall_penalty_s: float = 3.0

    current_pos: tuple[float, float] = field(init=False)
    active_checkpoint_idx: int = 0
    status: GameStatus = GameStatus.WAITING_FOR_TOUCH

    elapsed_time: float = 0.0
    total_penalties: int = 0
    penalty_stun_timer: float = 0.0
    stun_duration_s: float = 0.4

    trail: list[tuple[float, float]] = field(default_factory=list)
    max_trail_points: int = 500

    def __post_init__(self) -> None:
        start_center = self.layout.cell_to_pixel_center(*self.maze_def.start_cell)
        self.current_pos = start_center
        self.trail.append(start_center)

    def current_checkpoint_pos(self) -> tuple[float, float]:
        cp_cell = self.maze_def.checkpoints[self.active_checkpoint_idx]
        return self.layout.cell_to_pixel_center(*cp_cell)

    def activation_radius(self) -> float:
        """Radius around checkpoint to activate/resume tracing."""
        return max(
            self.layout.cursor_radius * 2.0,
            min(self.layout.cell_width, self.layout.cell_height) * 0.45,
        )

    def update_position(self, target_pos: tuple[float, float], collides: bool) -> None:
        """Update player position given movement collision result."""
        if self.status in (GameStatus.FINISHED, GameStatus.PAUSED):
            return

        if self.status == GameStatus.PENALTY_STUN:
            return

        # If waiting to touch checkpoint / start
        if self.status in (GameStatus.WAITING_FOR_TOUCH, GameStatus.NOT_STARTED):
            cp_pos = self.current_checkpoint_pos()
            dist_to_cp = math.hypot(target_pos[0] - cp_pos[0], target_pos[1] - cp_pos[1])
            if dist_to_cp <= self.activation_radius():
                self.status = GameStatus.PLAYING
                self.current_pos = cp_pos
                self.trail = [cp_pos]
            return

        # If actively playing
        if collides:
            # Wall hit penalty
            self.total_penalties += 1
            self.status = GameStatus.PENALTY_STUN
            self.penalty_stun_timer = self.stun_duration_s
            # Reset to current checkpoint
            self.current_pos = self.current_checkpoint_pos()
            self.trail = [self.current_pos]
            return

        # Valid movement along corridor
        self.current_pos = target_pos
        self.trail.append(target_pos)
        if len(self.trail) > self.max_trail_points:
            self.trail.pop(0)

        # Check if reached exit
        exit_cell = self.maze_def.exit_cell
        curr_col, curr_row = self.layout.pixel_to_cell(*self.current_pos)
        if (curr_col, curr_row) == exit_cell:
            self.status = GameStatus.FINISHED
            return

        # Check if reached a further checkpoint
        if self.active_checkpoint_idx + 1 < len(self.maze_def.checkpoints):
            next_cp_cell = self.maze_def.checkpoints[self.active_checkpoint_idx + 1]
            if (curr_col, curr_row) == next_cp_cell:
                self.active_checkpoint_idx += 1

    def tick_time(self, dt: float) -> None:
        """Advance timers according to delta time."""
        if self.status == GameStatus.PLAYING:
            self.elapsed_time += dt
        elif self.status == GameStatus.PENALTY_STUN:
            self.elapsed_time += dt
            self.penalty_stun_timer -= dt
            if self.penalty_stun_timer <= 0:
                self.status = GameStatus.WAITING_FOR_TOUCH

    @property
    def total_score_time(self) -> float:
        """Total time including penalties."""
        return self.elapsed_time + (self.total_penalties * self.wall_penalty_s)
