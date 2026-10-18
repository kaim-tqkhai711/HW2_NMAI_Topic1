r"""Pattern-based static evaluation for the (N, k) game.

Formula (X-perspective score; the caller negates it when O is to move)::

    E(s) = \sum_{W \in \mathcal{W}} \sigma(W) + \sum_{R \in \mathcal{R}} \tau(R)

where :math:`\mathcal{W}` is the set of all length-k windows (cell segments) in
the four directions (row, column, diagonal, anti-diagonal), and for a window
with :math:`x` X-stones and :math:`o` O-stones::

    \sigma(W) = +w[x]   if o = 0 and x > 0
              = -w[o]   if x = 0 and o > 0
              =  0      otherwise (empty or mixed)

:math:`\mathcal{R}` is the set of maximal runs of equal stones along a line. A
run of length :math:`\ell` with :math:`e \in \{0,1,2\}` open ends (the cell
just beyond the end exists and is empty) contributes, with sign +1 for X and
-1 for O::

    \tau(R) = sign * open_k1   if l = k-1 and e = 2
            = sign * half_k1   if l = k-1 and e = 1
            = sign * open_k2   if l = k-2 and e = 2 (k >= 3)
            = 0                otherwise

Broken patterns such as ``X X . X`` are covered only by the window term.
Every term depends on a single line, so a move at cell c changes only the four
lines through c; `IncrementalEval` rescans exactly those.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from core.rules import EMPTY, X, GameConfig


@dataclass(frozen=True)
class EvalWeights:
    """Tunable weights of the evaluation.

    Attributes:
        window: ``window[c]`` is the value of a window holding c stones of one
            side and none of the other, for c in 0..k (``window[0]`` is 0).
        open_k1: Run of k-1 with both ends open.
        half_k1: Run of k-1 with exactly one open end.
        open_k2: Run of k-2 with both ends open.
    """

    window: tuple[int, ...]
    open_k1: int
    half_k1: int
    open_k2: int

    @staticmethod
    def default(k: int) -> EvalWeights:
        """Geometric weights scaled to the win length."""
        window = (0,) + tuple(10 ** (c - 1) for c in range(1, k)) + (10**k,)
        return EvalWeights(
            window=window,
            open_k1=5 * 10 ** (k - 1),
            half_k1=10 ** (k - 1),
            open_k2=10 ** (k - 2) if k >= 3 else 0,
        )


@lru_cache(maxsize=None)
def _lines(n: int) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    """All lines of the board as cell tuples, and per cell the 4 line ids through it."""
    lines: list[tuple[int, ...]] = []
    through: list[list[int]] = [[] for _ in range(n * n)]

    def add(cells: list[int]) -> None:
        lid = len(lines)
        lines.append(tuple(cells))
        for c in cells:
            through[c].append(lid)

    for r in range(n):
        add([r * n + c for c in range(n)])
    for c in range(n):
        add([r * n + c for r in range(n)])
    for d in range(-(n - 1), n):
        add([r * n + (r - d) for r in range(n) if 0 <= r - d < n])
    for s in range(2 * n - 1):
        add([r * n + (s - r) for r in range(n) if 0 <= s - r < n])
    return tuple(lines), tuple(tuple(t) for t in through)


def line_score(cells: list[int], line: tuple[int, ...], k: int, w: EvalWeights) -> int:
    """X-perspective score of one line (window term plus run-threat term)."""
    length = len(line)
    if length < k:
        return 0
    vals = [cells[i] for i in line]
    total = 0
    wt = w.window
    nx = sum(1 for v in vals[:k] if v == X)
    no = sum(1 for v in vals[:k] if v == -X)
    for s in range(length - k + 1):
        if s:
            out, inn = vals[s - 1], vals[s + k - 1]
            if out == X:
                nx -= 1
            elif out == -X:
                no -= 1
            if inn == X:
                nx += 1
            elif inn == -X:
                no += 1
        if no == 0:
            total += wt[nx]
        elif nx == 0:
            total -= wt[no]
    i = 0
    while i < length:
        v = vals[i]
        if v == EMPTY:
            i += 1
            continue
        j = i
        while j + 1 < length and vals[j + 1] == v:
            j += 1
        run = j - i + 1
        if run >= k - 2:
            ends = (i > 0 and vals[i - 1] == EMPTY) + (j + 1 < length and vals[j + 1] == EMPTY)
            bonus = 0
            if run == k - 1:
                bonus = w.open_k1 if ends == 2 else w.half_k1 if ends == 1 else 0
            elif run == k - 2 and ends == 2:
                bonus = w.open_k2
            total += bonus if v == X else -bonus
        i = j + 1
    return total


def evaluate(cells: list[int], config: GameConfig, to_move: int, w: EvalWeights) -> int:
    """Full evaluation from the side-to-move's perspective (negamax convention)."""
    lines, _ = _lines(config.n)
    total = sum(line_score(cells, ln, config.k, w) for ln in lines)
    return total if to_move == X else -total


class IncrementalEval:
    """Evaluation maintained across make/unmake by rescanning only 4 lines.

    Usage: call `push(move)` right after `board.make(move)` and `pop()` right
    after `board.unmake_move()`.

    Args:
        cells: The board's live `cells_list`; it is read, never written.
        config: Game configuration.
        weights: Evaluation weights; defaults to `EvalWeights.default(k)`.
    """

    def __init__(
        self, cells: list[int], config: GameConfig, weights: EvalWeights | None = None
    ) -> None:
        self.cells = cells
        self.k = config.k
        self.w = weights or EvalWeights.default(config.k)
        self._lines, self._through = _lines(config.n)
        self.line_vals = [line_score(cells, ln, self.k, self.w) for ln in self._lines]
        self.total = sum(self.line_vals)
        self._stack: list[tuple[int, ...]] = []

    def push(self, move: int) -> None:
        """Update after `cells[move]` changed (a stone was placed)."""
        saved: list[int] = []
        for lid in self._through[move]:
            old = self.line_vals[lid]
            new = line_score(self.cells, self._lines[lid], self.k, self.w)
            saved.append(old)
            self.line_vals[lid] = new
            self.total += new - old
        self._stack.append((move, *saved))

    def pop(self) -> None:
        """Undo the most recent `push` (call after the board's `unmake_move`)."""
        move, *saved = self._stack.pop()
        for lid, old in zip(self._through[move], saved):
            self.total += old - self.line_vals[lid]
            self.line_vals[lid] = old

    def value(self, to_move: int) -> int:
        """Score from the side-to-move's perspective."""
        return self.total if to_move == X else -self.total
