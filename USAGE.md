# User and Operator Guide

Welcome to MazeHaus. This guide explains how to set up the system, calibrate tracking, play the game, and adjust configuration settings. It is designed for both everyday players and operators setting up an interactive kiosk.

## Quick Start

You can run MazeHaus on a standard desktop computer or on a Raspberry Pi 4.

### 1. Installation

Clone the repository and set up a virtual environment using Python 3.11 or 3.12.

#### Option A: Using Standard Pip

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_model.py
```

#### Option B: Using uv

```bash
uv sync
uv run python scripts/download_model.py
```

### 2. Verify Your Setup

Run the built-in diagnostic script to confirm your camera, Python version, and model weights are ready:

```bash
python scripts/check_environment.py
```

## How to Run the Game

### Camera Mode (Standard)

Launch the game using your primary camera:

```bash
python -m fingermaze
```

### Fullscreen Kiosk Mode

Ideal for standalone exhibition screens, monitors, and TV displays:

```bash
python -m fingermaze --fullscreen
```

### Mouse Mode (Development and Testing)

If you are developing on a laptop or do not have a camera attached, use mouse mode:

```bash
python -m fingermaze --mouse
```

### Custom Grid Sizes

You can change the complexity of the maze directly from the command line:

```bash
python -m fingermaze --cols 14 --rows 9
```

## How to Play

### 1. Position Yourself
Stand or sit comfortably roughly one meter in front of the camera. Make sure your hand is visible in the camera frame. The live camera preview in the sidebar will show your hand and tracking status.

### 2. Center Calibration
When the game starts, a circular target appears in the middle of the arena. Hold your index finger steady inside the circle for about half a second. The game registers this spot as your natural resting position so you can play comfortably without straining your arm.

### 3. Countdown and Start
After calibration, a three-second countdown begins. Move your finger to the green START square at the maze entrance to start the timer.

### 4. Navigating Corridors
Guide the glowing pointer through the open paths toward the EXIT. Smooth hand movements work best. An adaptive filter cleans up natural hand tremor while preserving quick responses.

### 5. Checkpoints and Wall Penalties
As you advance through the maze, you will clear numbered checkpoints. If your pointer touches a wall, the game triggers a brief penalty stun, adds 2.5 seconds to your time, and places you back at the last checkpoint you cleared.

### 6. Finishing and High Scores
Reach the green EXIT cell to complete your run. Your total score includes your raw run time plus any wall collision penalties. If your score beats the historic best time, it is saved automatically to the local leaderboard.

## Controls and Shortcuts

* **Index Finger Movement:** Guides the game cursor in camera mode.
* **Mouse Movement:** Guides the cursor when running with the `--mouse` flag.
* **R or C:** Reset the current run and return to the calibration screen.
* **P:** Pause or resume gameplay.
* **ESC:** Exit the game safely and release all camera resources.

## Configuration Options

You can fine tune game behavior in `config.toml`:

```toml
[display]
width = 1280
height = 720
fullscreen = false
target_fps = 60

[camera]
device_index = 0
width = 640
height = 480
fps = 30
mirror = true

[maze]
cols = 10
rows = 7
wall_thickness = 6
cursor_radius = 14
wall_penalty_seconds = 2.5
```

* **device_index:** Change to 1 or 2 if you have multiple webcams connected.
* **cols and rows:** Adjust grid dimensions to make mazes easier or more challenging.
* **wall_penalty_seconds:** Adjust the time penalty applied when touching a wall.

## Helpful Troubleshooting Tips

* **Camera Not Detected:** Verify your camera index in `config.toml`. On Linux, ensure your user account has permission to read video devices by running `sudo usermod -aG video $USER` and then logging back in.
* **Lighting Conditions:** Stable room lighting works best. Avoid dark rooms or intense light sources directly behind you that wash out the camera sensor.
* **Tracking Fallback:** If the MediaPipe model file is not downloaded, MazeHaus automatically uses its built-in OpenCV skin tracking fallback so the game remains playable.
