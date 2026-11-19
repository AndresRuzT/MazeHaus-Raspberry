# System Requirements and Specifications

This document outlines the hardware, operating system, and software dependencies required to run and develop MazeHaus.

## Hardware Requirements

MazeHaus is optimized for single-board computers like the Raspberry Pi 4 Model B, but it also runs smoothly on modern desktop and laptop computers.

* **Processor:** Raspberry Pi 4 Model B (4 GB or 8 GB RAM recommended, 2 GB supported) or any modern x86_64 / ARM64 CPU.
* **Camera:** Standard USB webcam supporting V4L2 or a Raspberry Pi Camera Module. A capture resolution of 640x480 at 30 FPS is ideal.
* **Display:** Monitor, TV, or kiosk screen running at 1280x720 or 1920x1080 resolution.
* **Environment:** Indoor ambient lighting. Avoid direct bright sunlight or strong backlighting behind the player.

## Operating System and System Libraries

* **Operating System:** Raspberry Pi OS 64-bit (Debian Bookworm or Bullseye), Ubuntu 22.04 or newer, or compatible Linux distributions. It can also be run on macOS and Windows for testing.
* **Python Runtime:** Python 3.11 or 3.12. MediaPipe native wheels are validated for these versions on ARM64 architectures.
* **System Packages:** Linux systems require basic multimedia and video capture libraries:
  * `v4l-utils`
  * `libgl1`
  * `libglib2.0-0`
  * `libasound2`

On Debian and Raspberry Pi OS, these can be installed with:
```bash
sudo apt update && sudo apt install -y v4l-utils libgl1 libglib2.0-0 libasound2
```

## Python Dependencies

All Python packages are listed in `pyproject.toml` and `requirements.txt`.

### Core Runtime Dependencies

* **pygame-ce (Community Edition):** Powers the 60 FPS game loop, HUD interface, particle effects, and sound triggers.
* **mediapipe:** Provides the primary neural network hand landmarker task, extracting 21 hand landmarks with CPU acceleration.
* **opencv-python-headless:** Handles webcam frame acquisition, horizontal mirroring, color space transforms, and the fallback morphological tracker.
* **numpy:** Powers coordinate transforms, array manipulation, and filter calculations.
* **pydantic:** Validates runtime configuration settings loaded from `config.toml`.

### Development and Testing Tools

* **pytest:** Automated test execution.
* **pytest-cov:** Test coverage reporting.
* **hypothesis:** Property-based testing for maze generation and math logic.
* **ruff:** Fast code formatting and linting.
* **mypy:** Strict static type analysis.

## Key Functional Requirements

* **Touchless Control:** Real-time index fingertip tracking with adaptive One Euro low-pass filtering to remove hand tremor.
* **Decoupled Architecture:** The vision thread runs asynchronously between 15 and 30 FPS, while the Pygame render thread stays fixed at 60 FPS using non-blocking mailbox updates.
* **Dual Tracking Pipeline:** Automatic use of Google MediaPipe when model weights exist, with seamless fallback to OpenCV skin and apex detection if the model file is not present.
* **Development Mode:** Instant fallback to mouse control using the `--mouse` command line flag for testing on machines without a camera.
* **Continuous Collision Detection:** High-speed movement across walls is caught using ray marching, eliminating tunneling effects.
* **Local Record Storage:** High scores and best times are saved locally to `data/records.json`.
* **Privacy and Security:** Video frames are processed in memory only. No frames or personal images are ever recorded, saved to disk, or sent across a network.
