"""Mutable board with make/unmake, incremental candidate moves and Zobrist hash."""
from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache

import numpy as np
from numpy.typing import NDArray

from core.rules import EMPTY, O, X, GameConfig, wins_at

_ZOBRIST_SEED = 0x5EED
_SYMBOL = {X: "X", O: "O", EMPTY: "."}
_PARSE = {"X": X, "x": X, "O": O, "o": O, ".": EMPTY}


@lru_cache(maxsize=None)
def _zobrist_keys(size: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    rng = np.random.default_rng(_ZOBRIST_SEED)
    keys = rng.integers(0, 2**63, size=(2, size), dtype=np.uint64)
    return tuple(keys[0].tolist()), tuple(keys[1].tolist())


class _Neighbourhood:
    """Empty cells within Chebyshev `radius` of some stone, kept incrementally.

    `near[c]` counts stones within the radius of cell c; `items` holds exactly
    the empty cells with a positive count, index-backed by `pos` for O(1)
    insert/remove.
    """

    def __init__(self, n: int, radius: int, cells: Sequence[int]) -> None:
        self.nbrs: tuple[tuple[int, ...], ...] = tuple(
            tuple(
                r2 * n + c2
                for r2 in range(max(0, r - radius), min(n, r + radius + 1))
                for c2 in range(max(0, c - radius), min(n, c + radius + 1))
                if (r2, c2) != (r, c)
            )
            for r in range(n)
            for c in range(n)
        )
        self.near = [0] * (n * n)
        self.items: list[int] = []
        self.pos = [-1] * (n * n)
        for m, v in enumerate(cells):
            if v != EMPTY:
                self.on_place(m, cells)

    def copy(self) -> _Neighbourhood:
        t = _Neighbourhood.__new__(_Neighbourhood)
        t.nbrs = self.nbrs
        t.near = self.near[:]
        t.items = self.items[:]
        t.pos = self.pos[:]
        return t

    def _add(self, x: int) -> None:
        self.pos[x] = len(self.items)
        self.items.append(x)

    def _remove(self, x: int) -> None:
        i = self.pos[x]
        last = self.items.pop()
        if last != x:
            self.items[i] = last
            self.pos[last] = i
        self.pos[x] = -1

    def on_place(self, m: int, cells: Sequence[int]) -> None:
        """Update after `cells[m]` became occupied."""
        if self.pos[m] >= 0:
            self._remove(m)
        near = self.near
        for nb in self.nbrs[m]:
            near[nb] += 1
            if near[nb] == 1 and cells[nb] == EMPTY:
                self._add(nb)

    def on_remove(self, m: int, cells: Sequence[int]) -> None:
        """Update after `cells[m]` became empty."""
        near = self.near
        for nb in self.nbrs[m]:
            near[nb] -= 1
            if near[nb] == 0 and cells[nb] == EMPTY:
                self._remove(nb)
        if near[m] > 0:
            self._add(m)


class Board:
    """N x N board; a move is a flat row-major index `r * N + c`.

    `cells` (numpy int8) is the canonical public view. `cells_list` mirrors it
    as a Python list for hot-path reads; both are updated together by
    `make`/`unmake_move`, which mutate in place so search never copies a board.
    """

    def __init__(self, config: GameConfig) -> None:
        size = config.n * config.n
        self.config = config
        self.n = config.n
        self.cells: NDArray[np.int8] = np.zeros(size, dtype=np.int8)
        self.cells_list: list[int] = [EMPTY] * size
        self.to_move = X
        self.winner = EMPTY
        self.hash = 0
        self._size = size
        self._history: list[int] = []
        self._empties = list(range(size))
        self._epos = list(range(size))
        self._eidx: list[int] = []
        self._count = [0, 0, 0]  # stones per player, indexed by X=1 / O=-1
        self._zob = _zobrist_keys(size)
        self._trackers: dict[int, _Neighbourhood] = {}
        self._tracker_list: list[_Neighbourhood] = []

    @classmethod
    def from_string(cls, s: str, config: GameConfig, to_move: int) -> Board:
        """Parse a position, either a bare grid or the output of `str(board)`.

        Cells are X/O/. separated by whitespace; an optional header row and
        leading row labels are ignored. The resulting board has no move history.

        Raises:
            ValueError: On wrong dimensions, unknown symbols, stone counts that
                are inconsistent with X moving first, or both sides winning.
        """
        n = config.n
        rows = [ln.split() for ln in s.strip().splitlines() if ln.strip()]
        if rows and all(tok.isdigit() for tok in rows[0]):
            rows = rows[1:]
        if len(rows) != n:
            raise ValueError(f"expected {n} rows, got {len(rows)}")
        board = cls(config)
        for r, toks in enumerate(rows):
            if len(toks) == n + 1 and toks[0].isdigit():
                toks = toks[1:]
            if len(toks) != n:
                raise ValueError(f"row {r}: expected {n} cells, got {len(toks)}")
            for c, tok in enumerate(toks):
                if tok not in _PARSE:
                    raise ValueError(f"row {r}: unknown symbol {tok!r}")
                if _PARSE[tok] != EMPTY:
                    board._place_raw(r * n + c, _PARSE[tok])
        nx, no = board._count[X], board._count[O]
        if nx - no != (0 if to_move == X else 1):
            raise ValueError(
                f"{nx} X and {no} O stones do not fit {'X' if to_move == X else 'O'} to move"
            )
        board.to_move = to_move
        won = {
            v
            for m, v in enumerate(board.cells_list)
            if v != EMPTY and wins_at(board.cells_list, config, m, v)
        }
        if len(won) > 1:
            raise ValueError("both players have a winning line")
        board.winner = won.pop() if won else EMPTY
        return board

    def to_rc(self, move: int) -> tuple[int, int]:
        """Convert a flat move index to (row, col)."""
        return divmod(move, self.n)

    def from_rc(self, r: int, c: int) -> int:
        """Convert (row, col) to a flat move index.

        Raises:
            ValueError: If the coordinates are off the board.
        """
        if not (0 <= r < self.n and 0 <= c < self.n):
            raise ValueError(f"({r}, {c}) is off the {self.n}x{self.n} board")
        return r * self.n + c

    @property
    def last_move(self) -> int | None:
        """Most recent move, or None if none has been made."""
        return self._history[-1] if self._history else None

    @property
    def move_history(self) -> tuple[int, ...]:
        """Moves played via `make`, oldest first."""
        return tuple(self._history)

    @property
    def ply(self) -> int:
        """Number of moves played via `make` and not yet unmade."""
        return len(self._history)

    @property
    def n_empty(self) -> int:
        """Number of empty cells."""
        return len(self._empties)

    @property
    def is_terminal(self) -> bool:
        """True if someone has won or the board is full."""
        return self.winner != EMPTY or not self._empties

    @property
    def empty_cells(self) -> Sequence[int]:
        """Live, unordered view of the empty cells; do not mutate or retain.

        Unlike `legal_moves`, this does not check for a finished game and does
        not copy, so it is the fast path for rollouts.
        """
        return self._empties

    def legal_moves(self) -> list[int]:
        """Copy of the playable cells; empty once the game is over.

        The order is unspecified and changes with make/unmake of other moves.
        """
        return [] if self.winner != EMPTY else self._empties[:]

    def candidate_moves(self, radius: int) -> list[int]:
        """Empty cells within Chebyshev distance `radius` of any stone.

        Returns the centre cell on an empty board and an empty list once the
        game is over. Order is unspecified. The first call for a given radius
        builds a counter structure that make/unmake then maintain in
        O(radius^2) per move, so untouched radii cost nothing.

        Raises:
            ValueError: If `radius` < 1.
        """
        if radius < 1:
            raise ValueError("radius must be >= 1")
        if self.is_terminal:
            return []
        if len(self._empties) == self._size:
            return [(self.n // 2) * self.n + self.n // 2]
        tracker = self._trackers.get(radius)
        if tracker is None:
            tracker = _Neighbourhood(self.n, radius, self.cells_list)
            self._trackers[radius] = tracker
            self._tracker_list.append(tracker)
        return tracker.items[:]

    def _remove_empty(self, move: int) -> int:
        i = self._epos[move]
        last = self._empties.pop()
        if i < len(self._empties):
            self._empties[i] = last
            self._epos[last] = i
        self._epos[move] = -1
        return i

    def _restore_empty(self, move: int, i: int) -> None:
        empties = self._empties
        if i == len(empties):
            empties.append(move)
        else:
            displaced = empties[i]
            empties[i] = move
            empties.append(displaced)
            self._epos[displaced] = len(empties) - 1
        self._epos[move] = i

    def _place_raw(self, move: int, player: int) -> None:
        self.cells_list[move] = player
        self.cells[move] = player
        self._remove_empty(move)
        self._count[player] += 1
        self.hash ^= self._zob[0 if player == X else 1][move]

    def make(self, move: int) -> None:
        """Place the current player's stone at `move`.

        Raises:
            ValueError: If the move is off the board, the cell is occupied, or
                the game is over.
        """
        if self.winner != EMPTY:
            raise ValueError("game is already over")
        if not 0 <= move < self._size:
            raise ValueError(f"move {move} is off the board")
        cl = self.cells_list
        if cl[move] != EMPTY:
            raise ValueError(f"cell {move} is occupied")
        player = self.to_move
        cl[move] = player
        self.cells[move] = player
        self._eidx.append(self._remove_empty(move))
        self._history.append(move)
        self.hash ^= self._zob[0 if player == X else 1][move]
        for tracker in self._tracker_list:
            tracker.on_place(move, cl)
        self._count[player] += 1
        if self._count[player] >= self.config.k and wins_at(
            cl, self.config, move, player
        ):
            self.winner = player
        self.to_move = -player

    def unmake_move(self) -> int:
        """Undo the most recent `make` and return that move.

        Raises:
            IndexError: If there is no move to undo.
        """
        if not self._history:
            raise IndexError("no move to unmake")
        move = self._history.pop()
        cl = self.cells_list
        player = cl[move]
        cl[move] = EMPTY
        self.cells[move] = EMPTY
        self._restore_empty(move, self._eidx.pop())
        self.hash ^= self._zob[0 if player == X else 1][move]
        for tracker in self._tracker_list:
            tracker.on_remove(move, cl)
        self._count[player] -= 1
        self.winner = EMPTY
        self.to_move = player
        return move

    def result(self) -> int:
        """Outcome from X's view: +1 X won, -1 O won, 0 draw or unfinished."""
        return self.winner

    def copy(self, track_candidates: bool = False) -> Board:
        """Independent copy (for GUI/tournament use, not for search).

        Args:
            track_candidates: If True, the copy inherits this board's candidate
                counters. By default it carries none, so make/unmake on the copy
                does no counter work (they are rebuilt lazily on demand).
        """
        b = Board.__new__(Board)
        b.config, b.n, b._size = self.config, self.n, self._size
        b.cells = self.cells.copy()
        b.cells_list = self.cells_list[:]
        b.to_move, b.winner, b.hash = self.to_move, self.winner, self.hash
        b._history = self._history[:]
        b._empties = self._empties[:]
        b._epos = self._epos[:]
        b._eidx = self._eidx[:]
        b._count = self._count[:]
        b._zob = self._zob
        if track_candidates:
            b._trackers = {r: t.copy() for r, t in self._trackers.items()}
        else:
            b._trackers = {}
        b._tracker_list = list(b._trackers.values())
        return b

    def __str__(self) -> str:
        w = len(str(self.n - 1))
        lines = [" " * w + "  " + " ".join(f"{c:>{w}}" for c in range(self.n))]
        for r in range(self.n):
            row = self.cells_list[r * self.n : (r + 1) * self.n]
            lines.append(f"{r:>{w}}  " + " ".join(f"{_SYMBOL[v]:>{w}}" for v in row))
        return "\n".join(lines)
