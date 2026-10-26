"""Vision input provider bridging background worker to game loop."""

from __future__ import annotations

from fingermaze.core.ports import InputProvider
from fingermaze.core.types import InputSnapshot, PlayerId, Point2D, Pointer, TrackingState
from fingermaze.input.filters import OneEuroFilter2D
from fingermaze.input.mailbox import LatestValueMailbox
from fingermaze.input.mapping import CoordinateMapper
from fingermaze.input.vision_worker import RawDetectionSnapshot, VisionWorker


class VisionInputProvider(InputProvider):
    """Provides filtered, screen-mapped pointer snapshots from the vision worker."""

    def __init__(
        self,
        worker: VisionWorker,
        mailbox: LatestValueMailbox[RawDetectionSnapshot],
        mapper: CoordinateMapper,
        hand_lost_timeout_s: float = 1.0,
        filter_min_cutoff: float = 1.0,
        filter_beta: float = 0.05,
    ) -> None:
        self.worker = worker
        self.mailbox = mailbox
        self.mapper = mapper
        self.hand_lost_timeout_s = hand_lost_timeout_s

        # Per-player One Euro filters
        self.filters: dict[PlayerId, OneEuroFilter2D] = {
            PlayerId.PLAYER_1: OneEuroFilter2D(min_cutoff=filter_min_cutoff, beta=filter_beta),
            PlayerId.PLAYER_2: OneEuroFilter2D(min_cutoff=filter_min_cutoff, beta=filter_beta),
        }

        # Cached last known pointers
        self.last_pointers: dict[PlayerId, Pointer] = {}
        self.last_seen_time: dict[PlayerId, float] = {}

    def calibrate_center(self, norm_x: float, norm_y: float) -> None:
        """Calibrate the natural center point of the hand in camera space."""
        self.mapper.calibrate_center(norm_x, norm_y)

    def poll(self, now: float) -> InputSnapshot:
        snapshot, _ = self.mailbox.read()
        current_pointers: dict[PlayerId, Pointer] = {}
        preview_surf = snapshot.preview_surface if snapshot is not None else None
        status_label = snapshot.status_label if snapshot is not None else "BUSCANDO DEDO"

        if snapshot is not None and snapshot.has_hand:
            for sample in snapshot.samples:
                # If pointing gesture is not confirmed (e.g. open hand), freeze position to prevent erratic jumps
                if sample.confidence < 0.5 and sample.player_id in self.last_pointers:
                    prev_ptr = self.last_pointers[sample.player_id]
                    current_pointers[sample.player_id] = Pointer(
                        player_id=sample.player_id,
                        position=prev_ptr.position,
                        state=TrackingState.TRACKED,
                        timestamp=now,
                        confidence=sample.confidence,
                        raw_norm=(sample.norm_x, sample.norm_y),
                    )
                    self.last_seen_time[sample.player_id] = now
                    continue

                # Coordinate mapping
                mapped_pt = self.mapper.map_to_viewport(
                    sample.norm_x, sample.norm_y, player_id=sample.player_id
                )

                # Low-pass adaptive filtering
                filt = self.filters.setdefault(
                    sample.player_id,
                    OneEuroFilter2D(),
                )
                filtered_x, filtered_y = filt.filter(mapped_pt.x, mapped_pt.y, now)

                pointer = Pointer(
                    player_id=sample.player_id,
                    position=Point2D(x=filtered_x, y=filtered_y),
                    state=TrackingState.TRACKED,
                    timestamp=now,
                    confidence=sample.confidence,
                    raw_norm=(sample.norm_x, sample.norm_y),
                )
                current_pointers[sample.player_id] = pointer
                self.last_pointers[sample.player_id] = pointer
                self.last_seen_time[sample.player_id] = now

        # Check for lost tracking on any previously active player
        for pid, last_ptr in self.last_pointers.items():
            if pid not in current_pointers:
                time_since_seen = now - self.last_seen_time.get(pid, 0.0)
                if time_since_seen > self.hand_lost_timeout_s:
                    current_pointers[pid] = Pointer(
                        player_id=pid,
                        position=last_ptr.position,
                        state=TrackingState.LOST,
                        timestamp=now,
                        confidence=0.0,
                    )
                else:
                    current_pointers[pid] = last_ptr

        return InputSnapshot(
            timestamp=now,
            pointers=current_pointers,
            camera_preview=preview_surf,
            status_label=status_label,
        )

    def close(self) -> None:
        self.worker.stop()
