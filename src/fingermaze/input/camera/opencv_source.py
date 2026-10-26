"""OpenCV video capture adapter."""

from __future__ import annotations

import cv2
import numpy as np

from fingermaze.core.ports import CameraSource, Frame


class OpenCVCameraSource(CameraSource):
    """Captures frames from a local USB/V4L2 camera using OpenCV."""

    def __init__(
        self,
        device_index: int = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        mirror: bool = True,
    ) -> None:
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps = fps
        self.mirror = mirror
        self.cap: cv2.VideoCapture | None = None

    def open(self) -> None:
        if self.cap is not None and self.cap.isOpened():
            return

        self.cap = cv2.VideoCapture(self.device_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Unable to open camera at index {self.device_index}")

        # Configure camera capture properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        # Minimize buffer size to 1 to reduce latency and drop stale frames
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def read(self) -> Frame | None:
        if self.cap is None or not self.cap.isOpened():
            return None

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None

        # Mirror horizontally so player movement matches screen intuitively
        if self.mirror:
            frame = np.asarray(cv2.flip(frame, 1), dtype=np.uint8)

        return frame

    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
