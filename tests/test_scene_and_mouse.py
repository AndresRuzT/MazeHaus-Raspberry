from __future__ import annotations

import pygame

from fingermaze.config.settings import GameConfig
from fingermaze.core.types import InputSnapshot, PlayerId, Point2D, Pointer, TrackingState
from fingermaze.games.maze.scene import MazeScene
from fingermaze.input.mouse_input import MouseInputProvider


def test_mouse_input_provider() -> None:
    pygame.init()
    pygame.display.set_mode((100, 100))
    provider = MouseInputProvider()
    snapshot = provider.poll(100.0)
    assert snapshot.timestamp == 100.0
    ptr = snapshot.get_pointer(PlayerId.PLAYER_1)
    assert ptr is not None
    assert ptr.state == TrackingState.TRACKED
    provider.close()


def test_maze_scene_lifecycle_and_draw() -> None:
    pygame.init()
    surface = pygame.Surface((800, 600))
    config = GameConfig()
    config.display.width = 800
    config.display.height = 600
    config.maze.cols = 6
    config.maze.rows = 4

    scene = MazeScene(config=config)

    # Initial draw
    scene.draw(surface)

    # Update with pointer tracking
    start_pos = scene.player_state.current_pos
    pointer = Pointer(
        player_id=PlayerId.PLAYER_1,
        position=Point2D(x=start_pos[0] + 2.0, y=start_pos[1] + 2.0),
        state=TrackingState.TRACKED,
    )
    inputs = InputSnapshot(timestamp=1.0, pointers={PlayerId.PLAYER_1: pointer})

    scene.update(0.016, inputs)
    scene.draw(surface)

    # Test pause toggle
    key_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p)
    scene.handle_event(key_event)
    assert scene.is_paused is True
    scene.draw(surface)

    # Test reset toggle
    r_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r)
    scene.handle_event(r_event)

    # Test quit toggle
    esc_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    scene.handle_event(esc_event)
    assert scene.should_quit is True
