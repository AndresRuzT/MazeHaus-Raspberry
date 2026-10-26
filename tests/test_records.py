from __future__ import annotations

import tempfile
from pathlib import Path

from fingermaze.games.maze.domain.records import RecordStore


def test_record_store_initialization_and_update() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "test_records.json"
        store = RecordStore(json_path)

        # Baseline should be 75.0s
        assert store.current_record.best_time == 75.0

        # Run with slower time -> not a new record
        assert store.check_and_update(82.0, "SLOW POKE") is False
        assert store.current_record.best_time == 75.0

        # Run with faster time -> new record
        assert store.check_and_update(45.5, "SPEEDY") is True
        assert store.current_record.best_time == 45.5
        assert store.current_record.holder_name == "SPEEDY"

        # Reload from disk
        store2 = RecordStore(json_path)
        assert store2.current_record.best_time == 45.5
        assert store2.current_record.holder_name == "SPEEDY"
