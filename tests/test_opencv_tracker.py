from __future__ import annotations

import numpy as np

from fingermaze.input.tracking.opencv_tracker import OpenCVHandTracker


def test_opencv_hand_tracker_empty_frame() -> None:
    tracker = OpenCVHandTracker()
    black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = tracker.process_frame(black_frame)
    assert len(detections) == 0
    tracker.close()


def test_opencv_hand_tracker_detects_tip() -> None:
    tracker = OpenCVHandTracker()
    # Create synthetic frame with a skin-colored patch (YCrCb ~ [120, 150, 100])
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Fill a polygon representing an upward hand
    import cv2

    ycrcb_skin = np.array([120, 150, 100], dtype=np.uint8)
    bgr_skin = cv2.cvtColor(np.uint8([[ycrcb_skin]]), cv2.COLOR_YCrCb2BGR)[0][0]

    cv2.circle(frame, (320, 200), 50, (int(bgr_skin[0]), int(bgr_skin[1]), int(bgr_skin[2])), -1)

    detections = tracker.process_frame(frame)
    assert len(detections) == 1
    tip = detections[0].index_finger_tip
    assert 0.0 <= tip.x <= 1.0
    assert 0.0 <= tip.y <= 1.0
    tracker.close()
