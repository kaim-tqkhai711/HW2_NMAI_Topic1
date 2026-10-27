from dataclasses import replace

import numpy as np
import pytest

from agents.mcts import MCTSAgent, MCTSConfig
from agents.presets import (
    AGENT_REGISTRY,
    MCTS_HEURISTIC,
    MCTS_PRESETS,
    MCTS_RANDOM,
    MCTS_RAVE,
)
from core.board import Board
from core.rules import GameConfig, O, X
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


def run(cfg: MCTSConfig, b: Board, iters: int) -> MCTSAgent:
    agent = MCTSAgent(replace(cfg, max_iterations=iters))
    agent.select_move(b, 600.0)
    return agent


@pytest.mark.parametrize("cfg", list(MCTS_PRESETS.values()), ids=list(MCTS_PRESETS))
def test_deterministic_given_seed_and_iterations(cfg: MCTSConfig) -> None:
    for pos in (QUIET_74, QUIET_95):
        b = pos.board()
        a1 = MCTSAgent(replace(cfg, max_iterations=400, seed=5))
        a2 = MCTSAgent(replace(cfg, max_iterations=400, seed=5))
        assert a1.select_move(b, 600.0) == a2.select_move(b, 600.0)
        assert np.array_equal(a1.root_visit_map(), a2.root_visit_map())
        assert np.array_equal(
            a1.root_value_map(), a2.root_value_map(), equal_nan=True
        )
        a3 = MCTSAgent(replace(cfg, max_iterations=400, seed=6))
        a3.select_move(b, 600.0)
        assert not np.array_equal(a1.root_visit_map(), a3.root_visit_map())


def mirror(pos: Pos) -> Board:
    """Swap colours and add one far-away X stone so that O is to move."""
    flipped = pos.grid.translate(str.maketrans("XO", "OX"))
    rows = flipped.split("\n")
    last = rows[-1].split()
    for i in range(len(last) - 1, -1, -1):
        if last[i] == ".":
            last[i] = "X"
            break
    rows[-1] = " ".join(last)
    return Board.from_string("\n".join(rows), pos.cfg, O)


def test_mirror_is_a_valid_o_to_move_position() -> None:
    b = mirror(WIN_IN_1_74)
    assert b.to_move == O and b.n_empty == 49 - 7


@pytest.mark.parametrize(
    "cfg", list(MCTS_PRESETS.values()), ids=list(MCTS_PRESETS)
)
def test_sign_convention_winning_child_has_highest_q(cfg: MCTSConfig) -> None:
    for pos in (WIN_IN_1_74, WIN_IN_1_95):
        for b in (pos.board(), mirror(pos)):
            agent = run(cfg, b, 2000)
            vmap = agent.root_value_map().ravel()
            visits = agent.root_visit_map().ravel()
            valid = np.where(visits >= 10, vmap, -1.0)
            assert any(visits[w] > 0 for w in pos.best)
            for w in pos.best:
                if visits[w] > 0:
                    assert vmap[w] == 1.0 == valid.max()
            if cfg.rollout == "random":
                top = {int(i) for i in np.flatnonzero(valid == valid.max())}
                assert top <= set(pos.best), (pos.name, top)
                assert agent.select_move(b, 600.0) in pos.best


def block_rate(pos: Pos, iters: int, seeds: int) -> int:
    return sum(
        MCTSAgent(replace(MCTS_HEURISTIC, max_iterations=iters, seed=s)).select_move(
            pos.board(), 600.0
        )
        in pos.best
        for s in range(seeds)
    )


def test_heuristic_mcts_blocks_opponent_threat_7x7() -> None:
    assert block_rate(MUST_BLOCK_74, 3000, 20) >= 19


def test_heuristic_mcts_blocks_opponent_threat_9x9() -> None:
    # The wider 9x9 tree needs ~8000 simulations before the refutations of
    # non-blocking moves outweigh the averaging over their many replies.
    assert block_rate(MUST_BLOCK_95, 8000, 8) == 8


def test_heuristic_mcts_blocks_as_o_to_move() -> None:
    # X has three in row 3 with the left end blocked; O to move must take (3,5).
    b = Board.from_string(
        "O . . . . . .\n. . . . . . .\n. . . . . . .\n. O X X X . .\n"
        ". . . . . . .\n. . O . . . .\n. . . . . . X",
        GameConfig(7, 4),
        O,
    )
    ok = sum(
        MCTSAgent(replace(MCTS_HEURISTIC, max_iterations=3000, seed=s)).select_move(b, 60.0)
        == 3 * 7 + 5
        for s in range(10)
    )
    assert ok >= 9


def test_board_unchanged_after_select_move() -> None:
    for cfg in MCTS_PRESETS.values():
        for pos in (QUIET_74, QUIET_95, MUST_BLOCK_74):
            b = pos.board()
            cand = sorted(b.candidate_moves(2))
            before = state(b)
            agent = MCTSAgent(replace(cfg, max_iterations=300))
            agent.select_move(b, 600.0)
            assert state(b) == before and sorted(b.candidate_moves(2)) == cand
            agent.select_move(b, 0.05)
            assert state(b) == before


def test_time_budget_and_stats() -> None:
    b = QUIET_95.board()
    agent = MCTSAgent(MCTS_HEURISTIC)
    m = agent.select_move(b, 0.3)
    st = agent.last_stats()
    assert m in b.legal_moves()
    assert st.nodes >= 64 and st.time_s < 0.6
    assert st.extra["sims_per_s"] > 0 and st.extra["max_tree_depth"] >= 1


def test_tree_reuse_continues_from_subtree() -> None:
    cfg = replace(MCTS_RANDOM, max_iterations=300)
    b = Board(GameConfig(7, 4))
    for m in (24, 25, 17):
        b.make(m)
    agent = MCTSAgent(cfg)
    mv = agent.select_move(b, 600.0)
    assert agent._root is not None
    sub = agent._root.children[mv]
    assert sub.children
    reply = max(sub.children, key=lambda c: sub.children[c].N)
    prior = sub.children[reply].N
    b.make(mv)
    b.make(reply)
    agent.select_move(b, 600.0)
    assert agent._root is not None and agent._root.N == prior + 300

    fresh = MCTSAgent(replace(cfg, reuse_tree=False))
    fresh.select_move(b, 600.0)
    assert fresh._root is not None and fresh._root.N == 300


def test_rave_amaf_statistics_are_populated_and_bounded() -> None:
    agent = run(MCTS_RAVE, QUIET_74.board(), 800)
    root = agent._root
    assert root is not None
    assert sum(ch.rn for ch in root.children.values()) > 0
    assert all(0.0 <= ch.rw <= ch.rn for ch in root.children.values())


def test_max_rollout_depth_and_no_radius() -> None:
    b = QUIET_95.board()
    agent = run(replace(MCTS_RANDOM, max_rollout_depth=5, candidate_radius=None), b, 300)
    assert agent.select_move(b, 0.1) in b.legal_moves()
    assert agent.last_stats().nodes >= 64


def test_single_legal_move_and_finished_game() -> None:
    cfg = GameConfig(3, 3)
    b = Board.from_string("X O X\nX O O\nO X .", cfg, X)
    assert MCTSAgent(MCTSConfig(max_iterations=10)).select_move(b, 1.0) == 8
    done = Board(cfg)
    for m in (0, 3, 1, 4, 2):
        done.make(m)
    with pytest.raises(ValueError):
        MCTSAgent().select_move(done, 1.0)


def test_exact_k_rollouts_run_to_completion() -> None:
    b = Board(GameConfig(5, 3, exact_k=True))
    agent = MCTSAgent(replace(MCTS_HEURISTIC, max_iterations=300))
    for _ in range(8):
        if b.is_terminal:
            break
        b.make(agent.select_move(b, 5.0))


def test_registry_has_mcts_entries() -> None:
    for name in ("mcts_random", "mcts_heuristic", "mcts_rave"):
        agent = AGENT_REGISTRY[name](3)
        assert agent.select_move(QUIET_74.board(), 0.1) in range(49)


def test_tree_is_not_reused_across_unrelated_positions_without_history() -> None:
    # Boards built by from_string have an empty move history, so a history-prefix
    # check alone would wrongly reuse the previous position's tree.
    cfg = replace(MCTS_RANDOM, max_iterations=150)
    agent = MCTSAgent(cfg)
    for pos in (QUIET_74, WIN_IN_1_74, MUST_BLOCK_74, QUIET_74):
        b = pos.board()
        before = state(b)
        assert agent.select_move(b, 60.0) in b.legal_moves()
        assert agent._root is not None and agent._root.N == 150
        assert state(b) == before


WIN_IN_3 = [WIN_IN_3_A_74, WIN_IN_3_B_74, WIN_IN_3_A_95, WIN_IN_3_B_95]


@pytest.mark.parametrize("pos", WIN_IN_3, ids=lambda p: p.name)
@pytest.mark.parametrize("colour", ["X", "O"])
@pytest.mark.parametrize("cfg", [MCTS_HEURISTIC, MCTS_RAVE], ids=["heuristic", "rave"])
def test_mcts_finds_forced_win_in_3_for_both_colours(
    cfg: MCTSConfig, colour: str, pos: Pos
) -> None:
    """The winning moves are hand-verified and re-derived by exhaustive search in
    tests/test_positions.py; the O-to-move version is the colour-swapped board."""
    b = pos.board() if colour == "X" else mirror(pos)
    for seed in (0, 1):
        agent = MCTSAgent(replace(cfg, max_iterations=4000, seed=seed))
        assert agent.select_move(b, 600.0) in pos.best


@pytest.mark.parametrize("pos", [WIN_IN_3_A_74, WIN_IN_3_B_74], ids=lambda p: p.name)
@pytest.mark.parametrize("colour", ["X", "O"])
def test_random_rollout_mcts_finds_forced_win_in_3_on_7x7(colour: str, pos: Pos) -> None:
    b = pos.board() if colour == "X" else mirror(pos)
    agent = MCTSAgent(replace(MCTS_RANDOM, max_iterations=20000, seed=0))
    assert agent.select_move(b, 600.0) in pos.best
