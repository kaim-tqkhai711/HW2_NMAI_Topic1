import numpy as np

from agents.evaluation import EvalWeights, IncrementalEval, evaluate
from core.board import Board
from core.rules import GameConfig, O, X

DIRS = ((0, 1), (1, 0), (1, 1), (1, -1))


def ref_score(cells: list[int], cfg: GameConfig, w: EvalWeights) -> int:
    """X-perspective score straight from the definition, by coordinates."""
    n, k = cfg.n, cfg.k

    def at(r: int, c: int) -> int | None:
        return cells[r * n + c] if 0 <= r < n and 0 <= c < n else None

    total = 0
    for r in range(n):
        for c in range(n):
            for dr, dc in DIRS:
                if at(r + (k - 1) * dr, c + (k - 1) * dc) is not None:
                    win = [cells[(r + i * dr) * n + c + i * dc] for i in range(k)]
                    x, o = win.count(X), win.count(O)
                    if x and not o:
                        total += w.window[x]
                    elif o and not x:
                        total -= w.window[o]
                v = cells[r * n + c]
                if v == 0 or at(r - dr, c - dc) == v:
                    continue
                length = 0
                while at(r + length * dr, c + length * dc) == v:
                    length += 1
                ends = (at(r - dr, c - dc) == 0) + (at(r + length * dr, c + length * dc) == 0)
                bonus = 0
                if length == k - 1 and ends == 2:
                    bonus = w.open_k1
                elif length == k - 1 and ends == 1:
                    bonus = w.half_k1
                elif length == k - 2 and ends == 2:
                    bonus = w.open_k2
                total += bonus * v
    return total


def random_position(cfg: GameConfig, rng: np.random.Generator, plies: int) -> Board:
    b = Board(cfg)
    for _ in range(plies):
        if b.is_terminal:
            break
        b.make(int(rng.choice(b.legal_moves())))
    return b


def test_hand_computed_value() -> None:
    cfg = GameConfig(5, 3)
    w = EvalWeights(window=(0, 1, 10, 100), open_k1=1000, half_k1=500, open_k2=7)
    # Single X at the centre of a 5x5: 12 windows of length 3 contain it? centre
    # (2,2): row 3, col 3, diag 3, anti 3 = 12 windows, each worth w[1]=1.
    # Runs of length 1 = k-2 with both ends open in all 4 directions: 4 * open_k2.
    b = Board.from_string(". . . . .\n. . . . .\n. . X . .\n. . . . .\n. . . . .", cfg, O)
    assert evaluate(b.cells_list, cfg, X, w) == 12 * 1 + 4 * 7
    assert evaluate(b.cells_list, cfg, O, w) == -(12 * 1 + 4 * 7)
    # X at (2,0),(2,1): windows 10+1 (row) +3+3 (cols) +1+1 (diags of (2,0))
    # +2+2 (diags of (2,1)) = 23; half-open 2-run = 500; four open singles = 28.
    cells = [0] * 25
    cells[2 * 5 + 0] = cells[2 * 5 + 1] = X
    assert evaluate(cells, cfg, X, w) == 23 + 500 + 28


def test_mixed_windows_cancel_and_symmetry() -> None:
    cfg = GameConfig(5, 4)
    w = EvalWeights.default(4)
    rng = np.random.default_rng(1)
    for _ in range(50):
        b = random_position(cfg, rng, int(rng.integers(0, 15)))
        flipped = [-v for v in b.cells_list]
        assert ref_score(flipped, cfg, w) == -ref_score(b.cells_list, cfg, w)
        assert evaluate(flipped, cfg, X, w) == -evaluate(b.cells_list, cfg, X, w)


def test_full_matches_reference_definition() -> None:
    rng = np.random.default_rng(2)
    for n, k in [(5, 3), (6, 4), (7, 4), (9, 5)]:
        cfg = GameConfig(n, k)
        w = EvalWeights.default(k)
        for _ in range(40):
            b = random_position(cfg, rng, int(rng.integers(0, n * n // 2)))
            score = ref_score(b.cells_list, cfg, w)
            assert evaluate(b.cells_list, cfg, X, w) == score
            assert evaluate(b.cells_list, cfg, O, w) == -score


def test_incremental_equals_full_on_500_positions() -> None:
    rng = np.random.default_rng(3)
    checked = 0
    for n, k in [(7, 4), (9, 5)]:
        cfg = GameConfig(n, k)
        w = EvalWeights.default(k)
        while checked < (250 if n == 7 else 500):
            b = Board(cfg)
            inc = IncrementalEval(b.cells_list, cfg, w)
            depth = int(rng.integers(1, n * n // 2))
            for _ in range(depth):
                if b.is_terminal:
                    break
                m = int(rng.choice(b.legal_moves()))
                b.make(m)
                inc.push(m)
                if rng.random() < 0.25:
                    b.unmake_move()
                    inc.pop()
                    continue
                assert inc.value(b.to_move) == evaluate(b.cells_list, cfg, b.to_move, w)
                checked += 1
            while b.ply:
                b.unmake_move()
                inc.pop()
                assert inc.value(b.to_move) == evaluate(b.cells_list, cfg, b.to_move, w)
            assert inc.total == 0
    assert checked >= 500
