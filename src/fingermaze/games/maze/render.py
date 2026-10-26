"""Visual rendering for the maze, walls, checkpoints, and player cursor."""

from __future__ import annotations

import pygame

from fingermaze.games.maze.domain.collision import MazeLayout
from fingermaze.games.maze.domain.generator import MazeDefinition
from fingermaze.games.maze.domain.grid import Wall
from fingermaze.games.maze.domain.scoring import GameStatus, PlayerGameState

# Simple high-contrast color palette
COLOR_BG = (20, 24, 30)
COLOR_WALL = (180, 190, 205)
COLOR_START = (46, 204, 113)
COLOR_EXIT = (241, 196, 15)
COLOR_CHECKPOINT = (52, 152, 219)
COLOR_CHECKPOINT_PASSED = (39, 174, 96)
COLOR_TRAIL = (0, 220, 255)
COLOR_CURSOR_NORMAL = (0, 245, 255)
COLOR_CURSOR_STUN = (231, 76, 60)
COLOR_TEXT = (240, 245, 250)


class MazeRenderer:
    """Renders maze grid, walls, checkpoints, player, and HUD."""

    def __init__(self, font: pygame.font.Font | None = None) -> None:
        if font is None:
            pygame.font.init()
            self.font = pygame.font.Font(None, 24)
            self.large_font = pygame.font.Font(None, 42)
        else:
            self.font = font
            self.large_font = font

    def draw(
        self,
        surface: pygame.Surface,
        maze_def: MazeDefinition,
        layout: MazeLayout,
        state: PlayerGameState,
    ) -> None:
        # Clear background
        surface.fill(COLOR_BG)

        # Draw Start and Exit zones
        self._draw_cell_highlight(surface, layout, maze_def.start_cell, COLOR_START, "INICIO")
        self._draw_cell_highlight(surface, layout, maze_def.exit_cell, COLOR_EXIT, "META")

        # Draw Checkpoints
        for idx, cp_cell in enumerate(maze_def.checkpoints):
            if cp_cell == maze_def.start_cell or cp_cell == maze_def.exit_cell:
                continue
            color = (
                COLOR_CHECKPOINT_PASSED if idx <= state.active_checkpoint_idx else COLOR_CHECKPOINT
            )
            cx, cy = layout.cell_to_pixel_center(*cp_cell)
            pygame.draw.circle(surface, color, (int(cx), int(cy)), int(layout.cell_width * 0.25))

        # Draw Maze Walls
        self._draw_walls(surface, maze_def, layout)

        # Draw Player Trail
        if len(state.trail) >= 2:
            int_trail = [(int(x), int(y)) for x, y in state.trail]
            pygame.draw.lines(surface, COLOR_TRAIL, False, int_trail, width=3)

        # Draw Player Cursor
        px, py = int(state.current_pos[0]), int(state.current_pos[1])
        cursor_color = (
            COLOR_CURSOR_STUN if state.status == GameStatus.PENALTY_STUN else COLOR_CURSOR_NORMAL
        )
        pygame.draw.circle(surface, cursor_color, (px, py), int(layout.cursor_radius))
        pygame.draw.circle(
            surface, (255, 255, 255), (px, py), max(2, int(layout.cursor_radius * 0.4))
        )

        # Draw HUD overlay
        self._draw_hud(surface, state, maze_def)

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
        # Draw soft background tint
        tint_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        tint_surf.fill((*color, 90))
        surface.blit(tint_surf, (rect.x, rect.y))

        # Text label
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
        # Time display
        time_str = f"Tiempo: {state.elapsed_time:.1f}s"
        penalties_str = f"Penalizaciones: {state.total_penalties} (+{state.total_penalties * state.wall_penalty_s:.0f}s)"
        score_str = f"Total: {state.total_score_time:.1f}s"

        surf_time = self.font.render(time_str, True, COLOR_TEXT)
        surf_pen = self.font.render(
            penalties_str, True, (240, 100, 100) if state.total_penalties > 0 else COLOR_TEXT
        )
        surf_score = self.font.render(score_str, True, COLOR_EXIT)

        surface.blit(surf_time, (20, 15))
        surface.blit(surf_pen, (240, 15))
        surface.blit(surf_score, (560, 15))

        # Checkpoints progress
        cp_str = f"Checkpoint: {state.active_checkpoint_idx + 1} / {len(maze_def.checkpoints)}"
        surf_cp = self.font.render(cp_str, True, COLOR_CHECKPOINT)
        surface.blit(surf_cp, (800, 15))

        # Big Victory / Status Banner
        if state.status == GameStatus.FINISHED:
            banner = self.large_font.render(
                f"¡LABERINTO COMPLETADO! Puntuación: {state.total_score_time:.1f}s",
                True,
                COLOR_EXIT,
            )
            sub = self.font.render("Presiona [R] para jugar un nuevo laberinto", True, COLOR_TEXT)
            b_rect = banner.get_rect(
                center=(surface.get_width() // 2, surface.get_height() // 2 - 20)
            )
            s_rect = sub.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2 + 30))

            bg_rect = b_rect.inflate(40, 90)
            overlay = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            overlay.fill((10, 15, 20, 230))
            surface.blit(overlay, bg_rect.topleft)
            pygame.draw.rect(surface, COLOR_EXIT, bg_rect, width=3, border_radius=8)

            surface.blit(banner, b_rect)
            surface.blit(sub, s_rect)

        elif state.status == GameStatus.PENALTY_STUN:
            alert = self.font.render(
                "¡CHOQUE CON PARED! Penalización aplicada", True, COLOR_CURSOR_STUN
            )
            surface.blit(alert, (surface.get_width() // 2 - alert.get_width() // 2, 50))
