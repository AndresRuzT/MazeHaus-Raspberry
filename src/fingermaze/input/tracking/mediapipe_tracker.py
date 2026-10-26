"""MediaPipe Hand Landmarker adapter."""

from __future__ import annotations

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
                tip = landmarks[INDEX_FINGER_TIP]
                detections.append(
                    HandDetection(
                        landmarks=landmarks,
                        index_finger_tip=tip,
                        confidence=1.0,
                    )
                )

        return detections

    def close(self) -> None:
        if hasattr(self, "landmarker") and self.landmarker is not None:
            self.landmarker.close()
