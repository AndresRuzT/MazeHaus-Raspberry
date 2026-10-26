"""Mouse input adapter for development, testing, and fallback."""

from __future__ import annotations

import pygame

from fingermaze.core.ports import InputProvider
from fingermaze.core.types import InputSnapshot, PlayerId, Point2D, Pointer, TrackingState


class MouseInputProvider(InputProvider):
    """Provides cursor input from standard system mouse."""

    def __init__(self, player_id: PlayerId = PlayerId.PLAYER_1) -> None:
        self.player_id = player_id

    def poll(self, now: float) -> InputSnapshot:
        mx, my = pygame.mouse.get_pos()
        pointer = Pointer(
            player_id=self.player_id,
            position=Point2D(x=float(mx), y=float(my)),
            state=TrackingState.TRACKED,
            timestamp=now,
            confidence=1.0,
        )
        return InputSnapshot(
            timestamp=now,
            pointers={self.player_id: pointer},
        )

    def close(self) -> None:
        pass
