import numpy as np
import pytest

from agents.base import SearchStats
from agents.random_agent import RandomAgent
from core.board import Board
from core.rules import GameConfig


def state(b: Board) -> tuple[bytes, list[int], int, tuple[int, ...], int, list[int]]:
    return (
        b.cells.tobytes(),
        b.cells_list[:],
        b.to_move,
        b.move_history,
        b.hash,
        list(b.empty_cells),
    )


def test_random_agent_returns_legal_move_and_leaves_board_unchanged() -> None:
    rng = np.random.default_rng(0)
    agent = RandomAgent(seed=1)
    for _ in range(200):
        b = Board(GameConfig(5, 4))
        for _ in range(int(rng.integers(0, 12))):
            if not b.is_terminal:
                b.make(int(rng.choice(b.legal_moves())))
        if b.is_terminal:
            continue
        before = state(b)
        move = agent.select_move(b, 0.1)
        assert state(b) == before
        assert move in b.legal_moves() and isinstance(move, int)


def test_random_agent_seeded_and_budget_is_per_call() -> None:
    b = Board(GameConfig(7, 4))
    a1, a2 = RandomAgent(seed=7), RandomAgent(seed=7)
    s1 = [a1.select_move(b, t) for t in (0.01, 1.0, 5.0, 0.0)]
    s2 = [a2.select_move(b, 1.0) for _ in range(4)]
    assert s1 == s2


def test_random_agent_stats() -> None:
    agent = RandomAgent()
    agent.select_move(Board(GameConfig(3, 3)), 1.0)
    st = agent.last_stats()
    assert isinstance(st, SearchStats)
    assert st.nodes == 0 and st.time_s >= 0.0 and st.depth_reached is None
    assert st.extra == {}


def test_random_agent_rejects_finished_game() -> None:
    b = Board(GameConfig(3, 3))
    for m in (0, 3, 1, 4, 2):
        b.make(m)
    with pytest.raises(ValueError):
        RandomAgent().select_move(b, 1.0)
