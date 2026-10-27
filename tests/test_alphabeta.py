from dataclasses import replace
from time import perf_counter

import numpy as np
import pytest

from agents.alphabeta import WIN_SCORE, ABConfig, AlphaBetaAgent
from agents.backtracking import BacktrackingAgent
from agents.evaluation import EvalWeights
from agents.presets import (
    AB_FULL,
    AB_ORDER,
    AB_ORDER_ID,
    AB_ORDER_ID_TT,
    AB_PLAIN,
    AB_PRESETS,
    AGENT_REGISTRY,
)
from core.board import Board
from core.rules import GameConfig, X
from tests.positions import (
    ALL_POSITIONS,
    C74,
    MUST_BLOCK_74,
    MUST_BLOCK_95,
    QUIET_74,
    QUIET_95,
    WIN_IN_1_74,
    WIN_IN_3_A_74,
    WIN_IN_3_A_95,
    WIN_IN_3_B_74,
    WIN_IN_3_B_95,
    Pos,
    midgame_positions_95,
)
from tests.test_agents import state

FULL_NO_RADIUS = replace(AB_FULL, candidate_radius=None)
ALL_NO_RADIUS = [AB_PLAIN, AB_ORDER, AB_ORDER_ID, AB_ORDER_ID_TT, FULL_NO_RADIUS]


def score_of(cfg: ABConfig, b: Board, budget: float = 600.0) -> int:
    agent = AlphaBetaAgent(cfg)
    agent.select_move(b, budget)
    assert agent.last_stats().extra["timed_out"] == 0.0
    return int(agent.last_stats().extra["score"])


def depth_for(pos: Pos) -> int:
    return 4 if pos.cfg.n == 7 else 3


@pytest.mark.parametrize("pos", ALL_POSITIONS, ids=lambda p: p.name)
@pytest.mark.slow
def test_pruning_and_enhancements_do_not_change_the_minimax_value(pos: Pos) -> None:
    d = depth_for(pos)
    values = {
        i: score_of(replace(c, max_depth=d), pos.board())
        for i, c in enumerate(ALL_NO_RADIUS)
    }
    assert len(set(values.values())) == 1, values


def test_value_equality_on_9x9_midgames() -> None:
    for b in midgame_positions_95():
        vals = {score_of(replace(c, max_depth=3), b) for c in ALL_NO_RADIUS}
        assert len(vals) == 1


def test_plain_value_matches_backtracking_on_4x4() -> None:
    rng = np.random.default_rng(11)
    for k in (3, 4):
        cfg = GameConfig(4, k)
        zero = EvalWeights((0,) * (k + 1), 0, 0, 0)
        for plies in (0, 2, 3, 4, 5, 6):
            b = Board(cfg)
            for _ in range(plies):
                if b.is_terminal:
                    break
                b.make(int(rng.choice(b.legal_moves())))
            if b.is_terminal:
                continue
            for depth in (2, 3, 4):
                bt = BacktrackingAgent(max_depth=depth)
                bt.select_move(b, 600.0)
                expected = int(bt.last_stats().extra["score"])
                for c in (AB_PLAIN, FULL_NO_RADIUS):
                    ab = AlphaBetaAgent(replace(c, max_depth=depth), weights=zero)
                    ab.select_move(b, 600.0)
                    got = int(ab.last_stats().extra["score"])
                    assert got == expected, (k, plies, depth, c)


@pytest.mark.parametrize(
    "pos",
    [WIN_IN_1_74, MUST_BLOCK_74, MUST_BLOCK_95, WIN_IN_3_A_74, WIN_IN_3_B_74,
     WIN_IN_3_A_95, WIN_IN_3_B_95],
    ids=lambda p: p.name,
)
def test_finds_tactics(pos: Pos) -> None:
    for cfg in (AB_ORDER_ID_TT, AB_FULL, AB_ORDER):
        b = pos.board()
        agent = AlphaBetaAgent(replace(cfg, max_depth=4))
        move = agent.select_move(b, 600.0)
        assert move in pos.best, (cfg, move)
        if pos.win_ply is not None:
            assert agent.last_stats().extra["score"] == WIN_SCORE - pos.win_ply


def test_plain_alpha_beta_also_finds_forced_win_in_3() -> None:
    b = WIN_IN_3_A_74.board()
    agent = AlphaBetaAgent(replace(AB_PLAIN, max_depth=3))
    assert agent.select_move(b, 600.0) in WIN_IN_3_A_74.best
    assert agent.last_stats().extra["score"] == WIN_SCORE - 3


def test_answers_opponent_open_three_on_an_end() -> None:
    # O has an open three (k-1 on 7x7 k=4): X cannot stop both ends, so it must
    # at least take one of them rather than play elsewhere.
    b = Board.from_string(
        ". . . . . . .\n. . . . . . .\n. . . . . . .\n. . O O O . .\n"
        ". . . . . . .\nX . . . . . .\n. . X . . . X",
        C74,
        X,
    )
    move = AlphaBetaAgent(replace(AB_FULL, max_depth=4)).select_move(b, 600.0)
    assert move in {3 * 7 + 1, 3 * 7 + 5}


def test_iterative_deepening_respects_budget() -> None:
    cfg = replace(AB_FULL, max_depth=64)
    for b in [QUIET_95.board(), QUIET_74.board(), midgame_positions_95()[0]]:
        for budget in (0.3, 1.0):
            agent = AlphaBetaAgent(cfg)
            t0 = perf_counter()
            move = agent.select_move(b, budget)
            elapsed = perf_counter() - t0
            assert elapsed <= budget * 1.1, (elapsed, budget)
            assert move in b.legal_moves()
            st = agent.last_stats()
            assert st.depth_reached is not None and st.depth_reached >= 1


def test_non_id_timeout_returns_legal_move() -> None:
    b = QUIET_95.board()
    agent = AlphaBetaAgent(replace(AB_PLAIN, max_depth=8))
    t0 = perf_counter()
    move = agent.select_move(b, 0.2)
    assert perf_counter() - t0 <= 0.22
    assert move in b.legal_moves() and agent.last_stats().extra["timed_out"] == 1.0


@pytest.mark.parametrize("name", list(AB_PRESETS))
def test_board_unchanged_after_select_move(name: str) -> None:
    for pos in (QUIET_74, QUIET_95, MUST_BLOCK_74, WIN_IN_3_A_95):
        b = pos.board()
        before = state(b)
        cands_before = sorted(b.candidate_moves(2))
        for budget in (0.05, 5.0):
            agent = AlphaBetaAgent(replace(AB_PRESETS[name], max_depth=3))
            agent.select_move(b, budget)
            assert state(b) == before
            assert sorted(b.candidate_moves(2)) == cands_before


def test_stats_and_pv() -> None:
    b = QUIET_74.board()
    agent = AlphaBetaAgent(replace(AB_FULL, max_depth=4))
    move = agent.select_move(b, 600.0)
    st = agent.last_stats()
    assert st.nodes > 0 and st.depth_reached == 4 and st.time_s > 0
    assert {"tt_hits", "cutoffs", "ebf"} <= set(st.extra)
    assert st.extra["cutoffs"] > 0 and st.extra["ebf"] > 1
    pv = agent.last_pv()
    assert pv and pv[0] == move and len(pv) <= 4
    for m in pv:
        assert m in b.legal_moves()
        b.make(m)


def test_pruning_reduces_nodes_and_ordering_helps() -> None:
    b = QUIET_74.board()
    bt = BacktrackingAgent(max_depth=3)
    bt.select_move(b, 600.0)
    nodes = {}
    for name, cfg in (("plain", AB_PLAIN), ("order", AB_ORDER)):
        a = AlphaBetaAgent(replace(cfg, max_depth=3))
        a.select_move(b, 600.0)
        nodes[name] = a.last_stats().nodes
    assert nodes["plain"] < bt.last_stats().nodes
    assert nodes["order"] <= nodes["plain"]


def test_candidate_radius_restricts_moves() -> None:
    b = QUIET_95.board()
    near = set(b.candidate_moves(2))
    agent = AlphaBetaAgent(replace(AB_FULL, max_depth=3))
    assert agent.select_move(b, 600.0) in near


def test_empty_board_and_finished_game() -> None:
    agent = AlphaBetaAgent(replace(AB_FULL, max_depth=2))
    assert agent.select_move(Board(GameConfig(9, 5)), 5.0) in range(81)
    done = Board(GameConfig(3, 3))
    for m in (0, 3, 1, 4, 2):
        done.make(m)
    with pytest.raises(ValueError):
        agent.select_move(done, 1.0)


def test_exact_k_overline_gap_is_not_a_winning_cell() -> None:
    grid = (
        "O . . . . . O\n. . . . . . .\n. . . . . . .\nX X . X X . .\n"
        ". . . . . . .\n. . . . . . .\nO . . . . . O"
    )
    free = Board.from_string(grid, GameConfig(7, 4), X)
    exact = Board.from_string(grid, GameConfig(7, 4, exact_k=True), X)
    cfg = replace(AB_ORDER, max_depth=2)
    a_free, a_exact = AlphaBetaAgent(cfg), AlphaBetaAgent(cfg)
    assert a_free.select_move(free, 60.0) == 3 * 7 + 2
    assert a_free.last_stats().extra["score"] == WIN_SCORE - 1
    a_exact.select_move(exact, 60.0)
    assert a_exact.last_stats().extra["score"] != WIN_SCORE - 1


def test_registry_builds_agents_for_every_name() -> None:
    b = QUIET_74.board()
    for name, factory in AGENT_REGISTRY.items():
        agent = factory(0)
        assert agent.select_move(b, 0.3) in b.legal_moves(), name
        assert agent.last_stats().time_s >= 0
