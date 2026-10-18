import numpy as np
import pytest
from numpy.typing import NDArray

from core.board import Board
from core.rules import EMPTY, O, X, GameConfig

CFG = GameConfig(5, 4)


def test_turn_alternation_and_legal_moves() -> None:
    b = Board(CFG)
    assert b.to_move == X and len(b.legal_moves()) == 25
    b.make(12)
    assert b.to_move == O and 12 not in b.legal_moves() and b.last_move == 12


def test_rc_conversion() -> None:
    b = Board(GameConfig(7, 4))
    assert b.from_rc(2, 3) == 17 and b.to_rc(17) == (2, 3)
    for m in range(49):
        assert b.from_rc(*b.to_rc(m)) == m
    with pytest.raises(ValueError):
        b.from_rc(7, 0)
    with pytest.raises(ValueError):
        b.from_rc(0, -1)


def test_move_history_and_unmake_returns_move() -> None:
    b = Board(CFG)
    for m in (3, 7, 11):
        b.make(m)
    assert b.move_history == (3, 7, 11) and b.ply == 3
    assert b.unmake_move() == 11
    assert b.move_history == (3, 7)
    b.unmake_move()
    b.unmake_move()
    with pytest.raises(IndexError):
        b.unmake_move()


def test_unmake_clears_winner() -> None:
    b = Board(GameConfig(3, 3))
    for m in (0, 3, 1, 4, 2):
        b.make(m)
    assert b.winner == X
    b.unmake_move()
    assert b.winner == EMPTY and b.to_move == X and not b.is_terminal


def test_hash_is_transposition_invariant() -> None:
    a, b = Board(CFG), Board(CFG)
    for m in (0, 1, 2, 3):
        a.make(m)
    for m in (2, 3, 0, 1):
        b.make(m)
    assert a.hash == b.hash
    c = Board(CFG)
    for m in (1, 0, 2, 3):
        c.make(m)
    assert c.hash != a.hash


def test_illegal_moves_rejected() -> None:
    b = Board(CFG)
    b.make(0)
    for bad in (0, -1, 25):
        with pytest.raises(ValueError):
            b.make(bad)
    g = Board(GameConfig(3, 3))
    for m in (0, 3, 1, 4, 2):
        g.make(m)
    with pytest.raises(ValueError):
        g.make(8)
    assert g.legal_moves() == []


def test_copy_is_independent() -> None:
    b = Board(CFG)
    b.candidate_moves(1)
    b.make(3)
    c = b.copy()
    c.make(4)
    assert b.n_empty == 24 and c.n_empty == 23 and b.hash != c.hash
    assert sorted(b.candidate_moves(1)) != sorted(c.candidate_moves(1))
    c.unmake_move()
    assert c.hash == b.hash
    assert sorted(c.candidate_moves(1)) == sorted(b.candidate_moves(1))


def test_empty_cell_order_restored_exactly() -> None:
    b = Board(GameConfig(6, 4))
    rng = np.random.default_rng(3)
    for _ in range(10):
        b.make(int(rng.choice(b.legal_moves())))
    before = list(b.empty_cells)
    moves = [int(rng.choice(b.legal_moves())) for _ in range(1)]
    b.make(moves[0])
    b.unmake_move()
    assert list(b.empty_cells) == before


# ---------------------------------------------------------------- invariants


def full_scan(g: NDArray[np.int8], k: int) -> int:
    n = g.shape[0]
    for r in range(n):
        for c in range(n):
            p = int(g[r, c])
            if p == 0:
                continue
            for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                er, ec = r + (k - 1) * dr, c + (k - 1) * dc
                if 0 <= er < n and 0 <= ec < n and all(
                    g[r + i * dr, c + i * dc] == p for i in range(k)
                ):
                    return p
    return 0


def zobrist_from_scratch(b: Board) -> int:
    h = 0
    for m, v in enumerate(b.cells_list):
        if v != EMPTY:
            h ^= b._zob[0 if v == X else 1][m]
    return h


def check_invariants(b: Board) -> None:
    cfg = b.config
    assert np.array_equal(b.cells, np.array(b.cells_list, dtype=np.int8))
    zeros = np.flatnonzero(b.cells == EMPTY).tolist()
    assert sorted(b.empty_cells) == zeros and b.n_empty == len(zeros)
    for i, m in enumerate(b.empty_cells):
        assert b._epos[m] == i
    assert all(b._epos[m] == -1 for m in range(cfg.n**2) if b.cells_list[m] != EMPTY)
    assert b.hash == zobrist_from_scratch(b)
    assert b.winner == full_scan(b.cells.reshape(cfg.n, cfg.n), cfg.k)
    assert b.to_move == (X if b.ply % 2 == 0 else O)
    if b.winner != EMPTY:
        assert b.legal_moves() == []
    else:
        assert sorted(b.legal_moves()) == zeros


def snapshot(b: Board) -> tuple[bytes, int, int, int, tuple[int, ...]]:
    return (b.cells.tobytes(), b.hash, b.to_move, b.winner, tuple(b.empty_cells))


def test_make_unmake_property_1000_games() -> None:
    configs = [GameConfig(3, 3), GameConfig(5, 4), GameConfig(6, 4)]
    rng = np.random.default_rng(2024)
    for g in range(1000):
        cfg = configs[g % 3]
        b = Board(cfg)
        snaps = [snapshot(b)]
        check_invariants(b)
        target = int(rng.integers(0, cfg.n**2 + 1))
        while not b.is_terminal and b.ply < target:
            b.make(int(rng.choice(b.legal_moves())))
            check_invariants(b)
            snaps.append(snapshot(b))
        for _ in range(int(rng.integers(0, b.ply + 1))):
            b.unmake_move()
            assert snapshot(b) == snaps[b.ply]
            check_invariants(b)
        while not b.is_terminal:
            b.make(int(rng.choice(b.legal_moves())))
        check_invariants(b)
        while b.ply:
            b.unmake_move()
        assert snapshot(b) == snaps[0]


# ---------------------------------------------------------- candidate_moves


def brute_candidates(b: Board, radius: int) -> list[int]:
    n = b.n
    if b.is_terminal:
        return []
    if b.n_empty == n * n:
        return [(n // 2) * n + n // 2]
    stones = [divmod(i, n) for i, v in enumerate(b.cells_list) if v != EMPTY]
    return [
        i
        for i, v in enumerate(b.cells_list)
        if v == EMPTY
        and any(max(abs(i // n - sr), abs(i % n - sc)) <= radius for sr, sc in stones)
    ]


def assert_candidates(b: Board, radii: tuple[int, ...]) -> None:
    for r in radii:
        got = b.candidate_moves(r)
        assert len(got) == len(set(got))
        assert sorted(got) == sorted(brute_candidates(b, r)), (r, str(b))


def test_candidate_moves_match_bruteforce_1000_positions() -> None:
    configs = [GameConfig(5, 4), GameConfig(7, 4), GameConfig(9, 5), GameConfig(11, 5)]
    radii = (1, 2, 3)
    rng = np.random.default_rng(99)
    for p in range(1000):
        cfg = configs[p % 4]
        b = Board(cfg)
        if p % 2 == 0:
            assert_candidates(b, radii)  # trackers maintained from the start
        target = int(rng.integers(0, cfg.n**2 // 2 + 1))
        while not b.is_terminal and b.ply < target:
            b.make(int(rng.choice(b.legal_moves())))
        assert_candidates(b, radii)  # odd p: trackers built lazily mid-game
        for _ in range(int(rng.integers(0, b.ply + 1))):
            b.unmake_move()
        assert_candidates(b, radii)
        for _ in range(2):
            if not b.is_terminal:
                b.make(int(rng.choice(b.legal_moves())))
        assert_candidates(b, radii)


def test_candidate_moves_edge_cases() -> None:
    b = Board(GameConfig(7, 4))
    assert b.candidate_moves(1) == [24] and b.candidate_moves(2) == [24]
    b.make(24)
    assert len(b.candidate_moves(1)) == 8 and len(b.candidate_moves(2)) == 24
    with pytest.raises(ValueError):
        b.candidate_moves(0)
    g = Board(GameConfig(3, 3))
    for m in (0, 3, 1, 4, 2):
        g.make(m)
    assert g.candidate_moves(1) == []


# ---------------------------------------------------------------- strings


def test_str_format() -> None:
    b = Board(GameConfig(3, 3))
    b.make(b.from_rc(0, 1))
    b.make(b.from_rc(2, 2))
    assert str(b) == "   0 1 2\n0  . X .\n1  . . .\n2  . . O"


def test_string_round_trip_random_positions() -> None:
    rng = np.random.default_rng(5)
    for cfg in (GameConfig(3, 3), GameConfig(7, 4), GameConfig(11, 5)):
        for _ in range(100):
            b = Board(cfg)
            for _ in range(int(rng.integers(0, cfg.n**2))):
                if b.is_terminal:
                    break
                b.make(int(rng.choice(b.legal_moves())))
            r = Board.from_string(str(b), cfg, b.to_move)
            assert np.array_equal(r.cells, b.cells)
            assert r.cells_list == b.cells_list
            assert (r.hash, r.to_move, r.winner, r.n_empty) == (
                b.hash,
                b.to_move,
                b.winner,
                b.n_empty,
            )
            assert str(r) == str(b)
            check_invariants_loose(r)


def check_invariants_loose(b: Board) -> None:
    assert sorted(b.empty_cells) == np.flatnonzero(b.cells == EMPTY).tolist()
    assert b.hash == zobrist_from_scratch(b)


def test_from_string_bare_grid_and_play_on() -> None:
    b = Board.from_string("X X .\nO O .\n. . .", GameConfig(3, 3), X)
    assert b.winner == EMPTY and b.n_empty == 5 and b.move_history == ()
    b.make(2)
    assert b.winner == X
    b.unmake_move()
    assert b.winner == EMPTY


def test_from_string_detects_existing_win() -> None:
    b = Board.from_string("X X X\nO O .\n. . .", GameConfig(3, 3), O)
    assert b.winner == X and b.legal_moves() == []


@pytest.mark.parametrize(
    "text, to_move",
    [
        ("X X .\nO O .", X),
        ("X X .\nO O .\n. . Z", X),
        ("X . .\n. . .\n. . .", X),
        ("X X X\nO O O\n. . .", O),
    ],
)
def test_from_string_rejects_bad_input(text: str, to_move: int) -> None:
    with pytest.raises(ValueError):
        Board.from_string(text, GameConfig(3, 3), to_move)


def _brute_candidates(b: Board, radius: int) -> set[int]:
    n = b.n
    stones = [m for m in range(n * n) if b.cells_list[m] != 0]
    return {
        m
        for m in range(n * n)
        if b.cells_list[m] == 0
        and any(
            max(abs(m // n - s // n), abs(m % n - s % n)) <= radius for s in stones
        )
    }


def test_default_copy_carries_no_candidate_counters() -> None:
    b = Board(CFG)
    b.make(12)
    b.candidate_moves(1)
    b.candidate_moves(2)
    c = b.copy()
    assert c._trackers == {} and c._tracker_list == []
    c.make(13)
    c.make(7)
    c.unmake_move()
    c.unmake_move()
    assert c._trackers == {} and c._tracker_list == []
    assert c.hash == b.hash and list(c.empty_cells) == list(b.empty_cells)
    assert set(c.candidate_moves(1)) == _brute_candidates(c, 1)
    assert len(b._tracker_list) == 2


def test_tracked_copy_keeps_correct_counters() -> None:
    b = Board(CFG)
    b.make(12)
    b.candidate_moves(2)
    b.make(6)
    c = b.copy(track_candidates=True)
    assert len(c._tracker_list) == 1
    c.make(18)
    assert set(c.candidate_moves(2)) == _brute_candidates(c, 2)
    assert set(b.candidate_moves(2)) == _brute_candidates(b, 2)
    c.unmake_move()
    assert set(c.candidate_moves(2)) == _brute_candidates(c, 2)
