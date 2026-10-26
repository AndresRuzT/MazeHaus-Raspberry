"""Visual rendering for the maze, walls, checkpoints, player cursor, calibration, and PiP."""

from __future__ import annotations

import math
import time
from typing import Any

import pygame

from fingermaze.games.maze.domain.collision import MazeLayout
from fingermaze.games.maze.domain.generator import MazeDefinition
from fingermaze.games.maze.domain.grid import Wall
from fingermaze.games.maze.domain.scoring import GameStatus, PlayerGameState

COLOR_BG = (18, 22, 28)
COLOR_WALL = (170, 185, 200)
COLOR_START = (46, 204, 113)
COLOR_EXIT = (241, 196, 15)
COLOR_CHECKPOINT = (52, 152, 219)
COLOR_CHECKPOINT_PASSED = (39, 174, 96)
COLOR_TRAIL = (0, 220, 255)
COLOR_CURSOR_NORMAL = (0, 245, 255)
COLOR_CURSOR_STUN = (231, 76, 60)
COLOR_HAND_POINTER = (255, 215, 0)
COLOR_TEXT = (240, 245, 250)


class MazeRenderer:
    """Renders maze grid, walls, checkpoints, player, HUD, calibration, and live camera feed."""

    def __init__(self, font: pygame.font.Font | None = None) -> None:
        if font is None:
            pygame.font.init()
            self.font = pygame.font.Font(None, 26)
            self.large_font = pygame.font.Font(None, 44)
            self.huge_font = pygame.font.Font(None, 72)
            self.small_font = pygame.font.Font(None, 20)
        else:
            self.font = font
            self.large_font = font
            self.huge_font = font
            self.small_font = font

    def draw_calibration(
        self,
        surface: pygame.Surface,
        hand_pos: tuple[float, float] | None,
        dwell_progress: float,
        camera_preview: Any,
        hand_detected: bool,
    ) -> None:
        """Render the center calibration screen."""
        surface.fill(COLOR_BG)
        w, h = surface.get_width(), surface.get_height()
        cx, cy = w // 2, h // 2

        # Title and instructions
        title = self.large_font.render("CALIBRACIÓN DE POSICIÓN CÓMODA", True, COLOR_TEXT)
        surface.blit(title, title.get_rect(center=(cx, 90)))

        subtitle = self.font.render(
            "Coloca tu dedo índice en el centro de tu campo de visión para fijar tu postura",
            True,
            (180, 195, 210),
        )
        surface.blit(subtitle, subtitle.get_rect(center=(cx, 130)))

        # Target center circle
        target_r = 55
        pygame.draw.circle(surface, (40, 50, 65), (cx, cy), target_r)
        pygame.draw.circle(surface, (100, 120, 150), (cx, cy), target_r, width=2)
        # Crosshair lines
        pygame.draw.line(
            surface, (80, 100, 120), (cx - target_r - 15, cy), (cx + target_r + 15, cy), 2
        )
        pygame.draw.line(
            surface, (80, 100, 120), (cx, cy - target_r - 15), (cx, cy + target_r + 15), 2
        )

        # Dwell progress ring
        if dwell_progress > 0.0:
            pct_angle = int(dwell_progress * 360)
            arc_rect = pygame.Rect(cx - target_r, cy - target_r, target_r * 2, target_r * 2)
            pygame.draw.arc(surface, COLOR_START, arc_rect, 0, math.radians(pct_angle), width=6)
            prog_txt = self.font.render(f"{int(dwell_progress * 100)}%", True, COLOR_START)
            surface.blit(prog_txt, prog_txt.get_rect(center=(cx, cy)))
        else:
            lbl = self.small_font.render("CENTRO", True, (160, 175, 190))
            surface.blit(lbl, lbl.get_rect(center=(cx, cy)))

        # Bottom tip
        tip = self.small_font.render(
            "A partir de este punto, tus movimientos arriba/abajo e izquierda/derecha serán suaves y naturales",
            True,
            (140, 155, 170),
        )
        surface.blit(tip, tip.get_rect(center=(cx, h - 60)))

        # Hand pointer
        if hand_pos is not None:
            hx, hy = int(hand_pos[0]), int(hand_pos[1])
            pygame.draw.circle(surface, COLOR_HAND_POINTER, (hx, hy), 16, width=2)
            pygame.draw.circle(surface, (255, 255, 255), (hx, hy), 4)

        # Camera PiP
        self._draw_camera_pip(surface, camera_preview, hand_detected)

    def draw_countdown(
        self,
        surface: pygame.Surface,
        count_number: int,
    ) -> None:
        """Render stylish countdown before maze starts."""
        w, h = surface.get_width(), surface.get_height()
        cx, cy = w // 2, h // 2

        text_str = str(count_number) if count_number > 0 else "¡YA!"
        color = COLOR_START if count_number > 0 else COLOR_EXIT
        surf = self.huge_font.render(text_str, True, color)
        rect = surf.get_rect(center=(cx, cy))

        # Soft background glow
        bg_r = pygame.Rect(rect.x - 30, rect.y - 20, rect.width + 60, rect.height + 40)
        overlay = pygame.Surface((bg_r.width, bg_r.height), pygame.SRCALPHA)
        overlay.fill((10, 15, 20, 220))
        surface.blit(overlay, bg_r.topleft)
        pygame.draw.rect(surface, color, bg_r, width=3, border_radius=12)

        surface.blit(surf, rect)

    def draw(
        self,
        surface: pygame.Surface,
        maze_def: MazeDefinition,
        layout: MazeLayout,
        state: PlayerGameState,
        hand_pos: tuple[float, float] | None = None,
        camera_preview: Any = None,
        hand_detected: bool = False,
    ) -> None:
        surface.fill(COLOR_BG)

        # Start and Exit zones
        self._draw_cell_highlight(surface, layout, maze_def.start_cell, COLOR_START, "INICIO")
        self._draw_cell_highlight(surface, layout, maze_def.exit_cell, COLOR_EXIT, "META")

        # Checkpoints
        for idx, cp_cell in enumerate(maze_def.checkpoints):
            if cp_cell == maze_def.start_cell or cp_cell == maze_def.exit_cell:
                continue
            color = (
                COLOR_CHECKPOINT_PASSED if idx <= state.active_checkpoint_idx else COLOR_CHECKPOINT
            )
            cx, cy = layout.cell_to_pixel_center(*cp_cell)
            pygame.draw.circle(surface, color, (int(cx), int(cy)), int(layout.cell_width * 0.22))

        # Maze Walls
        self._draw_walls(surface, maze_def, layout)

        # Pulsing target when waiting for touch
        if state.status == GameStatus.WAITING_FOR_TOUCH:
            self._draw_pulsing_target(surface, layout, state.current_checkpoint_pos())

        # Player Trail
        if len(state.trail) >= 2:
            int_trail = [(int(x), int(y)) for x, y in state.trail]
            pygame.draw.lines(surface, COLOR_TRAIL, False, int_trail, width=5)

        # Maze Runner Head (trace head)
        px, py = int(state.current_pos[0]), int(state.current_pos[1])
        cursor_color = (
            COLOR_CURSOR_STUN if state.status == GameStatus.PENALTY_STUN else COLOR_CURSOR_NORMAL
        )
        pygame.draw.circle(surface, cursor_color, (px, py), int(layout.cursor_radius))
        pygame.draw.circle(
            surface, (255, 255, 255), (px, py), max(2, int(layout.cursor_radius * 0.4))
        )

        # Real-Time Hand Pointer
        if hand_pos is not None:
            hx, hy = int(hand_pos[0]), int(hand_pos[1])
            pygame.draw.circle(
                surface, COLOR_HAND_POINTER, (hx, hy), int(layout.cursor_radius * 1.3), width=2
            )
            pygame.draw.circle(surface, (255, 255, 255), (hx, hy), 3)
            if state.status == GameStatus.PLAYING:
                pygame.draw.line(surface, (*COLOR_HAND_POINTER, 150), (hx, hy), (px, py), width=2)

        # HUD overlay
        self._draw_hud(surface, state, maze_def)

        # Camera PiP
        self._draw_camera_pip(surface, camera_preview, hand_detected)

    def _draw_pulsing_target(
        self,
        surface: pygame.Surface,
        layout: MazeLayout,
        center_pos: tuple[float, float],
    ) -> None:
        cx, cy = int(center_pos[0]), int(center_pos[1])
        pulse = 0.5 + 0.5 * math.sin(time.monotonic() * 6.0)
        base_r = layout.cursor_radius * 1.5
        pulse_r = int(base_r + pulse * 10)
        pulse_surf = pygame.Surface((pulse_r * 2 + 4, pulse_r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(
            pulse_surf,
            (46, 204, 113, int(120 + pulse * 100)),
            (pulse_r + 2, pulse_r + 2),
            pulse_r,
            width=3,
        )
        surface.blit(pulse_surf, (cx - pulse_r - 2, cy - pulse_r - 2))

    def _draw_camera_pip(
        self,
        surface: pygame.Surface,
        camera_preview: Any,
        hand_detected: bool,
    ) -> None:
        pip_w, pip_h = 200, 150
        margin = 15
        pip_x = surface.get_width() - pip_w - margin
        pip_y = margin
        pip_rect = pygame.Rect(pip_x, pip_y, pip_w, pip_h)

        if camera_preview is not None and isinstance(camera_preview, pygame.Surface):
            surface.blit(camera_preview, pip_rect)
        else:
            pygame.draw.rect(surface, (30, 35, 45), pip_rect)
            placeholder = self.small_font.render("Sin señal de cámara", True, (140, 150, 160))
            surface.blit(placeholder, placeholder.get_rect(center=pip_rect.center))

        border_color = (46, 204, 113) if hand_detected else (230, 126, 34)
        status_text = "MANO DETECTADA" if hand_detected else "BUSCANDO DEDO..."
        pygame.draw.rect(surface, border_color, pip_rect, width=2, border_radius=4)

        badge_surf = self.small_font.render(status_text, True, border_color)
        bg_badge = pygame.Rect(pip_x, pip_y + pip_h + 4, pip_w, 20)
        pygame.draw.rect(surface, (15, 18, 24), bg_badge, border_radius=3)
        surface.blit(badge_surf, badge_surf.get_rect(center=bg_badge.center))

    def _draw_cell_highlight(
        self,
        surface: pygame.Surface,
        layout: MazeLayout,
        cell: tuple[int, int],
        color: tuple[int, int, int],
        label: str,
    ) -> None:
        c, r = cell
        x = layout.origin_x + c * layout.cell_width
        y = layout.origin_y + r * layout.cell_height
        rect = pygame.Rect(int(x), int(y), int(layout.cell_width), int(layout.cell_height))

        tint_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        tint_surf.fill((*color, 90))
        surface.blit(tint_surf, (rect.x, rect.y))

        txt = self.font.render(label, True, color)
        txt_rect = txt.get_rect(center=rect.center)
        surface.blit(txt, txt_rect)

    def _draw_walls(
        self,
        surface: pygame.Surface,
        maze_def: MazeDefinition,
        layout: MazeLayout,
    ) -> None:
        grid = maze_def.grid
        th = int(layout.wall_thickness)

        for c in range(grid.cols):
            for r in range(grid.rows):
                x1 = int(layout.origin_x + c * layout.cell_width)
                y1 = int(layout.origin_y + r * layout.cell_height)
                x2 = int(x1 + layout.cell_width)
                y2 = int(y1 + layout.cell_height)

                walls = grid.get_walls(c, r)
                if walls & Wall.NORTH:
                    pygame.draw.line(surface, COLOR_WALL, (x1, y1), (x2, y1), width=th)
                if walls & Wall.SOUTH:
                    pygame.draw.line(surface, COLOR_WALL, (x1, y2), (x2, y2), width=th)
                if walls & Wall.WEST:
                    pygame.draw.line(surface, COLOR_WALL, (x1, y1), (x1, y2), width=th)
                if walls & Wall.EAST:
                    pygame.draw.line(surface, COLOR_WALL, (x2, y1), (x2, y2), width=th)

    def _draw_hud(
        self,
        surface: pygame.Surface,
        state: PlayerGameState,
        maze_def: MazeDefinition,
    ) -> None:
        time_str = f"Tiempo: {state.elapsed_time:.1f}s"
        penalties_str = f"Penalizaciones: {state.total_penalties} (+{state.total_penalties * state.wall_penalty_s:.1f}s)"
        score_str = f"Total: {state.total_score_time:.1f}s"

        surf_time = self.font.render(time_str, True, COLOR_TEXT)
        surf_pen = self.font.render(
            penalties_str,
            True,
            (240, 100, 100) if state.total_penalties > 0 else COLOR_TEXT,
        )
        surf_score = self.font.render(score_str, True, COLOR_EXIT)

        surface.blit(surf_time, (20, 15))
        surface.blit(surf_pen, (200, 15))
        surface.blit(surf_score, (460, 15))

        cp_str = f"Checkpoint: {state.active_checkpoint_idx + 1} / {len(maze_def.checkpoints)}"
        surf_cp = self.font.render(cp_str, True, COLOR_CHECKPOINT)
        surface.blit(surf_cp, (660, 15))

        # Dynamic Game State Prompts
        if state.status == GameStatus.WAITING_FOR_TOUCH:
            target_name = "INICIO" if state.active_checkpoint_idx == 0 else "CHECKPOINT"
            prompt = self.font.render(
                f"Lleva tu dedo al {target_name} para continuar el trazado",
                True,
                COLOR_START,
            )
            surface.blit(prompt, (20, 48))

        elif state.status == GameStatus.PENALTY_STUN:
            alert = self.font.render(
                "¡CHOQUE CON PARED! Regresa al checkpoint...", True, COLOR_CURSOR_STUN
            )
            surface.blit(alert, (20, 48))

        elif state.status == GameStatus.FINISHED:
            banner = self.large_font.render(
                f"¡LABERINTO COMPLETADO! Puntuación Final: {state.total_score_time:.1f}s",
                True,
                COLOR_EXIT,
            )
            sub = self.font.render(
                "Presiona [R] para jugar un nuevo laberinto (o [C] para recalibrar)",
                True,
                COLOR_TEXT,
            )
            b_rect = banner.get_rect(
                center=(surface.get_width() // 2, surface.get_height() // 2 - 20)
            )
            s_rect = sub.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2 + 30))

            bg_rect = b_rect.inflate(40, 90)
            overlay = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            overlay.fill((10, 15, 20, 235))
            surface.blit(overlay, bg_rect.topleft)
            pygame.draw.rect(surface, COLOR_EXIT, bg_rect, width=3, border_radius=8)

            surface.blit(banner, b_rect)
            surface.blit(sub, s_rect)
