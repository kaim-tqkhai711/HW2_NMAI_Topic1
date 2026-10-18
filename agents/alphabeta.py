"""Alpha-beta search with independently switchable enhancements.

The scoring convention is negamax with ``WIN_SCORE - ply`` for a win at ply
``ply``. A depth-0 node returns the static evaluation, so "depth d" means d plies
of lookahead and the same horizon as `BacktrackingAgent(max_depth=d)`.

`ABConfig.move_ordering` enables everything that is about *which* moves are
looked at first or at all: TT-move/killer/heuristic ordering and the
immediate-threat logic (a side with a winning move returns it at once; if the
opponent threatens exactly one win the only move is the block; two distinct
threats are a lost position). These shortcuts only fire where the horizon lets
plain minimax see the same result, so they never change the minimax value.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from time import perf_counter

from agents.base import Agent, SearchStats
from agents.evaluation import EvalWeights, IncrementalEval
from core.board import Board
from core.rules import EMPTY, X, wins_at

WIN_SCORE = 1_000_000
_MATE = WIN_SCORE - 1000
_INF = 10 * WIN_SCORE
_CLOCK_MASK = 127
_EXACT, _LOWER, _UPPER = 0, 1, 2


@dataclass(frozen=True)
class ABConfig:
    """Switches and limits of `AlphaBetaAgent`.

    Attributes:
        move_ordering: TT-move / killer / heuristic ordering plus immediate
            win and block detection.
        iterative_deepening: Search depths 1..max_depth and keep the last
            completed one; otherwise search max_depth directly.
        transposition_table: Cache results by Zobrist hash.
        candidate_radius: Only consider empty cells within this Chebyshev
            distance of a stone; None considers every legal move.
        max_depth: Plies of lookahead (a cap when iterative deepening is on).
        killer_moves: Two killer moves per ply (effective with move_ordering).
        tt_size: Maximum number of TT entries (the table is cleared per call).
    """

    move_ordering: bool
    iterative_deepening: bool
    transposition_table: bool
    candidate_radius: int | None
    max_depth: int
    killer_moves: bool = False
    tt_size: int = 2**20


class _Timeout(Exception):
    pass


@lru_cache(maxsize=None)
def window_table(n: int, k: int) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    wins: list[tuple[int, ...]] = []
    for r in range(n):
        for c in range(n):
            for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                er, ec = r + (k - 1) * dr, c + (k - 1) * dc
                if 0 <= er < n and 0 <= ec < n:
                    wins.append(tuple((r + i * dr) * n + c + i * dc for i in range(k)))
    through: list[list[int]] = [[] for _ in range(n * n)]
    for wid, cells in enumerate(wins):
        for c in cells:
            through[c].append(wid)
    return tuple(wins), tuple(tuple(t) for t in through)


class WindowTracker:
    """Per-window stone counts, with the sets of windows one stone short of k.

    Also used by the MCTS heuristic rollout. Call `place(move, player, +1)`
    after a stone is placed and `place(move, player, -1)` after it is removed;
    the tracker reads the board's live `cells_list` and never writes it.

    Args:
        board: Board whose current stones initialise the counters.
    """

    def __init__(self, board: Board) -> None:
        self.config = board.config
        n, self.k = board.n, board.config.k
        self.cells = board.cells_list
        self.wins, self.through = window_table(n, self.k)
        self.cx = [0] * len(self.wins)
        self.co = [0] * len(self.wins)
        for m, v in enumerate(self.cells):
            if v != EMPTY:
                for w in self.through[m]:
                    if v == X:
                        self.cx[w] += 1
                    else:
                        self.co[w] += 1
        self.tx = {w for w in range(len(self.wins)) if self._short(self.cx[w], self.co[w])}
        self.to = {w for w in range(len(self.wins)) if self._short(self.co[w], self.cx[w])}

    def _short(self, mine: int, theirs: int) -> bool:
        return mine == self.k - 1 and theirs == 0

    def place(self, move: int, player: int, sign: int) -> None:
        """Account for a stone added (sign=+1) or removed (sign=-1) at `move`."""
        cx, co, tx, to, k = self.cx, self.co, self.tx, self.to, self.k
        arr = cx if player == X else co
        for w in self.through[move]:
            arr[w] += sign
            if cx[w] == k - 1 and co[w] == 0:
                tx.add(w)
            else:
                tx.discard(w)
            if co[w] == k - 1 and cx[w] == 0:
                to.add(w)
            else:
                to.discard(w)


    def winning_cells(self, player: int) -> list[int]:
        """Sorted empty cells where `player` would complete a winning line."""
        cl = self.cells
        cfg = self.config
        cells: set[int] = set()
        for w in self.tx if player == X else self.to:
            for c in self.wins[w]:
                if cl[c] == EMPTY:
                    if cfg.exact_k:
                        cl[c] = player
                        ok = wins_at(cl, cfg, c, player)
                        cl[c] = EMPTY
                        if not ok:
                            continue
                    cells.add(c)
                    break
        return sorted(cells)


class AlphaBetaAgent(Agent):
    """Fail-soft negamax alpha-beta; see `ABConfig` for the enhancements.

    Args:
        config: Search configuration.
        seed: Seed for the agent's private random generator (unused by the
            deterministic search, kept for interface uniformity).
        weights: Evaluation weights; defaults to `EvalWeights.default(k)`.
    """

    def __init__(
        self, config: ABConfig, seed: int = 0, weights: EvalWeights | None = None
    ) -> None:
        super().__init__(seed)
        self.config = config
        self.weights = weights
        self._stats = SearchStats()
        self._pv: list[int] = []

    @property
    def name(self) -> str:
        return f"AlphaBeta(d={self.config.max_depth})"

    def last_pv(self) -> list[int]:
        """Principal variation (flat moves) of the last completed iteration."""
        return self._pv[:]

    def last_stats(self) -> SearchStats:
        return self._stats

    def select_move(self, board: Board, time_budget_s: float) -> int:
        """Return the best move found within the budget.

        With iterative deepening a running iteration is aborted on timeout and
        the best move of the last completed depth is returned. If not even
        depth 1 completes, the heuristically first move is returned.
        `extra["score"]` is the value of the last completed search.

        Raises:
            ValueError: If the game is already over.
        """
        if not board.legal_moves():
            raise ValueError("no legal moves: game is over")
        cfg = self.config
        t0 = perf_counter()
        self._deadline = t0 + time_budget_s
        self._board = board
        self._ev = IncrementalEval(board.cells_list, board.config, self.weights)
        self._win: WindowTracker | None = WindowTracker(board) if cfg.move_ordering else None
        self._tt: dict[int, tuple[int, int, int, int]] = {}
        self._killers: list[list[int]] = [[-1, -1] for _ in range(cfg.max_depth + 4)]
        self._nodes = self._tt_hits = self._cutoffs = 0
        self._root_move = -1
        self._pv_tab: list[list[int]] = [[] for _ in range(cfg.max_depth + 4)]

        best_move = self._fallback_move(board)
        score = 0
        completed = 0
        timed_out = False
        last_depth = min(cfg.max_depth, board.n_empty)
        depths = range(1, last_depth + 1) if cfg.iterative_deepening else [last_depth]
        try:
            for d in depths:
                score = self._search(d, -_INF, _INF, 0)
                best_move, completed = self._root_move, d
                self._pv = self._pv_tab[0][:]
                if abs(score) >= _MATE:
                    break
        except _Timeout:
            timed_out = True
        elapsed = perf_counter() - t0
        ebf = self._nodes ** (1.0 / completed) if completed else 0.0
        self._stats = SearchStats(
            nodes=self._nodes,
            time_s=elapsed,
            depth_reached=completed or None,
            extra={
                "tt_hits": float(self._tt_hits),
                "cutoffs": float(self._cutoffs),
                "ebf": ebf,
                "score": float(score),
                "timed_out": 1.0 if timed_out else 0.0,
            },
        )
        return best_move

    def _fallback_move(self, board: Board) -> int:
        moves = self._moves(board) or board.legal_moves()
        if self._win is not None and len(moves) > 1:
            moves.sort(key=lambda m: (-self._local(m, board.to_move), m))
        return moves[0]

    def _moves(self, board: Board) -> list[int]:
        r = self.config.candidate_radius
        return board.legal_moves() if r is None else board.candidate_moves(r)

    def _local(self, move: int, player: int) -> int:
        win = self._win
        assert win is not None
        ww = self._ev.w.window
        mine, theirs = (win.cx, win.co) if player == X else (win.co, win.cx)
        score = 0
        for w in win.through[move]:
            a, b = mine[w], theirs[w]
            if b == 0:
                score += ww[a + 1] - ww[a]
            if a == 0:
                score += ww[b + 1] - ww[b]
        return score

    def _winning_cells(self, player: int) -> list[int]:
        win = self._win
        assert win is not None
        return win.winning_cells(player)

    def _search(self, depth: int, alpha: int, beta: int, ply: int) -> int:
        self._nodes += 1
        if not self._nodes & _CLOCK_MASK and perf_counter() > self._deadline:
            raise _Timeout
        board = self._board
        if board.winner:
            return -(WIN_SCORE - ply)
        if board.n_empty == 0:
            return 0
        if depth <= 0:
            return self._ev.value(board.to_move)
        cfg = self.config
        pv = self._pv_tab
        pv[ply] = []
        alpha0 = alpha
        tt_move = -1
        key = board.hash
        if cfg.transposition_table:
            entry = self._tt.get(key)
            if entry is not None:
                e_depth, e_val, e_flag, tt_move = entry
                if e_depth >= depth and ply > 0:
                    if e_val >= _MATE:
                        e_val -= ply
                    elif e_val <= -_MATE:
                        e_val += ply
                    if e_flag == _EXACT:
                        self._tt_hits += 1
                        return e_val
                    if e_flag == _LOWER and e_val > alpha:
                        alpha = e_val
                    elif e_flag == _UPPER and e_val < beta:
                        beta = e_val
                    if alpha >= beta:
                        self._tt_hits += 1
                        return e_val

        moves = self._moves(board) or board.legal_moves()
        if cfg.move_ordering:
            player = board.to_move
            mine = self._winning_cells(player)
            if mine:
                if ply == 0:
                    self._root_move = mine[0]
                pv[ply] = [mine[0]]
                return WIN_SCORE - (ply + 1)
            theirs = self._winning_cells(-player)
            if theirs and depth >= 2:
                if ply == 0:
                    self._root_move = theirs[0]
                if len(theirs) > 1:
                    pv[ply] = [theirs[0]]
                    return -(WIN_SCORE - (ply + 2))
                moves = theirs
            else:
                moves = self._order(moves, tt_move, ply, player)

        best = -_INF
        best_move = moves[0]
        for m in moves:
            board.make(m)
            self._ev.push(m)
            if self._win is not None:
                self._win.place(m, -board.to_move, 1)
            try:
                v = -self._search(depth - 1, -beta, -alpha, ply + 1)
            finally:
                if self._win is not None:
                    self._win.place(m, -board.to_move, -1)
                self._ev.pop()
                board.unmake_move()
            if v > best:
                best, best_move = v, m
                if v > alpha:
                    alpha = v
                    pv[ply] = [m] + pv[ply + 1]
                    if ply == 0:
                        self._root_move = m
                    if alpha >= beta:
                        self._cutoffs += 1
                        if cfg.killer_moves and cfg.move_ordering:
                            k = self._killers[ply]
                            if k[0] != m:
                                k[1], k[0] = k[0], m
                        break
        if cfg.transposition_table:
            flag = _EXACT
            if best <= alpha0:
                flag = _UPPER
            elif best >= beta:
                flag = _LOWER
            stored = best
            if stored >= _MATE:
                stored += ply
            elif stored <= -_MATE:
                stored -= ply
            old = self._tt.get(key)
            if old is None:
                if len(self._tt) < cfg.tt_size:
                    self._tt[key] = (depth, stored, flag, best_move)
            elif depth >= old[0]:
                self._tt[key] = (depth, stored, flag, best_move)
        return best

    def _order(self, moves: list[int], tt_move: int, ply: int, player: int) -> list[int]:
        scored = sorted(moves, key=lambda m: (-self._local(m, player), m))
        front: list[int] = []
        if self.config.killer_moves:
            front = [m for m in self._killers[ply] if m in scored]
        if tt_move >= 0 and tt_move in scored:
            front = [tt_move] + [m for m in front if m != tt_move]
        if not front:
            return scored
        fs = set(front)
        return front + [m for m in scored if m not in fs]
