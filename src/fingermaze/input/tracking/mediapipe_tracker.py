"""MediaPipe Hand Landmarker adapter."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp

from fingermaze.core.ports import Frame
from fingermaze.core.types import HandLandmark

INDEX_FINGER_TIP = 8


@dataclass(frozen=True)
class HandDetection:
    landmarks: list[HandLandmark]
    index_finger_tip: HandLandmark
    confidence: float


class MediaPipeHandTracker:
    """Detects hand landmarks using MediaPipe Hand Landmarker (Tasks API)."""

    def __init__(
        self,
        model_path: str | Path = "models/hand_landmarker.task",
        num_hands: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        self.model_path = Path(model_path).resolve()
        if not self.model_path.exists():
            raise FileNotFoundError(f"MediaPipe model file not found at: {self.model_path}")

        self.num_hands = num_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence

        self.is_pointing: bool = True
        self.status_message: str = "BUSCANDO DEDO"
        self.last_landmarks_normalized: list[tuple[float, float]] | None = None

        BaseOptions = mp.tasks.BaseOptions
        HandLandmarker = mp.tasks.vision.HandLandmarker
        HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(self.model_path)),
            running_mode=VisionRunningMode.VIDEO,
            num_hands=self.num_hands,
            min_hand_detection_confidence=self.min_detection_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
        )
        self.landmarker = HandLandmarker.create_from_options(options)
        self.start_time = time.monotonic()

    def process_frame(self, frame: Frame) -> list[HandDetection]:
        """Process a BGR frame and extract hand detections."""
        # OpenCV frames are BGR; convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Monotonic timestamp in milliseconds for video mode
        timestamp_ms = int((time.monotonic() - self.start_time) * 1000)

        result: Any = self.landmarker.detect_for_video(mp_image, timestamp_ms)
        detections: list[HandDetection] = []

        if not result.hand_landmarks:
            self.last_landmarks_normalized = None
            self.status_message = "MUESTRA TU MANO"
            return detections

        for hand_lms in result.hand_landmarks:
            landmarks: list[HandLandmark] = []
            for lm in hand_lms:
                landmarks.append(
                    HandLandmark(
                        x=float(lm.x),
                        y=float(lm.y),
                        z=float(lm.z),
                        visibility=float(getattr(lm, "visibility", 1.0) or 1.0),
                    )
                )

            if len(landmarks) > INDEX_FINGER_TIP:
                # Gesture classification: Pointing index vs Open Hand
                w_x, w_y = landmarks[0].x, landmarks[0].y
                dist_idx = math.hypot(landmarks[8].x - w_x, landmarks[8].y - w_y)
                dist_idx_pip = math.hypot(landmarks[6].x - w_x, landmarks[6].y - w_y)
                idx_extended = dist_idx > (dist_idx_pip * 1.15)

                dist_mid = math.hypot(landmarks[12].x - w_x, landmarks[12].y - w_y)
                dist_mid_pip = math.hypot(landmarks[10].x - w_x, landmarks[10].y - w_y)
                mid_folded = dist_mid < (dist_mid_pip * 1.15)

                dist_rng = math.hypot(landmarks[16].x - w_x, landmarks[16].y - w_y)
                dist_rng_pip = math.hypot(landmarks[14].x - w_x, landmarks[14].y - w_y)
                rng_folded = dist_rng < (dist_rng_pip * 1.15)

                dist_pnk = math.hypot(landmarks[20].x - w_x, landmarks[20].y - w_y)
                dist_pnk_pip = math.hypot(landmarks[18].x - w_x, landmarks[18].y - w_y)
                pnk_folded = dist_pnk < (dist_pnk_pip * 1.15)

                is_open = not mid_folded and not rng_folded and not pnk_folded
                is_pointing = idx_extended and (mid_folded or rng_folded)

                if is_open:
                    self.is_pointing = False
                    self.status_message = "CIERRA EL PUÑO Y APUNTA CON 1 DEDO"
                    gest_conf = 0.3
                elif is_pointing:
                    self.is_pointing = True
                    self.status_message = "DEDO ÍNDICE (OK)"
                    gest_conf = 1.0
                else:
                    self.is_pointing = True
                    self.status_message = "DEDO DETECTADO (OK)"
                    gest_conf = 0.9

                self.last_landmarks_normalized = [(lm.x, lm.y) for lm in landmarks]
                tip = landmarks[INDEX_FINGER_TIP]
                detections.append(
                    HandDetection(
                        landmarks=landmarks,
                        index_finger_tip=tip,
                        confidence=gest_conf,
                    )
                )

        return detections

    def close(self) -> None:
        if hasattr(self, "landmarker") and self.landmarker is not None:
            self.landmarker.close()
