from __future__ import annotations

import numpy as np

from fingermaze.input.tracking.opencv_tracker import OpenCVHandTracker


def test_opencv_hand_tracker_empty_frame() -> None:
    tracker = OpenCVHandTracker()
    black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = tracker.process_frame(black_frame)
    assert len(detections) == 0
    tracker.close()


def test_opencv_hand_tracker_ignores_face_in_upper_frame() -> None:
    tracker = OpenCVHandTracker()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    import cv2

    ycrcb_skin = np.array([120, 150, 100], dtype=np.uint8)
    bgr_skin = cv2.cvtColor(np.uint8([[ycrcb_skin]]), cv2.COLOR_YCrCb2BGR)[0][0]

    # Draw skin patch located exclusively in the upper 30% of the frame (face/forehead)
    cv2.circle(frame, (320, 80), 40, (int(bgr_skin[0]), int(bgr_skin[1]), int(bgr_skin[2])), -1)

    detections = tracker.process_frame(frame)
    # Must be suppressed by spatial hand prior
    assert len(detections) == 0
    tracker.close()


def test_opencv_hand_tracker_detects_tip() -> None:
    tracker = OpenCVHandTracker()
    # Create synthetic frame with a skin-colored patch reaching lower half
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    import cv2

    ycrcb_skin = np.array([120, 150, 100], dtype=np.uint8)
    bgr_skin = cv2.cvtColor(np.uint8([[ycrcb_skin]]), cv2.COLOR_YCrCb2BGR)[0][0]

    # Draw an arm/finger extending into the lower half
    cv2.rectangle(
        frame, (300, 180), (340, 400), (int(bgr_skin[0]), int(bgr_skin[1]), int(bgr_skin[2])), -1
    )

    detections = tracker.process_frame(frame)
    assert len(detections) == 1
    assert tracker.is_pointing is True
    tip = detections[0].index_finger_tip
    assert 0.0 <= tip.x <= 1.0
    assert 0.0 <= tip.y <= 1.0

    # Process next frame to test temporal tracking and smoothing
    frame2 = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(
        frame2, (305, 175), (345, 400), (int(bgr_skin[0]), int(bgr_skin[1]), int(bgr_skin[2])), -1
    )
    detections2 = tracker.process_frame(frame2)
    assert len(detections2) == 1
    tracker.close()


def test_opencv_hand_tracker_open_hand_detection() -> None:
    tracker = OpenCVHandTracker()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    import cv2

    ycrcb_skin = np.array([120, 150, 100], dtype=np.uint8)
    bgr_skin = cv2.cvtColor(np.uint8([[ycrcb_skin]]), cv2.COLOR_YCrCb2BGR)[0][0]

    # Draw a wide block (apex_width > 50) simulating an open palm / spread fingers
    cv2.rectangle(
        frame, (200, 150), (450, 420), (int(bgr_skin[0]), int(bgr_skin[1]), int(bgr_skin[2])), -1
    )

    detections = tracker.process_frame(frame)
    assert len(detections) == 1
    # Wide apex detected as open hand, not pointing finger
    assert tracker.is_pointing is False
    assert detections[0].confidence < 0.5
    assert "APUNTA" in tracker.status_message
    tracker.close()
