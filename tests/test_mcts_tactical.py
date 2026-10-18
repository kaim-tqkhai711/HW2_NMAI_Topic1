from dataclasses import replace

import numpy as np
import pytest

from agents.hybrid import HybridMCTSAgent
from agents.mcts import MCTSAgent, MCTSConfig
from agents.presets import (
    AGENT_REGISTRY,
    HYBRID_TAC_PRESETS,
    MCTS_HEURISTIC,
    MCTS_HEURISTIC_TAC,
    MCTS_PRESETS,
    MCTS_RAVE,
    MCTS_RAVE_TAC,
    MCTS_TAC_PRESETS,
)
from core.board import Board
from core.rules import GameConfig, O, X
from tests.positions import (
    MUST_BLOCK_74,
    MUST_BLOCK_95,
    QUIET_74,
    WIN_IN_1_74,
    WIN_IN_1_95,
    Pos,
)
from tests.test_agents import state
from tests.test_mcts import mirror

ALL_TAC = {**MCTS_TAC_PRESETS, **HYBRID_TAC_PRESETS}


def make(cfg: MCTSConfig, sims: int, seed: int) -> MCTSAgent:
    cfg = replace(cfg, max_iterations=sims, seed=seed)
    return HybridMCTSAgent(cfg) if hasattr(cfg, "leaf") else MCTSAgent(cfg)  # type: ignore[arg-type]


def test_flag_defaults_off_and_non_tac_presets_unchanged() -> None:
    assert MCTSConfig().tactical_root_check is False
    assert all(not c.tactical_root_check for c in MCTS_PRESETS.values())
    assert MCTS_HEURISTIC_TAC == replace(MCTS_HEURISTIC, tactical_root_check=True)
    assert MCTS_RAVE_TAC == replace(MCTS_RAVE, tactical_root_check=True)
    for name in ("mcts_heuristic_tac", "mcts_rave_tac", "mcts_eval_tac", "mcts_ab_tac"):
        assert AGENT_REGISTRY[name](1).config.tactical_root_check  # type: ignore[attr-defined]


@pytest.mark.parametrize("name", list(ALL_TAC))
@pytest.mark.parametrize("pos", [MUST_BLOCK_74, MUST_BLOCK_95], ids=lambda p: p.name)
def test_block_found_in_20_of_20_seeds_with_500_simulations(name: str, pos: Pos) -> None:
    cfg = ALL_TAC[name]
    seeds = 5 if name == "MCTS_AB_TAC" else 20  # AB-leaf simulations are ~50x slower
    for seed in range(seeds):
        agent = make(cfg, 500, seed)
        assert agent.select_move(pos.board(), 600.0) in pos.best
        assert agent.last_stats().nodes <= 500


def test_tac_blocks_even_with_tiny_budget() -> None:
    for seed in range(20):
        assert make(MCTS_HEURISTIC_TAC, 64, seed).select_move(
            MUST_BLOCK_95.board(), 60.0) in MUST_BLOCK_95.best


@pytest.mark.parametrize("pos", [WIN_IN_1_74, WIN_IN_1_95], ids=lambda p: p.name)
def test_immediate_win_is_returned_without_search(pos: Pos) -> None:
    for b in (pos.board(), mirror(pos)):
        agent = make(MCTS_RAVE_TAC, 500, 0)
        assert agent.select_move(b, 60.0) in pos.best
        st = agent.last_stats()
        assert st.nodes == 0 and st.extra["tactical"] == 1.0
        assert agent.root_visit_map().sum() == 0


def test_root_is_restricted_to_blocking_moves() -> None:
    agent = make(MCTS_HEURISTIC_TAC, 300, 3)
    agent.select_move(MUST_BLOCK_74.board(), 60.0)
    assert agent._root is not None
    assert set(agent._root.children) == set(MUST_BLOCK_74.best)
    assert agent.last_stats().extra["tactical"] == 1.0
    assert agent.last_stats().nodes == 300


def test_two_threats_restrict_to_the_blocking_cells() -> None:
    # O threatens (3,0) and (3,4) in row 3 (open three, k=4): both are legal blocks.
    b = Board.from_string(
        ". . . . . . X\n. . . . . . .\n. . . . . . .\n. . O O O . .\n"
        ". . . . . . .\nX . . . . . .\n. . . . . . X",
        GameConfig(7, 4), X)
    agent = make(MCTS_HEURISTIC_TAC, 200, 0)
    move = agent.select_move(b, 60.0)
    assert agent._root is not None
    assert set(agent._root.children) <= {3 * 7 + 1, 3 * 7 + 5}
    assert move in {3 * 7 + 1, 3 * 7 + 5}


def test_quiet_positions_are_not_affected() -> None:
    b = QUIET_74.board()
    plain = make(MCTS_HEURISTIC, 400, 7)
    tac = make(MCTS_HEURISTIC_TAC, 400, 7)
    assert plain.select_move(b, 60.0) == tac.select_move(b, 60.0)
    assert np.array_equal(plain.root_visit_map(), tac.root_visit_map())
    assert tac.last_stats().extra["tactical"] == 0.0


def test_as_o_to_move_and_board_untouched() -> None:
    b = Board.from_string(
        "O . . . . . .\n. . . . . . .\n. . . . . . .\n. O X X X . .\n"
        ". . . . . . .\n. . O . . . .\n. . . . . . X",
        GameConfig(7, 4), O)
    before = state(b)
    for seed in range(10):
        assert make(MCTS_RAVE_TAC, 300, seed).select_move(b, 60.0) == 3 * 7 + 5
    assert state(b) == before


def test_exact_k_overline_gap_is_not_an_immediate_win() -> None:
    grid = ("O . . . . . O\n. . . . . . .\n. . . . . . .\nX X . X X . .\n"
            ". . . . . . .\n. . . . . . .\nO . . . . . O")
    free = Board.from_string(grid, GameConfig(7, 4), X)
    exact = Board.from_string(grid, GameConfig(7, 4, exact_k=True), X)
    a = make(MCTS_HEURISTIC_TAC, 100, 0)
    assert a.select_move(free, 60.0) == 3 * 7 + 2 and a.last_stats().nodes == 0
    b = make(MCTS_HEURISTIC_TAC, 100, 0)
    b.select_move(exact, 60.0)
    assert b.last_stats().nodes == 100
