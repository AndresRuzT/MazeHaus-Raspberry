"""Fixed-timestep game loop and display manager."""

from __future__ import annotations

import logging
import time

import pygame

from fingermaze.config.settings import GameConfig
from fingermaze.core.ports import InputProvider, Scene

logger = logging.getLogger(__name__)


class GameLoop:
    """Manages the rendering window, timing, and main game loop execution."""

    def __init__(
        self,
        config: GameConfig,
        input_provider: InputProvider,
        initial_scene: Scene,
    ) -> None:
        self.config = config
        self.input_provider = input_provider
        self.scene = initial_scene
        self.clock = pygame.time.Clock()
        self.running = False

    def run(self) -> None:
        """Initialize SDL display and enter the main loop."""
        pygame.init()
        pygame.font.init()

        disp_cfg = self.config.display
        flags = pygame.DOUBLEBUF
        if disp_cfg.fullscreen:
            flags |= pygame.FULLSCREEN

        screen = pygame.display.set_mode((disp_cfg.width, disp_cfg.height), flags)
        pygame.display.set_caption("FingerMaze (MazeHaus)")

        self.running = True
        target_fps = disp_cfg.target_fps
        last_time = time.monotonic()

        logger.info(
            f"Main loop running at target {target_fps} FPS on {disp_cfg.width}x{disp_cfg.height}"
        )

        try:
            while self.running:
                now = time.monotonic()
                dt = now - last_time
                last_time = now

                # Clamp delta time to avoid large jumps if window is moved or paused
                clamped_dt = min(dt, 0.05)

                # Process window and key events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        break
                    self.scene.handle_event(event)

                # Poll input provider (non-blocking)
                inputs = self.input_provider.poll(now)

                # Update simulation
                self.scene.update(clamped_dt, inputs)

                # Check if scene requested quit
                if getattr(self.scene, "should_quit", False):
                    self.running = False
                    break

                # Render frame
                self.scene.draw(screen)
                pygame.display.flip()

                # Regulate frame rate
                self.clock.tick(target_fps)

        finally:
            logger.info("Cleaning up resources on main loop exit...")
            self.input_provider.close()
            pygame.quit()
