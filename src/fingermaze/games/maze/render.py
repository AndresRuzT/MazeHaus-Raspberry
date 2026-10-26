"""High-polish visual rendering for FingerMaze with dedicated sidebar and Cyber-Neon aesthetics."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Any

import pygame

from fingermaze.games.maze.domain.collision import MazeLayout
from fingermaze.games.maze.domain.generator import MazeDefinition
from fingermaze.games.maze.domain.grid import Wall
from fingermaze.games.maze.domain.scoring import GameStatus, PlayerGameState

# --- Cyber-Neon Palette ---
COLOR_BG = (12, 15, 22)
COLOR_ARENA_BG = (15, 19, 28)
COLOR_PANEL_BG = (20, 26, 38)
COLOR_PANEL_BORDER = (40, 52, 72)
COLOR_WALL = (80, 140, 210)
COLOR_WALL_ACCENT = (140, 190, 255)
COLOR_START = (0, 230, 140)
COLOR_EXIT = (255, 205, 30)
COLOR_CHECKPOINT = (0, 200, 255)
COLOR_CHECKPOINT_PASSED = (0, 230, 140)
COLOR_TRAIL_AURA = (0, 210, 255)
COLOR_TRAIL_CORE = (230, 250, 255)
COLOR_CURSOR_NORMAL = (0, 245, 255)
COLOR_CURSOR_STUN = (255, 65, 65)
COLOR_HAND_POINTER = (255, 215, 0)
COLOR_TEXT_PRIMARY = (245, 248, 252)
COLOR_TEXT_MUTED = (140, 158, 180)


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    radius: float
    life: float
    max_life: float

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        if self.life <= 0:
            return
        alpha = int(255 * max(0.0, self.life / self.max_life))
        r = max(1, int(self.radius * (self.life / self.max_life)))
        p_surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(p_surf, (*self.color, alpha), (r + 1, r + 1), r)
        surface.blit(p_surf, (int(self.x - r - 1), int(self.y - r - 1)))


class MazeRenderer:
    """Renders maze arena, sleek HUD sidebar, particles, luminous trails, and camera feed."""

    def __init__(self, font: pygame.font.Font | None = None) -> None:
        if font is None:
            pygame.font.init()
            self.font = pygame.font.Font(None, 24)
            self.large_font = pygame.font.Font(None, 40)
            self.huge_font = pygame.font.Font(None, 76)
            self.small_font = pygame.font.Font(None, 19)
            self.digital_font = pygame.font.Font(None, 34)
        else:
            self.font = font
            self.large_font = font
            self.huge_font = font
            self.small_font = font
            self.digital_font = font

        self.particles: list[Particle] = []
        self._last_spark_time = 0.0

    def spawn_sparks(
        self,
        x: float,
        y: float,
        color: tuple[int, int, int],
        count: int = 15,
        speed: float = 120.0,
    ) -> None:
        """Spawn radiating spark particles."""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            spd = random.uniform(speed * 0.4, speed)
            life = random.uniform(0.3, 0.6)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * spd,
                    vy=math.sin(angle) * spd,
                    color=color,
                    radius=random.uniform(2.5, 4.5),
                    life=life,
                    max_life=life,
                )
            )

    def update_particles(self, dt: float) -> None:
        """Update and cull active particles."""
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw_calibration(
        self,
        surface: pygame.Surface,
        hand_pos: tuple[float, float] | None,
        dwell_progress: float,
        camera_preview: Any,
        hand_detected: bool,
        target_center: tuple[float, float] | None = None,
    ) -> None:
        """Render stylish, welcoming calibration screen aligned with arena center."""
        surface.fill(COLOR_BG)
        w, h = surface.get_width(), surface.get_height()

        if target_center is not None:
            cx, cy = int(target_center[0]), int(target_center[1])
        else:
            cx, cy = w // 2, h // 2

        # Header banner
        title = self.large_font.render("CALIBRACIÓN DE POSICIÓN CÓMODA", True, COLOR_START)
        surface.blit(title, (40, 30))

        subtitle = self.font.render(
            "Coloca tu dedo índice en el círculo central (o presiona [ESPACIO] para jugar ya)",
            True,
            COLOR_TEXT_MUTED,
        )
        surface.blit(subtitle, (40, 75))

        # Target center concentric rings
        target_r = 65
        pulse = 0.5 + 0.5 * math.sin(time.monotonic() * 5.0)
        pygame.draw.circle(surface, (25, 33, 48), (cx, cy), target_r)
        pygame.draw.circle(surface, (60, 80, 110), (cx, cy), target_r, width=2)
        pygame.draw.circle(
            surface,
            (*COLOR_START, int(70 + pulse * 70)),
            (cx, cy),
            int(target_r + pulse * 10),
            width=2,
        )

        # Crosshairs
        pygame.draw.line(
            surface, (60, 80, 110), (cx - target_r - 20, cy), (cx + target_r + 20, cy), 2
        )
        pygame.draw.line(
            surface, (60, 80, 110), (cx, cy - target_r - 20), (cx, cy + target_r + 20), 2
        )

        # Progress Arc
        if dwell_progress > 0.0:
            arc_rect = pygame.Rect(cx - target_r, cy - target_r, target_r * 2, target_r * 2)
            pct_angle = dwell_progress * 360
            pygame.draw.arc(surface, COLOR_START, arc_rect, 0, math.radians(pct_angle), width=7)
            prog_txt = self.digital_font.render(f"{int(dwell_progress * 100)}%", True, COLOR_START)
            surface.blit(prog_txt, prog_txt.get_rect(center=(cx, cy)))
        else:
            lbl = self.small_font.render("CENTRO", True, COLOR_TEXT_MUTED)
            surface.blit(lbl, lbl.get_rect(center=(cx, cy)))

        # Explanatory tip at bottom
        tip = self.small_font.render(
            "Mueve tu dedo hacia el círculo o presiona la barra [ESPACIO] para saltar la calibración",
            True,
            COLOR_TEXT_PRIMARY,
        )
        surface.blit(tip, (40, h - 45))

        # Real-time Hand Pointer (gold reticle)
        if hand_pos is not None:
            hx, hy = int(hand_pos[0]), int(hand_pos[1])
            pygame.draw.circle(surface, COLOR_HAND_POINTER, (hx, hy), 20, width=2)
            pygame.draw.circle(surface, (255, 255, 255), (hx, hy), 4)

        # PiP preview in top right
        self._draw_camera_pip(surface, camera_preview, hand_detected, x=w - 240, y=20, w=220, h=165)

    def draw_countdown(self, surface: pygame.Surface, count_number: int) -> None:
        """Countdown badge overlay before maze begins."""
        w, h = surface.get_width(), surface.get_height()
        cx, cy = w // 2, h // 2

        text_str = str(count_number) if count_number > 0 else "¡YA!"
        color = COLOR_START if count_number > 0 else COLOR_EXIT
        surf = self.huge_font.render(text_str, True, color)
        rect = surf.get_rect(center=(cx, cy))

        bg_r = pygame.Rect(rect.x - 40, rect.y - 25, rect.width + 80, rect.height + 50)
        overlay = pygame.Surface((bg_r.width, bg_r.height), pygame.SRCALPHA)
        overlay.fill((10, 15, 22, 235))
        surface.blit(overlay, bg_r.topleft)
        pygame.draw.rect(surface, color, bg_r, width=3, border_radius=14)

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
        sidebar_x: int = 1015,
        sidebar_w: int = 245,
    ) -> None:
        """Render complete maze arena on left, and zero-overlap HUD sidebar on right."""
        # 1. Clear full window background
        surface.fill(COLOR_BG)

        # 2. Draw Maze Arena panel
        arena_rect = pygame.Rect(
            int(layout.origin_x - 12),
            int(layout.origin_y - 12),
            int(maze_def.grid.cols * layout.cell_width + 24),
            int(maze_def.grid.rows * layout.cell_height + 24),
        )
        pygame.draw.rect(surface, COLOR_ARENA_BG, arena_rect, border_radius=10)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, arena_rect, width=2, border_radius=10)

        # Screen shake offset during wall stun
        shake_ox, shake_oy = 0, 0
        if state.status == GameStatus.PENALTY_STUN and state.penalty_stun_timer > 0.1:
            shake_ox = random.randint(-3, 3)
            shake_oy = random.randint(-3, 3)

        # 3. Draw Start & Exit zones
        self._draw_cell_highlight(
            surface, layout, maze_def.start_cell, COLOR_START, "INICIO", shake_ox, shake_oy
        )
        self._draw_cell_highlight(
            surface, layout, maze_def.exit_cell, COLOR_EXIT, "META", shake_ox, shake_oy
        )

        # 4. Draw Checkpoints
        for idx, cp_cell in enumerate(maze_def.checkpoints):
            if cp_cell == maze_def.start_cell or cp_cell == maze_def.exit_cell:
                continue
            is_passed = idx <= state.active_checkpoint_idx
            color = COLOR_CHECKPOINT_PASSED if is_passed else COLOR_CHECKPOINT
            cx, cy = layout.cell_to_pixel_center(*cp_cell)
            r = int(layout.cell_width * 0.22)
            pygame.draw.circle(surface, color, (int(cx + shake_ox), int(cy + shake_oy)), r)
            pygame.draw.circle(
                surface,
                (255, 255, 255),
                (int(cx + shake_ox), int(cy + shake_oy)),
                max(2, int(r * 0.4)),
            )

        # 5. Draw Maze Walls with Neon Glow
        self._draw_walls(surface, maze_def, layout, shake_ox, shake_oy)

        # 6. Draw Pulsing Target when waiting for touch
        if state.status == GameStatus.WAITING_FOR_TOUCH:
            self._draw_pulsing_target(surface, layout, state.current_checkpoint_pos())

        # 7. Draw Luminous Ink Trail
        self._draw_luminous_trail(surface, state.trail, shake_ox, shake_oy)

        # 8. Draw Player Head (Token)
        px, py = int(state.current_pos[0] + shake_ox), int(state.current_pos[1] + shake_oy)
        cursor_color = (
            COLOR_CURSOR_STUN if state.status == GameStatus.PENALTY_STUN else COLOR_CURSOR_NORMAL
        )
        # Outer soft aura
        aura_surf = pygame.Surface((44, 44), pygame.SRCALPHA)
        pygame.draw.circle(aura_surf, (*cursor_color, 80), (22, 22), 20)
        surface.blit(aura_surf, (px - 22, py - 22))
        # Solid center
        pygame.draw.circle(surface, cursor_color, (px, py), int(layout.cursor_radius))
        pygame.draw.circle(
            surface, (255, 255, 255), (px, py), max(2, int(layout.cursor_radius * 0.4))
        )

        # 9. Draw Real-Time Hand Pointer (The Finger)
        if hand_pos is not None:
            hx, hy = int(hand_pos[0]), int(hand_pos[1])
            pygame.draw.circle(
                surface, COLOR_HAND_POINTER, (hx, hy), int(layout.cursor_radius * 1.3), width=2
            )
            pygame.draw.circle(surface, (255, 255, 255), (hx, hy), 3)
            if state.status == GameStatus.PLAYING:
                pygame.draw.line(surface, (*COLOR_HAND_POINTER, 140), (hx, hy), (px, py), width=2)

        # 10. Draw Active Particles
        for p in self.particles:
            p.draw(surface)

        # 11. Draw Dedicated HUD Sidebar (Guaranteed ZERO overlap with the maze!)
        self._draw_sidebar(
            surface=surface,
            state=state,
            maze_def=maze_def,
            camera_preview=camera_preview,
            hand_detected=hand_detected,
            sidebar_x=sidebar_x,
            sidebar_w=sidebar_w,
        )

        # 12. Victory Banner overlay if finished
        if state.status == GameStatus.FINISHED:
            self._draw_victory_banner(surface, state)

    def _draw_luminous_trail(
        self,
        surface: pygame.Surface,
        trail: list[tuple[float, float]],
        ox: int = 0,
        oy: int = 0,
    ) -> None:
        """Render multi-pass luminous trail with fading tail."""
        if len(trail) < 2:
            return

        points = [(int(x + ox), int(y + oy)) for x, y in trail]

        # Multi-layer line: wide aura + bright core
        pygame.draw.lines(surface, COLOR_TRAIL_AURA, False, points, width=6)
        pygame.draw.lines(surface, COLOR_TRAIL_CORE, False, points, width=2)

    def _draw_pulsing_target(
        self,
        surface: pygame.Surface,
        layout: MazeLayout,
        center_pos: tuple[float, float],
    ) -> None:
        cx, cy = int(center_pos[0]), int(center_pos[1])
        pulse = 0.5 + 0.5 * math.sin(time.monotonic() * 6.0)
        base_r = layout.cursor_radius * 1.6
        pulse_r = int(base_r + pulse * 12)
        pulse_surf = pygame.Surface((pulse_r * 2 + 4, pulse_r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(
            pulse_surf,
            (*COLOR_START, int(110 + pulse * 110)),
            (pulse_r + 2, pulse_r + 2),
            pulse_r,
            width=3,
        )
        surface.blit(pulse_surf, (cx - pulse_r - 2, cy - pulse_r - 2))

    def _draw_cell_highlight(
        self,
        surface: pygame.Surface,
        layout: MazeLayout,
        cell: tuple[int, int],
        color: tuple[int, int, int],
        label: str,
        ox: int = 0,
        oy: int = 0,
    ) -> None:
        c, r = cell
        x = int(layout.origin_x + c * layout.cell_width + ox)
        y = int(layout.origin_y + r * layout.cell_height + oy)
        rect = pygame.Rect(x + 2, y + 2, int(layout.cell_width - 4), int(layout.cell_height - 4))

        tint_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        tint_surf.fill((*color, 80))
        surface.blit(tint_surf, (rect.x, rect.y))
        pygame.draw.rect(surface, color, rect, width=2, border_radius=6)

        txt = self.font.render(label, True, color)
        surface.blit(txt, txt.get_rect(center=rect.center))

    def _draw_walls(
        self,
        surface: pygame.Surface,
        maze_def: MazeDefinition,
        layout: MazeLayout,
        ox: int = 0,
        oy: int = 0,
    ) -> None:
        grid = maze_def.grid
        th = int(layout.wall_thickness)

        for c in range(grid.cols):
            for r in range(grid.rows):
                x1 = int(layout.origin_x + c * layout.cell_width + ox)
                y1 = int(layout.origin_y + r * layout.cell_height + oy)
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

    def _draw_sidebar(
        self,
        surface: pygame.Surface,
        state: PlayerGameState,
        maze_def: MazeDefinition,
        camera_preview: Any,
        hand_detected: bool,
        sidebar_x: int,
        sidebar_w: int,
    ) -> None:
        """Render the sleek right-side HUD panel."""
        sb_h = surface.get_height() - 24
        panel_rect = pygame.Rect(sidebar_x, 12, sidebar_w, sb_h)

        pygame.draw.rect(surface, COLOR_PANEL_BG, panel_rect, border_radius=12)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, panel_rect, width=2, border_radius=12)

        # App Brand Header
        brand = self.large_font.render("MAZEHAUS", True, COLOR_START)
        surface.blit(brand, brand.get_rect(center=(sidebar_x + sidebar_w // 2, 38)))

        # 1. Camera PiP inside Sidebar (centered)
        pip_w = sidebar_w - 24
        pip_h = int(pip_w * 0.75)  # 4:3 ratio
        pip_x = sidebar_x + 12
        pip_y = 65
        self._draw_camera_pip(surface, camera_preview, hand_detected, pip_x, pip_y, pip_w, pip_h)

        # 2. Stats Card Container
        stats_y = pip_y + pip_h + 36
        card_w = sidebar_w - 24
        card_x = sidebar_x + 12

        # Card: Time
        self._draw_stat_card(
            surface=surface,
            x=card_x,
            y=stats_y,
            w=card_w,
            h=62,
            label="TIEMPO TRANSCURRIDO",
            value=f"{state.elapsed_time:.1f} s",
            val_color=COLOR_TEXT_PRIMARY,
        )

        # Card: Penalties
        pen_color = COLOR_CURSOR_STUN if state.total_penalties > 0 else COLOR_START
        pen_str = f"{state.total_penalties} (+{state.total_penalties * state.wall_penalty_s:.1f}s)"
        self._draw_stat_card(
            surface=surface,
            x=card_x,
            y=stats_y + 72,
            w=card_w,
            h=62,
            label="PENALIZACIONES",
            value=pen_str,
            val_color=pen_color,
        )

        # Card: Checkpoints & Progress
        cp_total = len(maze_def.checkpoints)
        cp_curr = min(cp_total, state.active_checkpoint_idx + 1)
        self._draw_stat_card(
            surface=surface,
            x=card_x,
            y=stats_y + 144,
            w=card_w,
            h=62,
            label="CHECKPOINTS",
            value=f"{cp_curr} / {cp_total}",
            val_color=COLOR_CHECKPOINT,
        )

        # 3. Dynamic Status Notification
        notif_y = stats_y + 218
        if state.status == GameStatus.WAITING_FOR_TOUCH:
            target = "INICIO" if state.active_checkpoint_idx == 0 else "CHECKPOINT"
            msg = f"Toca {target} para trazar"
            m_color = COLOR_START
        elif state.status == GameStatus.PENALTY_STUN:
            msg = "¡Choque! Vuelve al punto"
            m_color = COLOR_CURSOR_STUN
        else:
            msg = "¡Sigue el pasillo a META!"
            m_color = COLOR_TEXT_MUTED

        lbl_surf = self.small_font.render(msg, True, m_color)
        notif_bg = pygame.Rect(card_x, notif_y, card_w, 28)
        pygame.draw.rect(surface, (15, 20, 30), notif_bg, border_radius=5)
        surface.blit(lbl_surf, lbl_surf.get_rect(center=notif_bg.center))

        # 4. Keyboard Shortcuts Footer
        footer_y = sb_h - 75
        keys = [
            ("[R] Nuevo", COLOR_TEXT_MUTED),
            ("[C] Calibrar", COLOR_TEXT_MUTED),
            ("[P] Pausar", COLOR_TEXT_MUTED),
        ]
        kx = card_x + 10
        for key_text, kcol in keys:
            ksurf = self.small_font.render(key_text, True, kcol)
            surface.blit(ksurf, (kx, footer_y))
            kx += 72

    def _draw_stat_card(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        w: int,
        h: int,
        label: str,
        value: str,
        val_color: tuple[int, int, int],
    ) -> None:
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surface, (15, 20, 30), rect, border_radius=8)
        pygame.draw.rect(surface, (30, 40, 58), rect, width=1, border_radius=8)

        lbl_s = self.small_font.render(label, True, COLOR_TEXT_MUTED)
        val_s = self.digital_font.render(value, True, val_color)

        surface.blit(lbl_s, (x + 10, y + 8))
        surface.blit(val_s, (x + 10, y + 27))

    def _draw_camera_pip(
        self,
        surface: pygame.Surface,
        camera_preview: Any,
        hand_detected: bool,
        x: int,
        y: int,
        w: int,
        h: int,
    ) -> None:
        pip_rect = pygame.Rect(x, y, w, h)

        if camera_preview is not None and isinstance(camera_preview, pygame.Surface):
            # Scale preview cleanly to fill pip_rect
            scaled = pygame.transform.smoothscale(camera_preview, (w, h))
            surface.blit(scaled, pip_rect)
        else:
            pygame.draw.rect(surface, (25, 32, 46), pip_rect, border_radius=6)
            placeholder = self.small_font.render("Esperando Cámara...", True, COLOR_TEXT_MUTED)
            surface.blit(placeholder, placeholder.get_rect(center=pip_rect.center))

        border_color = COLOR_START if hand_detected else (230, 130, 35)
        status_text = "MANO DETECTADA" if hand_detected else "BUSCANDO DEDO"
        pygame.draw.rect(surface, border_color, pip_rect, width=2, border_radius=6)

        # Status badge below preview
        bg_badge = pygame.Rect(x, y + h + 4, w, 22)
        pygame.draw.rect(surface, (14, 18, 26), bg_badge, border_radius=4)
        badge_surf = self.small_font.render(status_text, True, border_color)
        surface.blit(badge_surf, badge_surf.get_rect(center=bg_badge.center))

    def _draw_victory_banner(self, surface: pygame.Surface, state: PlayerGameState) -> None:
        w, h = surface.get_width(), surface.get_height()
        box_w, box_h = 680, 170
        rect = pygame.Rect((w - box_w) // 2, (h - box_h) // 2, box_w, box_h)

        overlay = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        overlay.fill((10, 15, 24, 240))
        surface.blit(overlay, rect.topleft)
        pygame.draw.rect(surface, COLOR_EXIT, rect, width=3, border_radius=12)

        banner = self.large_font.render("¡LABERINTO COMPLETADO!", True, COLOR_EXIT)
        score_txt = self.font.render(
            f"Tiempo Final: {state.total_score_time:.1f}s   (Base: {state.elapsed_time:.1f}s + Penalizaciones: {state.total_penalties * state.wall_penalty_s:.1f}s)",
            True,
            COLOR_TEXT_PRIMARY,
        )
        sub = self.small_font.render(
            "Presiona [R] para jugar un nuevo laberinto (o [C] para recalibrar)",
            True,
            COLOR_TEXT_MUTED,
        )

        surface.blit(banner, banner.get_rect(center=(w // 2, h // 2 - 40)))
        surface.blit(score_txt, score_txt.get_rect(center=(w // 2, h // 2 + 5)))
        surface.blit(sub, sub.get_rect(center=(w // 2, h // 2 + 50)))
