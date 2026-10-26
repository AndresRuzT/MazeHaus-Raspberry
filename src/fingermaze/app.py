"""Composition root: wires adapters into the core application."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fingermaze.config.settings import GameConfig, load_config
from fingermaze.core.loop import GameLoop
from fingermaze.core.ports import InputProvider
from fingermaze.core.types import Viewport
from fingermaze.games.maze.scene import MazeScene
from fingermaze.input.camera.opencv_source import OpenCVCameraSource
from fingermaze.input.mailbox import LatestValueMailbox
from fingermaze.input.mapping import CoordinateMapper
from fingermaze.input.mouse_input import MouseInputProvider
from fingermaze.input.tracking.mediapipe_tracker import MediaPipeHandTracker
from fingermaze.input.tracking.opencv_tracker import OpenCVHandTracker
from fingermaze.input.vision_input import VisionInputProvider
from fingermaze.input.vision_worker import RawDetectionSnapshot, VisionWorker

logger = logging.getLogger(__name__)


def cpu_supports_aes() -> bool:
    """Check if host CPU supports hardware AES instructions required by generic MediaPipe wheels."""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("Features") or line.startswith("flags"):
                    return "aes" in line.lower()
    except Exception:
        pass
    import platform

    machine = platform.machine().lower()
    if "arm" in machine or "aarch64" in machine:
        return False
    return True


def create_input_provider(config: GameConfig) -> InputProvider:
    """Create either a vision-based or mouse-based input provider."""
    if config.use_mouse_fallback:
        logger.info("Using mouse input provider (fallback mode)")
        return MouseInputProvider()

    # Attempt to initialize OpenCV camera and MediaPipe tracker
    model_path = Path(config.tracking.model_path)
    if not model_path.exists():
        logger.warning(f"Model file {model_path} not found. Falling back to mouse input.")
        return MouseInputProvider()

    try:
        camera = OpenCVCameraSource(
            device_index=config.camera.device_index,
            width=config.camera.width,
            height=config.camera.height,
            fps=config.camera.fps,
            mirror=config.camera.mirror,
        )

        # Initialize Google MediaPipe Hand Landmarker (ARM-accelerated via XNNPACK in mediapipe 0.10.18)
        if model_path.exists():
            logger.info(
                "Initializing Google MediaPipe Hand Landmarker (XNNPACK CPU accelerated)..."
            )
            try:
                tracker: Any = MediaPipeHandTracker(
                    model_path=model_path,
                    num_hands=config.tracking.num_hands,
                    min_detection_confidence=config.tracking.min_detection_confidence,
                    min_tracking_confidence=config.tracking.min_tracking_confidence,
                )
            except Exception as mp_err:
                logger.warning(
                    f"MediaPipe initialization warning ({mp_err}). Falling back to native OpenCV tracker."
                )
                tracker = OpenCVHandTracker()
        else:
            logger.info("Model file not found. Using native OpenCV Tracker.")
            tracker = OpenCVHandTracker()

        mailbox: LatestValueMailbox[RawDetectionSnapshot] = LatestValueMailbox()
        worker = VisionWorker(camera=camera, tracker=tracker, mailbox=mailbox)
        worker.start()

        # Viewport maps directly to the dedicated maze arena (left of sidebar)
        sidebar_w = 245
        sidebar_x = config.display.width - sidebar_w - 12
        margin_x = 20
        margin_y = 20
        arena_w = sidebar_x - margin_x - 14
        arena_h = config.display.height - 2 * margin_y

        viewport = Viewport(x=margin_x, y=margin_y, width=arena_w, height=arena_h)
        mapper = CoordinateMapper(viewport=viewport)

        logger.info("Vision pipeline successfully initialized and started!")
        return VisionInputProvider(
            worker=worker,
            mailbox=mailbox,
            mapper=mapper,
            hand_lost_timeout_s=config.tracking.hand_lost_timeout_s,
            filter_min_cutoff=config.tracking.filter_min_cutoff,
            filter_beta=config.tracking.filter_beta,
        )
    except Exception as exc:
        logger.warning(
            f"Failed to initialize vision pipeline ({exc}). Falling back to mouse input."
        )
        return MouseInputProvider()


def run_app(config: GameConfig | None = None) -> None:
    """Run the FingerMaze game application."""
    if config is None:
        config = load_config()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.info("Starting FingerMaze application...")

    input_provider = create_input_provider(config)
    scene = MazeScene(config=config, input_provider=input_provider)
    loop = GameLoop(config=config, input_provider=input_provider, initial_scene=scene)

    loop.run()
