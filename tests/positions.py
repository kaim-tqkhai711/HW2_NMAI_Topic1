"""Fixed hand-built test positions (7x7 k=4 and 9x9 k=5).

Every position lists the acceptable first moves for the side to move and, for
forced wins, the exact ply at which the win lands. The expectations are derived
by hand and re-verified in tests/test_positions.py by an independent
exhaustive search that shares no code with the agents.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.board import Board
from core.rules import O, X, GameConfig

C74 = GameConfig(7, 4)
C95 = GameConfig(9, 5)


@dataclass(frozen=True)
class Pos:
    """A position with its expected answer.

    Attributes:
        name: Short identifier.
        cfg: Game configuration.
        grid: Rows separated by newlines, cells X/O/.
        to_move: Side to move.
        best: Acceptable first moves (flat indices); empty for quiet positions.
        win_ply: Ply at which the side to move forces a win (1 = immediately),
            or None.
    """

    name: str
    cfg: GameConfig
    grid: str
    to_move: int
    best: frozenset[int]
    win_ply: int | None

    def board(self) -> Board:
        return Board.from_string(self.grid, self.cfg, self.to_move)


def _g(*rows: str) -> str:
    return "\n".join(rows)


def _rc(n: int, *cells: tuple[int, int]) -> frozenset[int]:
    return frozenset(r * n + c for r, c in cells)


WIN_IN_1_74 = Pos(
    "win_in_1_7x7",
    C74,
    _g(
        ". . . . . . .",
        ". . . . . . .",
        ". O O . . . .",
        ". X X X . . .",
        ". . . . O . .",
        ". . . . . . .",
        ". . . . . . .",
    ),
    X,
    _rc(7, (3, 0), (3, 4)),
    1,
)
"""X has three in row 3 with both ends empty: completing either end wins at once."""

MUST_BLOCK_74 = Pos(
    "must_block_7x7",
    C74,
    _g(
        ". . . . . . .",
        ". . . . . . .",
        ". . . . . . .",
        ". X O O O . .",
        ". . . . . . .",
        ". . X . . . .",
        ". . . . . . X",
    ),
    X,
    _rc(7, (3, 5)),
    None,
)
"""O threatens to complete row 3 at (3,5) (the other end is X); X has no win, so
the only non-losing move is the block at (3,5)."""

WIN_IN_3_A_74 = Pos(
    "win_in_3_open_three_7x7",
    C74,
    _g(
        ". . . . . . O",
        ". . . . . . .",
        ". . . . . . .",
        ". . X X . . .",
        ". . . . . . .",
        ". . . . . . .",
        "O . . . . . .",
    ),
    X,
    _rc(7, (3, 1), (3, 4)),
    3,
)
"""Extending the open two to an open three ((3,1) or (3,4)) wins on the third ply:
O can block only one end."""

WIN_IN_3_B_74 = Pos(
    "win_in_3_column_7x7",
    C74,
    _g(
        ". . . . . . .",
        ". . . X . . .",
        ". . . X . . .",
        ". . . . . . .",
        ". . . . . . .",
        ". O . . . O .",
        ". . . . . . .",
    ),
    X,
    _rc(7, (3, 3)),
    3,
)
"""Vertical open two in column 3 (rows 1-2): only (3,3) wins by force, making an
open three whose ends (rows 0 and 4) are both free. (0,3) or (4,3) leave a single
completion cell that O can simply take."""

QUIET_74 = Pos(
    "quiet_midgame_7x7",
    C74,
    _g(
        ". . . . . . .",
        ". . X . . . .",
        ". O . O . . .",
        ". . . X O . .",
        ". X . O . . .",
        ". . . . X . .",
        ". . . . . . .",
    ),
    X,
    frozenset(),
    None,
)
"""No stone has a line of three; used to compare minimax values across configs."""

WIN_IN_1_95 = Pos(
    "win_in_1_9x9",
    C95,
    _g(
        ". . . . . . . . .",
        ". . . . . . . . .",
        ". . . . X O . . .",
        ". . . . X O . . .",
        ". . . . X O . . .",
        ". . . . X . . . .",
        ". . . . . . . . .",
        ". . . . . . . O .",
        ". . . . . . . . .",
    ),
    X,
    _rc(9, (1, 4), (6, 4)),
    1,
)
"""X has four in column 4 (rows 2-5) with both ends empty: (1,4) or (6,4) wins."""

MUST_BLOCK_95 = Pos(
    "must_block_9x9",
    C95,
    _g(
        "X . . . . . . . X",
        ". . . . . . . . .",
        ". . . . . . . . .",
        ". . . . . . . . .",
        ". X O O O O . . .",
        ". . . . . . . . .",
        ". . . . . . . . .",
        ". . . . . . . . .",
        "X . . . . . . . .",
    ),
    X,
    _rc(9, (4, 6)),
    None,
)
"""O has four in row 4 (cols 2-5) with the left end blocked by X: block at (4,6)."""

WIN_IN_3_A_95 = Pos(
    "win_in_3_open_four_9x9",
    C95,
    _g(
        "O . . . . . . . O",
        ". . . . . . . . .",
        ". . . . . . . . .",
        ". . . . . . . . .",
        ". . . X X X . . .",
        ". . . . . . . . .",
        ". . . . . . . . .",
        ". . . . . . . . .",
        "O . . . . . . . .",
    ),
    X,
    _rc(9, (4, 2), (4, 6)),
    3,
)
"""Open three in row 4 with room on both sides: (4,2) or (4,6) makes an open four,
which wins on the third ply."""

WIN_IN_3_B_95 = Pos(
    "win_in_3_column_9x9",
    C95,
    _g(
        ". . O . . . . . .",
        ". . . . . . . . .",
        ". . . . . . X . .",
        ". . . . . . X . .",
        ". . . . . . X . .",
        ". . . . . . . . .",
        ". . . . . . . . .",
        ". O . . . . . . .",
        "O . . . . . . . .",
    ),
    X,
    _rc(9, (1, 6), (5, 6)),
    3,
)
"""Vertical open three in column 6 (rows 2-4): (1,6) or (5,6) makes an open four."""

QUIET_95 = Pos(
    "quiet_midgame_9x9",
    C95,
    _g(
        ". . . . . . . . .",
        ". . . . . . . . .",
        ". . . X . . . . .",
        ". . . . O . . . .",
        ". . . O X O . . .",
        ". X . . O . . . .",
        ". . . . . X . . .",
        ". . . . . . . . .",
        ". . . . . . . . .",
    ),
    X,
    frozenset(),
    None,
)
"""Compact centre fight with no line of four; used for value comparisons."""

_MIDGAME_LINES: tuple[tuple[int, ...], ...] = (
    (40, 41, 31, 49, 32, 30, 50, 22, 23, 39),
    (40, 39, 41, 31, 42, 43, 32, 49, 33, 50),
    (40, 30, 50, 32, 31, 49, 22, 58, 23, 13, 41, 42),
)


def midgame_positions_95() -> list[Board]:
    """Three fixed 9x9 k=5 midgame positions reached by fixed move sequences."""
    boards = []
    for line in _MIDGAME_LINES:
        b = Board(C95)
        for m in line:
            b.make(m)
        boards.append(b)
    return boards


ALL_POSITIONS: tuple[Pos, ...] = (
    WIN_IN_1_74,
    MUST_BLOCK_74,
    WIN_IN_3_A_74,
    WIN_IN_3_B_74,
    QUIET_74,
    WIN_IN_1_95,
    MUST_BLOCK_95,
    WIN_IN_3_A_95,
    WIN_IN_3_B_95,
    QUIET_95,
)
