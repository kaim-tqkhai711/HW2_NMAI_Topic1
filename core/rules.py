"""Win detection for the (N, k) generalized tic-tac-toe."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

EMPTY = 0
X = 1
O = -1

_DIRECTIONS: tuple[tuple[int, int], ...] = ((0, 1), (1, 0), (1, 1), (1, -1))


@dataclass(frozen=True)
class GameConfig:
    """Board size and win condition.

    Attributes:
        n: Board side length.
        k: Stones in a row needed to win.
        exact_k: If True only a run of exactly k wins; longer runs do not.
    """

    n: int
    k: int
    exact_k: bool = False

    def __post_init__(self) -> None:
        if self.k < 1 or self.k > self.n:
            raise ValueError(f"need 1 <= k <= n, got n={self.n}, k={self.k}")


def wins_at(cells: Sequence[int], cfg: GameConfig, idx: int, player: int) -> bool:
    """Whether `player` has a winning line through the stone at `idx`.

    Args:
        cells: Flat row-major cell values (EMPTY/X/O).
        cfg: Game configuration.
        idx: Flat index of a cell occupied by `player`.
        player: X or O.
    """
    n, k = cfg.n, cfg.k
    r0, c0 = divmod(idx, n)
    for dr, dc in _DIRECTIONS:
        length = 1
        r, c = r0 + dr, c0 + dc
        while 0 <= r < n and 0 <= c < n and cells[r * n + c] == player:
            length += 1
            r += dr
            c += dc
        r, c = r0 - dr, c0 - dc
        while 0 <= r < n and 0 <= c < n and cells[r * n + c] == player:
            length += 1
            r -= dr
            c -= dc
        if length == k or (length > k and not cfg.exact_k):
            return True
    return False
