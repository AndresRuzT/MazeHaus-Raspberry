"""Single-player maze gameplay scene."""

from __future__ import annotations

import pygame

from fingermaze.config.settings import GameConfig
from fingermaze.core.ports import Scene
from fingermaze.core.types import InputSnapshot, PlayerId, TrackingState
from fingermaze.games.maze.domain.collision import MazeCollisionDetector, MazeLayout
from fingermaze.games.maze.domain.generator import MazeDefinition, generate_maze
from fingermaze.games.maze.domain.scoring import GameStatus, PlayerGameState
from fingermaze.games.maze.render import MazeRenderer


class MazeScene(Scene):
    """Active maze gameplay scene managing collision, progression, and drawing."""

    def __init__(self, config: GameConfig) -> None:
        self.config = config
        self.renderer = MazeRenderer()
        self.should_quit = False
        self.is_paused = False
        self.hand_lost = False

        self._reset_game()

    def _reset_game(self) -> None:
        cols = self.config.maze.cols
        rows = self.config.maze.rows

        # Calculate maze dimensions fitting comfortably on screen with margins
        margin_x = 80.0
        margin_y = 70.0
        available_w = self.config.display.width - 2 * margin_x
        available_h = self.config.display.height - margin_y - 40.0

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

        self.maze_def: MazeDefinition = generate_maze(cols=cols, rows=rows)
        self.collision_detector = MazeCollisionDetector(self.maze_def.grid, self.layout)
        self.player_state = PlayerGameState(
            maze_def=self.maze_def,
            layout=self.layout,
            wall_penalty_s=self.config.maze.wall_penalty_seconds,
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.should_quit = True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.should_quit = True
            elif event.key == pygame.K_r:
                self._reset_game()
            elif event.key == pygame.K_p:
                self.is_paused = not self.is_paused

    def update(self, dt: float, inputs: InputSnapshot) -> None:
        if self.is_paused:
            return

        ptr = inputs.get_pointer(PlayerId.PLAYER_1)
        if ptr is None or ptr.state == TrackingState.LOST:
            self.hand_lost = True
            return

        self.hand_lost = False
        target_pos = ptr.position.as_tuple()
        prev_pos = self.player_state.current_pos

        # Check collision with walls along the movement trajectory
        has_collision = self.collision_detector.check_wall_collision(prev_pos, target_pos)

        # Update player position and timers
        self.player_state.update_position(target_pos, collides=has_collision)
        self.player_state.tick_time(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self.renderer.draw(surface, self.maze_def, self.layout, self.player_state)

        # Lost tracking notification
        if self.hand_lost and self.player_state.status != GameStatus.FINISHED:
            self._draw_overlay_message(
                surface,
                "MANO FUERA DE CAMPO",
                "Coloca tu dedo índice frente a la cámara para reanudar el juego",
                (230, 126, 34),
            )
        elif self.is_paused:
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
        box_w, box_h = 600, 120
        rect = pygame.Rect((w - box_w) // 2, (h - box_h) // 2, box_w, box_h)

        overlay = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        overlay.fill((15, 20, 25, 235))
        surface.blit(overlay, rect.topleft)
        pygame.draw.rect(surface, border_color, rect, width=2, border_radius=6)

        t_surf = self.renderer.large_font.render(title, True, border_color)
        s_surf = self.renderer.font.render(subtitle, True, (240, 240, 240))

        surface.blit(t_surf, t_surf.get_rect(center=(w // 2, h // 2 - 20)))
        surface.blit(s_surf, s_surf.get_rect(center=(w // 2, h // 2 + 25)))
