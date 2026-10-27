import pytest

from agents.backtracking import BacktrackingAgent
from core.board import Board
from core.rules import GameConfig, X
from experiments.run_backtracking_growth import leaf_bound, node_bound
from experiments.run_solve import solve
from tests.test_agents import state


def brute_value(cfg: GameConfig) -> int:
    """Value for X by fully independent enumeration of move orders on a bare list."""
    n, k = cfg.n, cfg.k
    lines = []
    for r in range(n):
        for c in range(n):
            for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                cells = [(r + i * dr, c + i * dc) for i in range(k)]
                if all(0 <= a < n and 0 <= b < n for a, b in cells):
                    lines.append([a * n + b for a, b in cells])

    def rec(g: list[int], turn: int) -> int:
        for ln in lines:
            if all(g[i] == -turn for i in ln):
                return -1
        empt = [i for i, v in enumerate(g) if v == 0]
        if not empt:
            return 0
        best = -1
        for i in empt:
            g[i] = turn
            best = max(best, -rec(g, -turn))
            g[i] = 0
        return best

    return rec([0] * (n * n), 1)


@pytest.mark.slow
def test_known_values() -> None:
    assert solve(GameConfig(3, 3)).value == 0
    assert solve(GameConfig(4, 3)).value == 1  # first player wins 4x4, k=3
    assert solve(GameConfig(4, 4)).value == 0  # gate: 4x4, k=4 is a draw


def test_solver_matches_independent_brute_force() -> None:
    for n, k in [(2, 2), (3, 2), (3, 3)]:
        cfg = GameConfig(n, k)
        expected = brute_value(cfg)
        for memo, sym in [(False, False), (True, False), (True, True)]:
            assert solve(cfg, memo=memo, symmetry=sym).value == expected


def test_memoization_reduces_nodes() -> None:
    cfg = GameConfig(3, 3)
    plain = solve(cfg, memo=False)
    memo = solve(cfg, memo=True, symmetry=False)
    sym = solve(cfg, memo=True, symmetry=True)
    assert sym.nodes < memo.nodes < plain.nodes < 549946  # full tree has 549946 nodes


def test_best_first_move_is_optimal() -> None:
    r = solve(GameConfig(3, 2))
    b = Board(GameConfig(3, 2))
    assert r.best_first_move is not None
    b.make(r.best_first_move)
    assert solve_from(b) == -1


def solve_from(b: Board) -> int:
    """Independent negamax from an arbitrary position (value for side to move)."""
    if b.winner:
        return -1
    moves = b.legal_moves()
    if not moves:
        return 0
    best = -1
    for m in moves:
        b.make(m)
        best = max(best, -solve_from(b))
        b.unmake_move()
    return best


def test_solver_timeout_returns_unsolved() -> None:
    r = solve(GameConfig(5, 4), memo=False, timeout_s=0.05)
    assert not r.solved and r.value is None and r.best_first_move is None


def test_win_in_one_is_chosen() -> None:
    b = Board.from_string("X X .\nO O .\n. . .", GameConfig(3, 3), X)
    agent = BacktrackingAgent()
    assert agent.select_move(b, 30.0) == 2
    assert agent.last_stats().extra["timed_out"] == 0.0


def test_blocks_opponent_win_in_one() -> None:
    cfg = GameConfig(3, 3)
    b = Board.from_string("O O .\nX . .\nX . .", cfg, X)
    # O threatens to finish row 0 at cell 2; X has no immediate win.
    assert BacktrackingAgent().select_move(b, 30.0) == 2


def test_prefers_faster_win() -> None:
    # X also wins later by other routes; only cell 2 wins at ply 1.
    b = Board.from_string("X X .\nO O .\n. . .", GameConfig(3, 3), X)
    agent = BacktrackingAgent()
    agent.select_move(b, 30.0)
    assert agent.last_stats().extra["score"] == 999_999


def test_board_unchanged_after_select_move_including_timeout() -> None:
    cfg = GameConfig(5, 4)
    b = Board(cfg)
    for m in (12, 7, 13):
        b.make(m)
    before = state(b)
    agent = BacktrackingAgent()
    agent.select_move(b, 0.05)
    assert state(b) == before
    assert agent.last_stats().extra["timed_out"] == 1.0
    BacktrackingAgent(max_depth=2).select_move(b, 10.0)
    assert state(b) == before


def test_timeout_still_returns_legal_move_and_stats() -> None:
    b = Board(GameConfig(7, 4))
    agent = BacktrackingAgent()
    m = agent.select_move(b, 0.02)
    st = agent.last_stats()
    assert m in b.legal_moves() and st.extra["timed_out"] == 1.0 and st.nodes > 0


def test_depth_limit_node_counts_match_closed_form_without_wins() -> None:
    # With k = N = 7 no win is possible within 3 plies, so the tree is full.
    cfg = GameConfig(7, 7)
    for d in (1, 2, 3):
        agent = BacktrackingAgent(max_depth=d)
        agent.select_move(Board(cfg), 60.0)
        assert agent.last_stats().nodes == node_bound(7, d)
        assert agent.last_stats().depth_reached == d


def test_bounds() -> None:
    assert leaf_bound(7, 3) == 49 * 48 * 47
    assert node_bound(3, 2) == 1 + 9 + 72


def test_finished_game_rejected() -> None:
    b = Board(GameConfig(3, 3))
    for m in (0, 3, 1, 4, 2):
        b.make(m)
    with pytest.raises(ValueError):
        BacktrackingAgent().select_move(b, 1.0)


def test_without_early_stop_the_memo_free_tree_is_exactly_the_known_size() -> None:
    r = solve(GameConfig(3, 3), memo=False, early_stop=False)
    assert r.value == 0 and r.nodes == 549946  # all positions of 3x3 tic-tac-toe


@pytest.mark.slow
def test_early_stop_never_changes_the_value_only_the_work() -> None:
    # (4,3) with plain memo and no early stop does not finish in minutes, so only
    # the symmetric memo is used there.
    cases = [((3, 2), False), ((3, 2), True), ((3, 3), False), ((3, 3), True), ((4, 3), True)]
    for (n, k), sym in cases:
        cfg = GameConfig(n, k)
        for memo in (True,):
            full = solve(cfg, memo=memo, symmetry=sym, early_stop=False)
            fast = solve(cfg, memo=memo, symmetry=sym, early_stop=True)
            assert full.value == fast.value and full.nodes >= fast.nodes


def test_shipped_growth_csv_is_plain_minimax_without_pruning() -> None:
    # BacktrackingAgent has no memo, symmetry or cutoffs; with k=4 on 7x7 no win is
    # possible within 6 plies, so every completed depth must hit the closed form exactly.
    import csv
    from pathlib import Path

    rows = list(csv.DictReader(
        (Path(__file__).resolve().parent.parent / "results" / "backtracking_growth.csv").open()))
    done = [r for r in rows if r["timed_out"] == "0"]
    assert len(done) >= 4
    for r in done:
        assert int(r["nodes"]) == int(r["bound_nodes"]), r
    assert any(r["timed_out"] == "1" for r in rows)
