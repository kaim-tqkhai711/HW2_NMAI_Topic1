from dataclasses import replace

import numpy as np
import pytest

from agents.hybrid import HybridConfig, HybridMCTSAgent
from agents.mcts import MCTSAgent, Node
from agents.presets import AGENT_REGISTRY, HYBRID_PRESETS, MCTS_AB, MCTS_EVAL
from core.board import Board
from core.rules import GameConfig, O
from tests.positions import (
    MUST_BLOCK_74,
    MUST_BLOCK_95,
    QUIET_74,
    QUIET_95,
    WIN_IN_1_74,
    WIN_IN_1_95,
    WIN_IN_3_A_74,
    WIN_IN_3_A_95,
    WIN_IN_3_B_74,
    WIN_IN_3_B_95,
    Pos,
)
from tests.test_agents import state
from tests.test_mcts import mirror

HYBRIDS = list(HYBRID_PRESETS.values())
IDS = list(HYBRID_PRESETS)


def pick(cfg: HybridConfig, b: Board, iters: int, seed: int = 0) -> tuple[int, HybridMCTSAgent]:
    agent = HybridMCTSAgent(replace(cfg, max_iterations=iters, seed=seed))
    return agent.select_move(b, 600.0), agent


@pytest.mark.parametrize("cfg", HYBRIDS, ids=IDS)
@pytest.mark.parametrize("pos", [WIN_IN_1_74, WIN_IN_1_95], ids=lambda p: p.name)
def test_finds_win_in_1_for_both_colours(cfg: HybridConfig, pos: Pos) -> None:
    for b in (pos.board(), mirror(pos)):
        move, agent = pick(cfg, b, 600)
        assert move in pos.best
        q = agent.root_value_map().ravel()
        assert q[move] == 1.0


@pytest.mark.parametrize("cfg", HYBRIDS, ids=IDS)
@pytest.mark.parametrize("pos", [MUST_BLOCK_74, MUST_BLOCK_95], ids=lambda p: p.name)
def test_blocks_immediate_loss(cfg: HybridConfig, pos: Pos) -> None:
    ok = sum(pick(cfg, pos.board(), 800, seed=s)[0] in pos.best for s in range(5))
    assert ok == 5


@pytest.mark.parametrize(
    "pos", [WIN_IN_3_A_74, WIN_IN_3_B_74, WIN_IN_3_A_95, WIN_IN_3_B_95], ids=lambda p: p.name
)
def test_mcts_ab_finds_forced_win_in_3(pos: Pos) -> None:
    for seed in range(3):
        move, agent = pick(MCTS_AB, pos.board(), 800, seed=seed)
        assert move in pos.best
        assert agent.root_value_map().ravel()[move] == 1.0


def test_leaf_values_are_exact_for_proven_results_and_bounded_otherwise() -> None:
    b = MUST_BLOCK_74.board()
    b.make(0)  # X ignores the threat; O to move has an immediate win
    for cfg in HYBRIDS:
        agent = HybridMCTSAgent(cfg)
        agent._tb, agent._sb = b.copy(track_candidates=True), b.copy()
        leaf = Node(0, None, -b.to_move, False)  # mover into the leaf is X
        r = agent._evaluate_leaf(leaf, [])
        assert 0.0 <= r <= 1.0
        if cfg.leaf == "ab":
            assert r == 0.0  # proven loss for the mover, exact
        else:
            assert r < 0.5  # static evaluation also sees O far ahead
    q = QUIET_74.board()
    for cfg in HYBRIDS:
        agent = HybridMCTSAgent(cfg)
        agent._tb, agent._sb = q.copy(track_candidates=True), q.copy()
        r = agent._evaluate_leaf(Node(0, None, -q.to_move, False), [])
        assert 0.0 < r < 1.0


def test_terminal_leaf_is_exact() -> None:
    b = Board.from_string("X X X\nO O .\n. . .", GameConfig(3, 3), O)
    agent = HybridMCTSAgent(HybridConfig(leaf="eval"))
    agent._tb, agent._sb = b.copy(track_candidates=True), b.copy()
    assert agent._evaluate_leaf(Node(0, None, 1, True), []) == 1.0
    assert agent._evaluate_leaf(Node(0, None, -1, True), []) == 0.0


@pytest.mark.parametrize("cfg", HYBRIDS, ids=IDS)
def test_deterministic_and_board_unchanged(cfg: HybridConfig) -> None:
    b = QUIET_74.board()
    before = state(b)
    a1, a2 = (HybridMCTSAgent(replace(cfg, max_iterations=150, seed=4)) for _ in range(2))
    assert a1.select_move(b, 600.0) == a2.select_move(b, 600.0)
    assert np.array_equal(a1.root_visit_map(), a2.root_visit_map())
    assert state(b) == before
    a1.select_move(b, 0.05)
    assert state(b) == before


def test_hybrids_extend_not_replace_plain_mcts() -> None:
    assert issubclass(HybridMCTSAgent, MCTSAgent)
    for name in ("mcts_eval", "mcts_ab"):
        agent = AGENT_REGISTRY[name](1)
        assert agent.select_move(QUIET_95.board(), 0.2) in range(81)
    assert MCTS_EVAL.leaf == "eval" and MCTS_AB.leaf == "ab"
    assert (MCTS_AB.ab_depth, MCTS_AB.ab_radius) == (2, 1)


def test_scale_changes_leaf_value() -> None:
    q = QUIET_74.board()
    vals = []
    for scale in (10.0, 1e6):
        agent = HybridMCTSAgent(HybridConfig(leaf="eval", eval_scale=scale))
        agent._tb, agent._sb = q.copy(track_candidates=True), q.copy()
        vals.append(agent._evaluate_leaf(Node(0, None, -q.to_move, False), []))
    assert abs(vals[0] - 0.5) > abs(vals[1] - 0.5)
