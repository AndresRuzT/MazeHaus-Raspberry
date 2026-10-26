from __future__ import annotations

import numpy as np
import pytest

from fingermaze.input.tracking.onnx_tracker import MPPalmDetector, ONNXHandTracker


def test_palm_detector_anchors() -> None:
    anchors = MPPalmDetector._generate_anchors()
    assert anchors.shape == (2016, 2)
    assert 0.0 <= anchors[0, 0] <= 1.0
    assert 0.0 <= anchors[0, 1] <= 1.0


def test_onnx_hand_tracker_empty_frame() -> None:
    try:
        tracker = ONNXHandTracker()
    except Exception as exc:
        pytest.skip(f"ONNX models not available for test: {exc}")

    black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = tracker.process_frame(black_frame)
    assert len(detections) == 0
    tracker.close()
