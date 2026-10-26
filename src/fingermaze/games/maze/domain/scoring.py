"""Player progression, scoring, checkpoints, and penalties."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from fingermaze.games.maze.domain.collision import MazeLayout
from fingermaze.games.maze.domain.generator import MazeDefinition


class GameStatus(Enum):
    NOT_STARTED = auto()
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
    status: GameStatus = GameStatus.NOT_STARTED

    elapsed_time: float = 0.0
    total_penalties: int = 0
    penalty_stun_timer: float = 0.0
    stun_duration_s: float = 0.4

    trail: list[tuple[float, float]] = field(default_factory=list)
    max_trail_points: int = 300

    def __post_init__(self) -> None:
        start_center = self.layout.cell_to_pixel_center(*self.maze_def.start_cell)
        self.current_pos = start_center
        self.trail.append(start_center)

    def current_checkpoint_pos(self) -> tuple[float, float]:
        cp_cell = self.maze_def.checkpoints[self.active_checkpoint_idx]
        return self.layout.cell_to_pixel_center(*cp_cell)

    def update_position(self, target_pos: tuple[float, float], collides: bool) -> None:
        """Update player position given movement collision result."""
        if self.status in (GameStatus.FINISHED, GameStatus.PAUSED):
            return

        if self.status == GameStatus.PENALTY_STUN:
            return

        if self.status == GameStatus.NOT_STARTED:
            self.status = GameStatus.PLAYING

        if collides:
            # Wall hit penalty
            self.total_penalties += 1
            self.status = GameStatus.PENALTY_STUN
            self.penalty_stun_timer = self.stun_duration_s
            # Reset to current checkpoint
            self.current_pos = self.current_checkpoint_pos()
            self.trail = [self.current_pos]
            return

        # Valid movement
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
                self.status = GameStatus.PLAYING

    @property
    def total_score_time(self) -> float:
        """Total time including penalties."""
        return self.elapsed_time + (self.total_penalties * self.wall_penalty_s)
