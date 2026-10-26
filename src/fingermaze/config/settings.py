"""Configuration models and loading via TOML and Pydantic."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, Field


class DisplayConfig(BaseModel):
    width: int = Field(default=1280, ge=640, le=3840)
    height: int = Field(default=720, ge=480, le=2160)
    fullscreen: bool = False
    target_fps: int = Field(default=30, ge=15, le=120)


class CameraConfig(BaseModel):
    device_index: int = Field(default=0, ge=0)
    width: int = Field(default=640, ge=320, le=1920)
    height: int = Field(default=480, ge=240, le=1080)
    fps: int = Field(default=30, ge=15, le=60)
    mirror: bool = True


class TrackingConfig(BaseModel):
    model_path: str = "models/hand_landmarker.task"
    num_hands: int = Field(default=1, ge=1, le=2)
    min_detection_confidence: float = Field(default=0.5, ge=0.1, le=1.0)
    min_tracking_confidence: float = Field(default=0.5, ge=0.1, le=1.0)
    hand_lost_timeout_s: float = Field(default=1.0, ge=0.2, le=5.0)
    filter_min_cutoff: float = Field(default=1.0, ge=0.01, le=10.0)
    filter_beta: float = Field(default=0.05, ge=0.001, le=1.0)


class MazeDifficultyConfig(BaseModel):
    cols: int = Field(default=10, ge=4, le=64)
    rows: int = Field(default=7, ge=4, le=48)
    wall_thickness: int = Field(default=6, ge=2, le=30)
    cursor_radius: int = Field(default=14, ge=4, le=30)
    wall_penalty_seconds: float = Field(default=2.5, ge=0.0, le=15.0)


class GameConfig(BaseModel):
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    camera: CameraConfig = Field(default_factory=CameraConfig)
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    maze: MazeDifficultyConfig = Field(default_factory=MazeDifficultyConfig)
    use_mouse_fallback: bool = False


def load_config(config_path: Path | str | None = None) -> GameConfig:
    """Load configuration from a TOML file or return defaults."""
    if config_path is None:
        default_file = Path("config.toml")
        if default_file.exists():
            config_path = default_file

    if config_path is not None:
        p = Path(config_path)
        if p.exists():
            with p.open("rb") as f:
                data = tomllib.load(f)
            return GameConfig.model_validate(data)

    return GameConfig()
