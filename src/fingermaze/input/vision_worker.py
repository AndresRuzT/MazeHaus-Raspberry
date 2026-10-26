"""Background thread worker for camera frame capture and hand inference."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
import pygame

from fingermaze.core.ports import CameraSource
from fingermaze.core.types import PlayerId
from fingermaze.input.mailbox import LatestValueMailbox

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
    status_label: str = "BUSCANDO DEDO"


class VisionWorker:
    """Manages the background capture and inference loop."""

    def __init__(
        self,
        camera: CameraSource,
        tracker: Any,
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

            # Generate downscaled preview surface with tracking landmarks & skeleton
            preview_surf = None
            status_label = getattr(
                self.tracker, "status_message", "BUSCANDO DEDO" if not samples else "DEDO DETECTADO"
            )
            is_pointing = getattr(self.tracker, "is_pointing", True)
            try:
                pv_w, pv_h = 220, 165
                small = cv2.resize(frame, (pv_w, pv_h))

                # Draw ONNX 21 landmarks / hand skeleton if available
                last_lms = getattr(self.tracker, "last_landmarks_screen", None)
                if last_lms is not None:
                    scale_x = pv_w / frame.shape[1]
                    scale_y = pv_h / frame.shape[0]
                    # Draw connections
                    connections = [
                        (0, 1),
                        (1, 2),
                        (2, 3),
                        (3, 4),  # Thumb
                        (0, 5),
                        (5, 6),
                        (6, 7),
                        (7, 8),  # Index
                        (0, 9),
                        (9, 10),
                        (10, 11),
                        (11, 12),  # Middle
                        (0, 13),
                        (13, 14),
                        (14, 15),
                        (15, 16),  # Ring
                        (0, 17),
                        (17, 18),
                        (18, 19),
                        (19, 20),  # Pinky
                        (5, 9),
                        (9, 13),
                        (13, 17),  # Palm
                    ]
                    bone_color = (0, 230, 120) if is_pointing else (0, 140, 255)
                    for p1_idx, p2_idx in connections:
                        p1 = (
                            int(last_lms[p1_idx, 0] * scale_x),
                            int(last_lms[p1_idx, 1] * scale_y),
                        )
                        p2 = (
                            int(last_lms[p2_idx, 0] * scale_x),
                            int(last_lms[p2_idx, 1] * scale_y),
                        )
                        cv2.line(small, p1, p2, bone_color, 1)

                    # Draw keypoints
                    for i in range(21):
                        pt = (int(last_lms[i, 0] * scale_x), int(last_lms[i, 1] * scale_y))
                        cv2.circle(small, pt, 2, (255, 255, 255), -1)

                # Fallback: Draw contour if using OpenCVHandTracker
                last_cnt = getattr(self.tracker, "last_contour", None)
                if last_cnt is not None and last_lms is None:
                    scale_x = pv_w / frame.shape[1]
                    scale_y = pv_h / frame.shape[0]
                    scaled_cnt = np.array(last_cnt * [scale_x, scale_y], dtype=np.int32)
                    contour_color = (0, 230, 120) if is_pointing else (0, 140, 255)
                    cv2.drawContours(small, [scaled_cnt], -1, contour_color, 2)

                # Draw prominent yellow crosshair on index fingertip
                for s in samples:
                    fx = max(0, min(pv_w - 1, int(s.norm_x * pv_w)))
                    fy = max(0, min(pv_h - 1, int(s.norm_y * pv_h)))
                    cv2.circle(small, (fx, fy), 5, (0, 240, 255), -1)
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
                status_label=status_label,
            )
            self.mailbox.publish(snapshot)

            # Benchmark stats & 30 FPS rate limit to prevent CPU starvation
            frames_processed += 1
            if now - last_stat_time >= 1.0:
                self.tracking_rate_hz = frames_processed / (now - last_stat_time)
                frames_processed = 0

            # Yield CPU for Pygame rendering (30 FPS cap)
            elapsed = time.monotonic() - now
            sleep_time = 0.033 - elapsed
            if sleep_time > 0.002:
                time.sleep(sleep_time)
                last_stat_time = now
