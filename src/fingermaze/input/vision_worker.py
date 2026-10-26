"""Background thread worker for camera frame capture and hand inference."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

import cv2
import pygame

from fingermaze.core.ports import CameraSource
from fingermaze.core.types import PlayerId
from fingermaze.input.mailbox import LatestValueMailbox
from fingermaze.input.tracking.mediapipe_tracker import MediaPipeHandTracker

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RawPointerSample:
    player_id: PlayerId
    norm_x: float
    norm_y: float
    timestamp: float
    confidence: float


@dataclass(frozen=True)
class RawDetectionSnapshot:
    timestamp: float
    samples: list[RawPointerSample]
    has_hand: bool
    preview_surface: Any = None


class VisionWorker:
    """Manages the background capture and inference loop."""

    def __init__(
        self,
        camera: CameraSource,
        tracker: MediaPipeHandTracker,
        mailbox: LatestValueMailbox[RawDetectionSnapshot],
    ) -> None:
        self.camera = camera
        self.tracker = tracker
        self.mailbox = mailbox

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.fps_counter: int = 0
        self.tracking_rate_hz: float = 0.0

    def start(self) -> None:
        """Start the background worker thread."""
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self.camera.open()
        self._thread = threading.Thread(target=self._run_loop, name="VisionWorker", daemon=True)
        self._thread.start()
        logger.info("VisionWorker thread started.")

    def stop(self) -> None:
        """Signal the worker to stop and wait for it to join."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

        self.camera.close()
        self.tracker.close()
        logger.info("VisionWorker stopped.")

    def _run_loop(self) -> None:
        last_stat_time = time.monotonic()
        frames_processed = 0

        while not self._stop_event.is_set():
            frame = self.camera.read()
            now = time.monotonic()

            if frame is None:
                # Small yield if camera has no frame ready yet
                time.sleep(0.005)
                continue

            try:
                detections = self.tracker.process_frame(frame)
            except Exception as exc:
                logger.error(f"Inference error in VisionWorker: {exc}")
                continue

            samples: list[RawPointerSample] = []
            if detections:
                # Sort hands by X position for player assignment (FR-03)
                # Left half of mirrored camera = Player 1, Right half = Player 2
                sorted_detections = sorted(detections, key=lambda d: d.index_finger_tip.x)

                for idx, det in enumerate(sorted_detections):
                    player_id = PlayerId.PLAYER_1 if idx == 0 else PlayerId.PLAYER_2
                    tip = det.index_finger_tip
                    samples.append(
                        RawPointerSample(
                            player_id=player_id,
                            norm_x=tip.x,
                            norm_y=tip.y,
                            timestamp=now,
                            confidence=det.confidence,
                        )
                    )

            # Generate downscaled preview surface with tracking landmarks
            preview_surf = None
            try:
                pv_w, pv_h = 200, 150
                small = cv2.resize(frame, (pv_w, pv_h))
                for s in samples:
                    fx = max(0, min(pv_w - 1, int(s.norm_x * pv_w)))
                    fy = max(0, min(pv_h - 1, int(s.norm_y * pv_h)))
                    cv2.circle(small, (fx, fy), 5, (0, 255, 0), -1)
                    cv2.circle(small, (fx, fy), 8, (255, 255, 255), 1)

                small_rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                preview_surf = pygame.image.frombuffer(small_rgb.tobytes(), (pv_w, pv_h), "RGB")
            except Exception as exc:
                logger.debug(f"Preview creation error: {exc}")

            snapshot = RawDetectionSnapshot(
                timestamp=now,
                samples=samples,
                has_hand=bool(samples),
                preview_surface=preview_surf,
            )
            self.mailbox.publish(snapshot)

            # Benchmark stats
            frames_processed += 1
            if now - last_stat_time >= 1.0:
                self.tracking_rate_hz = frames_processed / (now - last_stat_time)
                frames_processed = 0
                last_stat_time = now
