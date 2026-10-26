from __future__ import annotations

from fingermaze.config.settings import GameConfig, load_config


def test_default_config_valid() -> None:
    config = GameConfig()
    assert config.display.width >= 640
    assert config.display.height >= 480
    assert config.maze.cols > 0
    assert config.maze.rows > 0
    assert config.maze.wall_penalty_seconds >= 0.0


def test_load_config_from_toml() -> None:
    config = load_config("config.toml")
    assert isinstance(config, GameConfig)
    assert config.maze.wall_thickness >= 2
