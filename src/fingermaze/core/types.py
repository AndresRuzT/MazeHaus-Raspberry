"""Core types and data transfer objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class PlayerId(Enum):
    PLAYER_1 = 1
    PLAYER_2 = 2


class TrackingState(Enum):
    TRACKED = auto()
    LOST = auto()
    PAUSED = auto()


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

    def as_int_tuple(self) -> tuple[int, int]:
        return (int(round(self.x)), int(round(self.y)))


@dataclass(frozen=True)
class Viewport:
    x: int
    y: int
    width: int
    height: int

    @property
    def rect(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.width, self.height)


@dataclass(frozen=True)
class HandLandmark:
    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0


@dataclass(frozen=True)
class Pointer:
    player_id: PlayerId
    position: Point2D
    state: TrackingState = TrackingState.TRACKED
    timestamp: float = 0.0
    confidence: float = 1.0


@dataclass(frozen=True)
class InputSnapshot:
    timestamp: float
    pointers: dict[PlayerId, Pointer] = field(default_factory=dict)
    camera_preview: object | None = None

    def get_pointer(self, player_id: PlayerId) -> Pointer | None:
        return self.pointers.get(player_id)
