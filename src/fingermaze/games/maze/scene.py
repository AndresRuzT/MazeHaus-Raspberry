"""Single-player maze gameplay scene with aligned center calibration and shortcuts."""

from __future__ import annotations

import math
import random
from enum import Enum, auto
from typing import Any

import pygame

from fingermaze.config.settings import GameConfig
from fingermaze.core.ports import InputProvider, Scene
from fingermaze.core.types import InputSnapshot, PlayerId, TrackingState
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
    """Active maze gameplay scene managing calibration, collision, and drawing."""

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

        # Sidebar positioning (Zero overlap with maze)
        self.sidebar_w = 245
        self.sidebar_x = self.config.display.width - self.sidebar_w - 12

        # High score record persistence & Arcade Feedback
        self.record_store = RecordStore(self.config.maze.records_path)
        self.has_processed_finish = False
        self.is_new_record = False
        self.screen_shake_time = 0.0

        # Calibration & Countdown states
        self.phase = ScenePhase.CALIBRATING
        self.dwell_timer: float = 0.0
        self.dwell_required: float = 0.7
        self.countdown_val: int = 3
        self.countdown_timer: float = 0.0
        self.last_checkpoint_seen = 0

        self._reset_game()

    def _reset_game(self) -> None:
        cols = self.config.maze.cols
        rows = self.config.maze.rows

        margin_x = 20.0
        margin_y = 20.0
        available_w = float(self.sidebar_x - margin_x - 14.0)
        available_h = float(self.config.display.height - 2 * margin_y)

        cell_w = available_w / cols
        cell_h = available_h / rows

        self.layout = MazeLayout(
            origin_x=margin_x,
            origin_y=margin_y,
            cell_width=cell_w,
            cell_height=cell_h,
            wall_thickness=float(self.config.maze.wall_thickness),
            cursor_radius=float(self.config.maze.cursor_radius),
        )

        # Single master map seed for strictly fair competitive leaderboard
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
            elif event.key == pygame.K_r:
                self._reset_game()
                self.phase = ScenePhase.PLAYING
                start_pos = self.player_state.current_checkpoint_pos()
                self.player_state.update_position(start_pos, collides=False)
            elif event.key == pygame.K_c:
                self.phase = ScenePhase.CALIBRATING
                self.dwell_timer = 0.0
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                # Quick skip calibration directly to gameplay
                if self.phase == ScenePhase.CALIBRATING:
                    self.phase = ScenePhase.PLAYING
                    start_pos = self.player_state.current_checkpoint_pos()
                    self.player_state.update_position(start_pos, collides=False)
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
            if self.phase == ScenePhase.PLAYING and self.player_state.status == GameStatus.PLAYING:
                self.player_state.status = GameStatus.WAITING_FOR_TOUCH
            return

        self.hand_lost = False
        self.hand_detected = True
        target_pos = ptr.position.as_tuple()
        self.latest_hand_pos = target_pos

        # 1. Calibration phase
        if self.phase == ScenePhase.CALIBRATING:
            arena_cx, arena_cy = self.get_arena_center()
            dist_to_center = math.hypot(target_pos[0] - arena_cx, target_pos[1] - arena_cy)

            # Generous target tolerance
            if dist_to_center <= 85.0:
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

        # 2. Countdown phase
        if self.phase == ScenePhase.COUNTDOWN:
            self.countdown_timer += dt
            if self.countdown_timer >= 0.35:
                self.countdown_timer = 0.0
                self.countdown_val -= 1
                if self.countdown_val < 0:
                    self.phase = ScenePhase.PLAYING
                    start_pos = self.player_state.current_checkpoint_pos()
                    self.player_state.update_position(start_pos, collides=False)
            return

        # 3. Main Gameplay phase
        self.screen_shake_time = max(0.0, self.screen_shake_time - dt)
        prev_pos = self.player_state.current_pos
        has_collision = self.collision_detector.check_wall_collision(prev_pos, target_pos)

        if has_collision and self.player_state.status == GameStatus.PLAYING:
            self.screen_shake_time = 0.22  # Arcade impact shake
            self.renderer.spawn_sparks(target_pos[0], target_pos[1], (255, 65, 65), count=16)

        old_status = self.player_state.status
        self.player_state.update_position(target_pos, collides=has_collision)
        self.player_state.tick_time(dt)

        if self.player_state.active_checkpoint_idx > self.last_checkpoint_seen:
            self.last_checkpoint_seen = self.player_state.active_checkpoint_idx
            cp_x, cp_y = self.player_state.current_checkpoint_pos()
            self.renderer.spawn_sparks(cp_x, cp_y, (0, 230, 140), count=22)

        if old_status != GameStatus.FINISHED and self.player_state.status == GameStatus.FINISHED:
            if not self.has_processed_finish:
                self.has_processed_finish = True
                self.is_new_record = self.record_store.check_and_update(
                    self.player_state.elapsed_time
                )
                if self.is_new_record:
                    # Explosive golden victory fireworks across entire screen
                    self.renderer.spawn_celebration_fireworks(
                        self.config.display.width, self.config.display.height, count=80
                    )
                else:
                    ex_x, ex_y = self.layout.cell_to_pixel_center(*self.maze_def.exit_cell)
                    self.renderer.spawn_sparks(ex_x, ex_y, (255, 205, 30), count=40, speed=180.0)

    def draw(self, surface: pygame.Surface) -> None:
        if self.phase == ScenePhase.CALIBRATING:
            progress = min(1.0, self.dwell_timer / self.dwell_required)
            self.renderer.draw_calibration(
                surface=surface,
                hand_pos=self.latest_hand_pos,
                dwell_progress=progress,
                camera_preview=self.camera_preview,
                hand_detected=self.hand_detected,
                target_center=self.get_arena_center(),
                status_label=getattr(self, "camera_status_label", "BUSCANDO DEDO"),
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
            status_label=getattr(self, "camera_status_label", "BUSCANDO DEDO"),
            record_entry=self.record_store.current_record,
            is_new_record=self.is_new_record,
            shake_ox=shake_ox,
            shake_oy=shake_oy,
        )

        if self.phase == ScenePhase.COUNTDOWN:
            self.renderer.draw_countdown(surface, self.countdown_val)

        if self.is_paused:
            self._draw_overlay_message(
                surface,
                "JUEGO EN PAUSA",
                "Presiona [P] para continuar",
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
