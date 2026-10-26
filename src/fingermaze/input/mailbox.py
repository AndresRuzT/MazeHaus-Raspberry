"""Thread-safe, single-slot, latest-value mailbox."""

from __future__ import annotations

import threading
from typing import TypeVar

T = TypeVar("T")


class LatestValueMailbox[T]:
    """Stores only the most recently published value.

    Guarantees O(1) non-blocking reads and prevents queue buildup or latency lag.
    """

    def __init__(self, initial_value: T | None = None) -> None:
        self._lock = threading.Lock()
        self._value: T | None = initial_value
        self._revision: int = 0

    def publish(self, value: T) -> None:
        """Publish a new value, overwriting any previous unread value."""
        with self._lock:
            self._value = value
            self._revision += 1

    def read(self) -> tuple[T | None, int]:
        """Read the latest value and its monotonic revision counter."""
        with self._lock:
            return self._value, self._revision

    def read_value(self) -> T | None:
        """Convenience method to read just the latest value."""
        with self._lock:
            return self._value
