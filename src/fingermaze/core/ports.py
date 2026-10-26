"""Key port interfaces for hexagonal architecture."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import numpy.typing as npt
import pygame

from fingermaze.core.types import InputSnapshot

Frame = npt.NDArray[Any]


@runtime_checkable
class CameraSource(Protocol):
    """Port for video capture sources."""

    def open(self) -> None:
        """Initialize and open the camera stream."""
        ...

    def read(self) -> Frame | None:
        """Read the latest captured frame, or None if unavailable."""
        ...

    def close(self) -> None:
        """Release camera resources."""
        ...


@runtime_checkable
class InputProvider(Protocol):
    """Port for input adapters (camera vision, mouse, replay)."""

    def poll(self, now: float) -> InputSnapshot:
        """Poll the latest input state without blocking."""
        ...

    def close(self) -> None:
        """Release any input background threads/resources."""
        ...


@runtime_checkable
class Scene(Protocol):
    """State machine scene for the game loop."""

    def handle_event(self, event: pygame.event.Event) -> None:
        """Process an SDL/Pygame window or input event."""
        ...

    def update(self, dt: float, inputs: InputSnapshot) -> None:
        """Update scene simulation state for the given delta time."""
        ...

    def draw(self, surface: pygame.Surface) -> None:
        """Render the scene onto the target display surface."""
        ...


@runtime_checkable
class Game(Protocol):
    """Protocol for playable games."""

    id: str
    title: str

    def create_scene(self) -> Scene:
        """Create and initialize a new scene for this game."""
        ...
