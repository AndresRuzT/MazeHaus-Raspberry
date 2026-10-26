"""CLI entry point for FingerMaze."""

from __future__ import annotations

import argparse

from fingermaze.app import run_app
from fingermaze.config.settings import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="FingerMaze - Computer Vision Maze Game")
    parser.add_argument("--mouse", action="store_true", help="Force mouse input instead of camera")
    parser.add_argument("--config", type=str, default=None, help="Path to config.toml")
    parser.add_argument("--cols", type=int, default=None, help="Number of maze columns")
    parser.add_argument("--rows", type=int, default=None, help="Number of maze rows")
    parser.add_argument("--fullscreen", action="store_true", help="Run in fullscreen mode")

    args = parser.parse_args()

    config = load_config(args.config)
    if args.mouse:
        config.use_mouse_fallback = True
    if args.cols is not None:
        config.maze.cols = args.cols
    if args.rows is not None:
        config.maze.rows = args.rows
    if args.fullscreen:
        config.display.fullscreen = True

    run_app(config)


if __name__ == "__main__":
    main()
