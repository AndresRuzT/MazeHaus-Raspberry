"""High score persistence and leaderboard manager for competitive speedrunning."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_RECORDS_PATH = Path("data/records.json")


@dataclass
class RecordEntry:
    best_time: float
    holder_name: str
    date_str: str


class RecordStore:
    """Manages loading, updating, and saving the all-time historic best time."""

    def __init__(self, file_path: Path | str = DEFAULT_RECORDS_PATH) -> None:
        self.file_path = Path(file_path)
        # Default baseline historic record: 1 minute 15 seconds (75.0s)
        self.current_record = RecordEntry(
            best_time=75.0,
            holder_name="HAUS MASTER",
            date_str="2026-10-26",
        )
        self.load()

    def load(self) -> None:
        """Load historic record from JSON storage if exists."""
        if not self.file_path.exists():
            return

        try:
            with open(self.file_path, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
                self.current_record = RecordEntry(
                    best_time=float(data.get("best_time", 75.0)),
                    holder_name=str(data.get("holder_name", "HAUS MASTER")),
                    date_str=str(data.get("date_str", "2026-10-26")),
                )
                logger.info(
                    f"Loaded historic record: {self.current_record.best_time:.2f}s by {self.current_record.holder_name}"
                )
        except Exception as exc:
            logger.warning(f"Failed to load records from {self.file_path} ({exc}). Using defaults.")

    def save(self) -> None:
        """Persist current record to disk."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self.current_record), f, indent=2)
                logger.info(f"Saved new historic record: {self.current_record.best_time:.2f}s")
        except Exception as exc:
            logger.error(f"Failed to save record to {self.file_path}: {exc}")

    def check_and_update(self, finish_time: float, holder: str = "JUGADOR") -> bool:
        """Update record if new time is faster. Returns True if new all-time record set."""
        if finish_time < self.current_record.best_time:
            import datetime

            today = datetime.date.today().isoformat()
            self.current_record = RecordEntry(
                best_time=round(finish_time, 2),
                holder_name=holder,
                date_str=today,
            )
            self.save()
            return True
        return False
