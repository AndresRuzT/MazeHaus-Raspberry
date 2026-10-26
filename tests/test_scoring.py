from __future__ import annotations

from fingermaze.games.maze.domain.collision import MazeLayout
from fingermaze.games.maze.domain.generator import generate_maze
from fingermaze.games.maze.domain.scoring import GameStatus, PlayerGameState


def test_player_game_state_lifecycle() -> None:
    maze_def = generate_maze(cols=4, rows=4, seed=42)
    layout = MazeLayout(
        origin_x=0.0,
        origin_y=0.0,
        cell_width=50.0,
        cell_height=50.0,
        wall_thickness=2.0,
        cursor_radius=5.0,
    )
    state = PlayerGameState(maze_def=maze_def, layout=layout, wall_penalty_s=2.0)

    # Initial state is WAITING_FOR_TOUCH
    assert state.status == GameStatus.WAITING_FOR_TOUCH
    assert state.total_penalties == 0

    # Moving to start position activates tracing (PLAYING)
    start_pos = layout.cell_to_pixel_center(0, 0)
    state.update_position(start_pos, collides=False)
    assert state.status == GameStatus.PLAYING

    # Moving validly
    state.update_position((start_pos[0] + 5, start_pos[1] + 5), collides=False)
    assert state.status == GameStatus.PLAYING

    # Time progression
    state.tick_time(1.5)
    assert state.elapsed_time == 1.5

    # Collision penalty
    state.update_position((0.0, 0.0), collides=True)
    assert state.total_penalties == 1
    assert state.status == GameStatus.PENALTY_STUN
    assert state.total_score_time == 1.5 + (1 * 2.0)

    # Stun tick recovery transitions to WAITING_FOR_TOUCH
    state.tick_time(0.5)
    assert state.status == GameStatus.WAITING_FOR_TOUCH

    # Touching checkpoint resumes PLAYING
    cp_pos = state.current_checkpoint_pos()
    state.update_position(cp_pos, collides=False)
    assert state.status == GameStatus.PLAYING

    # Reaching exit
    exit_pos = layout.cell_to_pixel_center(*maze_def.exit_cell)
    state.update_position(exit_pos, collides=False)
    assert state.status == GameStatus.FINISHED
