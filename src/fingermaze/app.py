"""Composition root: wires adapters into the core application."""

from __future__ import annotations

import logging
from pathlib import Path

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
from fingermaze.input.vision_input import VisionInputProvider
from fingermaze.input.vision_worker import RawDetectionSnapshot, VisionWorker

logger = logging.getLogger(__name__)


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
        tracker = MediaPipeHandTracker(
            model_path=model_path,
            num_hands=config.tracking.num_hands,
            min_detection_confidence=config.tracking.min_detection_confidence,
            min_tracking_confidence=config.tracking.min_tracking_confidence,
        )
        mailbox: LatestValueMailbox[RawDetectionSnapshot] = LatestValueMailbox()
        worker = VisionWorker(camera=camera, tracker=tracker, mailbox=mailbox)
        worker.start()

        viewport = Viewport(x=0, y=0, width=config.display.width, height=config.display.height)
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
