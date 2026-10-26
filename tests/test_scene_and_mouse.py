from __future__ import annotations

import pygame

from fingermaze.config.settings import GameConfig
from fingermaze.core.types import InputSnapshot, PlayerId, Point2D, Pointer, TrackingState
from fingermaze.games.maze.scene import MazeScene, ScenePhase
from fingermaze.input.mouse_input import MouseInputProvider


def test_mouse_input_provider() -> None:
    pygame.init()
    pygame.display.set_mode((100, 100))
    provider = MouseInputProvider()
    provider.calibrate_center(0.5, 0.5)
    snapshot = provider.poll(100.0)
    assert snapshot.timestamp == 100.0
    ptr = snapshot.get_pointer(PlayerId.PLAYER_1)
    assert ptr is not None
    assert ptr.state == TrackingState.TRACKED
    provider.close()


def test_maze_scene_calibration_flow() -> None:
    pygame.init()
    surface = pygame.Surface((800, 600))
    config = GameConfig()
    config.display.width = 800
    config.display.height = 600
    config.maze.cols = 6
    config.maze.rows = 4

    scene = MazeScene(config=config)
    assert scene.phase == ScenePhase.CALIBRATING

    # Draw calibration screen
    scene.draw(surface)

    # Move finger into arena center circle to dwell
    arena_cx, arena_cy = scene.get_arena_center()
    center_ptr = Pointer(
        player_id=PlayerId.PLAYER_1,
        position=Point2D(x=arena_cx, y=arena_cy),
        state=TrackingState.TRACKED,
        raw_norm=(0.5, 0.5),
    )
    inputs = InputSnapshot(timestamp=1.0, pointers={PlayerId.PLAYER_1: center_ptr})

    # Dwell tick
    scene.update(0.5, inputs)
    assert scene.phase == ScenePhase.CALIBRATING
    # Finish dwell -> triggers countdown
    scene.update(0.4, inputs)
    assert scene.phase == ScenePhase.COUNTDOWN

    # Draw countdown
    scene.draw(surface)

    # Countdown tick to completion
    for _ in range(5):
        scene.update(0.4, inputs)

    assert scene.phase == ScenePhase.PLAYING

    # Test reset toggle (R)
    r_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r)
    scene.handle_event(r_event)
    assert scene.phase == ScenePhase.PLAYING

    # Test calibrate shortcut (C)
    c_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c)
    scene.handle_event(c_event)
    assert scene.phase == ScenePhase.CALIBRATING

    # Test pause toggle
    p_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p)
    scene.handle_event(p_event)
    assert scene.is_paused is True

    # Test quit toggle
    esc_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    scene.handle_event(esc_event)
    assert scene.should_quit is True
