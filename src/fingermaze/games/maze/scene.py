"""Single-player maze gameplay scene with aligned center calibration and shortcuts."""

from __future__ import annotations

import math
import random
from enum import Enum, auto
from typing import Any

import pygame

from fingermaze.config.settings import GameConfig
from fingermaze.core.ports import InputProvider, Scene
from fingermaze.core.types import InputSnapshot, PlayerId, TrackingState, Viewport
from fingermaze.games.maze.domain.collision import MazeCollisionDetector, MazeLayout
from fingermaze.games.maze.domain.generator import MazeDefinition, generate_maze
from fingermaze.games.maze.domain.records import RecordStore
from fingermaze.games.maze.domain.scoring import GameStatus, PlayerGameState
from fingermaze.games.maze.render import MazeRenderer


class ScenePhase(Enum):
    CALIBRATING = auto()
    COUNTDOWN = auto()
    PLAYING = auto()


class MazeScene(Scene):
    """Active maze gameplay scene managing kiosk attract mode, collision, and drawing."""

    def __init__(
        self,
        config: GameConfig,
        input_provider: InputProvider | None = None,
    ) -> None:
        self.config = config
        self.input_provider = input_provider
        self.renderer = MazeRenderer()
        self.should_quit = False
        self.is_paused = False
        self.hand_lost = False
        self.hand_detected = False
        self.latest_hand_pos: tuple[float, float] | None = None
        self.camera_preview: Any = None
        self.camera_status_label: str = "LOOKING FOR HAND"

        # Display sizing & TV Safe Margins
        self.screen_w = self.config.display.width
        self.screen_h = self.config.display.height
        self.sidebar_w = 260
        self.sidebar_x = self.screen_w - self.sidebar_w - 48

        # Record persistence & Arcade feedback
        self.record_store = RecordStore(self.config.maze.records_path)
        self.has_processed_finish = False
        self.is_new_record = False
        self.screen_shake_time = 0.0

        # Kiosk 20s finish countdown timer
        self.finish_countdown: float = 0.0

        # Inactivity auto-reset timer (kiosk safety if player walks away)
        self.hand_lost_elapsed: float = 0.0

        # Calibration & Countdown states
        self.phase = ScenePhase.CALIBRATING
        self.dwell_timer: float = 0.0
        self.dwell_required: float = 0.65
        self.countdown_val: int = 3
        self.countdown_timer: float = 0.0
        self.last_checkpoint_seen = 0

        self._recompute_layout()
        self._reset_game()

    def on_display_size(self, width: int, height: int) -> None:
        """Handle dynamic window or fullscreen TV resolution changes."""
        if width == self.screen_w and height == self.screen_h:
            return
        self.screen_w = width
        self.screen_h = height
        self._recompute_layout()
        self._sync_player_state_layout()

    def _recompute_layout(self) -> None:
        """Compute layout with TV Safe Margins to prevent TV overscan cut-off."""
        safe_margin_x = max(42.0, self.screen_w * 0.045)
        safe_margin_y = max(28.0, self.screen_h * 0.045)

        self.sidebar_w = int(min(320.0, max(240.0, self.screen_w * 0.20)))
        self.sidebar_x = int(self.screen_w - self.sidebar_w - safe_margin_x)

        margin_x = safe_margin_x
        margin_y = safe_margin_y
        available_w = float(self.sidebar_x - margin_x - 18.0)
        available_h = float(self.screen_h - 2 * margin_y)

        cols = self.config.maze.cols
        rows = self.config.maze.rows
        cell_w = available_w / cols
        cell_h = available_h / rows

        # Dynamic sanity clamping: ensure cursor always fits inside corridors
        min_cell_dim = min(cell_w, cell_h)
        max_allowed_cursor = max(4.0, min_cell_dim * 0.28)
        actual_cursor_radius = min(float(self.config.maze.cursor_radius), max_allowed_cursor)
        actual_wall_thickness = min(
            float(self.config.maze.wall_thickness), max(2.0, actual_cursor_radius * 0.5)
        )

        self.layout = MazeLayout(
            origin_x=margin_x,
            origin_y=margin_y,
            cell_width=cell_w,
            cell_height=cell_h,
            wall_thickness=actual_wall_thickness,
            cursor_radius=actual_cursor_radius,
        )

        arena_viewport = Viewport(
            x=int(self.layout.origin_x),
            y=int(self.layout.origin_y),
            width=int(cols * self.layout.cell_width),
            height=int(rows * self.layout.cell_height),
        )
        if self.input_provider and hasattr(self.input_provider, "update_viewport"):
            self.input_provider.update_viewport(arena_viewport)

    def _sync_player_state_layout(self) -> None:
        if hasattr(self, "player_state") and hasattr(self, "maze_def"):
            self.collision_detector = MazeCollisionDetector(self.maze_def.grid, self.layout)
            self.player_state.layout = self.layout

    def _reset_game(self) -> None:
        cols = self.config.maze.cols
        rows = self.config.maze.rows
        start_cell = (cols // 2, rows // 2)
        seed = self.config.maze.master_seed

        self.maze_def: MazeDefinition = generate_maze(
            cols=cols, rows=rows, seed=seed, start_cell=start_cell
        )
        self.collision_detector = MazeCollisionDetector(self.maze_def.grid, self.layout)
        self.player_state = PlayerGameState(
            maze_def=self.maze_def,
            layout=self.layout,
            wall_penalty_s=self.config.maze.wall_penalty_seconds,
        )
        self.last_checkpoint_seen = 0
        self.has_processed_finish = False
        self.is_new_record = False
        self.screen_shake_time = 0.0
        self.finish_countdown = 0.0
        self.hand_lost_elapsed = 0.0

    def _reset_to_attract(self) -> None:
        """Reset game cleanly back to kiosk attract mode."""
        self._reset_game()
        self.phase = ScenePhase.CALIBRATING
        self.dwell_timer = 0.0

    def get_arena_center(self) -> tuple[float, float]:
        """Exact center coordinates of the playable maze arena."""
        cx = self.layout.origin_x + (self.maze_def.grid.cols * self.layout.cell_width) / 2.0
        cy = self.layout.origin_y + (self.maze_def.grid.rows * self.layout.cell_height) / 2.0
        return (cx, cy)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.should_quit = True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.should_quit = True
            elif event.key in (pygame.K_r, pygame.K_c):
                self._reset_to_attract()
            elif event.key == pygame.K_p:
                self.is_paused = not self.is_paused

    def update(self, dt: float, inputs: InputSnapshot) -> None:
        self.camera_preview = inputs.camera_preview
        self.camera_status_label = inputs.status_label
        self.renderer.update_particles(dt)

        if self.is_paused:
            return

        ptr = inputs.get_pointer(PlayerId.PLAYER_1)
        if ptr is None or ptr.state == TrackingState.LOST:
            self.hand_lost = True
            self.hand_detected = False
            self.latest_hand_pos = None

            if self.phase == ScenePhase.PLAYING:
                if self.player_state.status == GameStatus.PLAYING:
                    self.player_state.status = GameStatus.WAITING_FOR_TOUCH
                # Kiosk safety: if hand lost for 25s, return to attract
                self.hand_lost_elapsed += dt
                if self.hand_lost_elapsed >= 25.0:
                    self._reset_to_attract()
            return

        self.hand_lost = False
        self.hand_detected = True
        self.hand_lost_elapsed = 0.0
        target_pos = ptr.position.as_tuple()
        self.latest_hand_pos = target_pos

        # 1. Kiosk Attract / Calibration Phase
        if self.phase == ScenePhase.CALIBRATING:
            arena_cx, arena_cy = self.get_arena_center()
            dist_to_center = math.hypot(target_pos[0] - arena_cx, target_pos[1] - arena_cy)

            # Generous target radius for effortless kiosk activation
            if dist_to_center <= 90.0:
                self.dwell_timer += dt
                if self.dwell_timer >= self.dwell_required:
                    if self.input_provider and hasattr(self.input_provider, "calibrate_center"):
                        self.input_provider.calibrate_center(ptr.raw_norm[0], ptr.raw_norm[1])
                    self.phase = ScenePhase.COUNTDOWN
                    self.countdown_val = 3
                    self.countdown_timer = 0.0
            else:
                self.dwell_timer = max(0.0, self.dwell_timer - dt * 1.5)
            return

        # 2. Countdown Phase
        if self.phase == ScenePhase.COUNTDOWN:
            self.countdown_timer += dt
            if self.countdown_timer >= 0.40:
                self.countdown_timer = 0.0
                self.countdown_val -= 1
                if self.countdown_val < 0:
                    self.phase = ScenePhase.PLAYING
                    # Keep in WAITING_FOR_TOUCH so player can freely align finger to START
                    self.player_state.status = GameStatus.WAITING_FOR_TOUCH
            return

        # 3. Main Gameplay Phase
        self.screen_shake_time = max(0.0, self.screen_shake_time - dt)

        # Handle Round Finished state (20-second countdown)
        if self.player_state.status == GameStatus.FINISHED:
            self.finish_countdown -= dt
            if self.finish_countdown <= 0.0:
                self._reset_to_attract()
            return

        # Active movement & collision
        prev_pos = self.player_state.current_pos
        has_collision = self.collision_detector.check_wall_collision(prev_pos, target_pos)

        if has_collision and self.player_state.status == GameStatus.PLAYING:
            self.screen_shake_time = 0.22
            self.renderer.spawn_sparks(target_pos[0], target_pos[1], (255, 65, 65), count=16)

        old_status = self.player_state.status
        self.player_state.update_position(target_pos, collides=has_collision)
        self.player_state.tick_time(dt)

        if self.player_state.active_checkpoint_idx > self.last_checkpoint_seen:
            self.last_checkpoint_seen = self.player_state.active_checkpoint_idx
            cp_x, cp_y = self.player_state.current_checkpoint_pos()
            self.renderer.spawn_sparks(cp_x, cp_y, (0, 230, 140), count=22)

        # Trigger Finish logic
        if old_status != GameStatus.FINISHED and self.player_state.status == GameStatus.FINISHED:
            if not self.has_processed_finish:
                self.has_processed_finish = True
                self.finish_countdown = 20.0
                self.is_new_record = self.record_store.check_and_update(
                    self.player_state.total_score_time
                )
                if self.is_new_record:
                    self.renderer.spawn_celebration_fireworks(
                        self.screen_w, self.screen_h, count=80
                    )
                else:
                    ex_x, ex_y = self.layout.cell_to_pixel_center(*self.maze_def.exit_cell)
                    self.renderer.spawn_sparks(ex_x, ex_y, (255, 205, 30), count=40, speed=180.0)

    def draw(self, surface: pygame.Surface) -> None:
        # Auto-detect screen resize if surface dimensions differ
        if surface.get_size() != (self.screen_w, self.screen_h):
            self.on_display_size(surface.get_width(), surface.get_height())

        if self.phase == ScenePhase.CALIBRATING:
            progress = min(1.0, self.dwell_timer / self.dwell_required)
            self.renderer.draw_calibration(
                surface=surface,
                hand_pos=self.latest_hand_pos,
                dwell_progress=progress,
                camera_preview=self.camera_preview,
                hand_detected=self.hand_detected,
                target_center=self.get_arena_center(),
                status_label=self.camera_status_label,
                record_entry=self.record_store.current_record,
                sidebar_x=self.sidebar_x,
                sidebar_w=self.sidebar_w,
                state=self.player_state,
                maze_def=self.maze_def,
            )
            return

        shake_ox, shake_oy = 0, 0
        if self.screen_shake_time > 0.0:
            shake_ox = random.randint(-6, 6)
            shake_oy = random.randint(-6, 6)

        self.renderer.draw(
            surface=surface,
            maze_def=self.maze_def,
            layout=self.layout,
            state=self.player_state,
            hand_pos=self.latest_hand_pos,
            camera_preview=self.camera_preview,
            hand_detected=self.hand_detected,
            sidebar_x=self.sidebar_x,
            sidebar_w=self.sidebar_w,
            status_label=self.camera_status_label,
            record_entry=self.record_store.current_record,
            is_new_record=self.is_new_record,
            shake_ox=shake_ox,
            shake_oy=shake_oy,
            finish_countdown=self.finish_countdown,
        )

        if self.phase == ScenePhase.COUNTDOWN:
            self.renderer.draw_countdown(surface, self.countdown_val)

        if self.is_paused:
            self._draw_overlay_message(
                surface,
                "GAME PAUSED",
                "Press [P] to resume",
                (200, 200, 200),
            )

    def _draw_overlay_message(
        self,
        surface: pygame.Surface,
        title: str,
        subtitle: str,
        border_color: tuple[int, int, int],
    ) -> None:
        w, h = surface.get_width(), surface.get_height()
        box_w, box_h = 500, 110
        rect = pygame.Rect((w - box_w) // 2, (h - box_h) // 2, box_w, box_h)

        overlay = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        overlay.fill((10, 15, 22, 240))
        surface.blit(overlay, rect.topleft)
        pygame.draw.rect(surface, border_color, rect, width=2, border_radius=8)

        t_surf = self.renderer.large_font.render(title, True, border_color)
        s_surf = self.renderer.font.render(subtitle, True, (240, 240, 240))

        surface.blit(t_surf, t_surf.get_rect(center=(w // 2, h // 2 - 20)))
        surface.blit(s_surf, s_surf.get_rect(center=(w // 2, h // 2 + 25)))
