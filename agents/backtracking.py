"""Plain minimax baseline: no pruning, no move ordering, no heuristic."""
from __future__ import annotations

from time import perf_counter

from agents.base import Agent, SearchStats
from core.board import Board

_WIN = 1_000_000
_CLOCK_MASK = 255


class _Timeout(Exception):
    pass


class BacktrackingAgent(Agent):
    """Exhaustive negamax over `legal_moves()`.

    This is the honest baseline: every legal move is expanded at every node, in
    whatever order `legal_moves()` returns them. A win at ply p scores
    `WIN - p` for the winner, so a faster win (or slower loss) is preferred;
    draws score 0.

    Args:
        max_depth: Search horizon in plies, or None to search to the end of the
            game. At the horizon the search returns 0 (a draw-like value)
            without any heuristic, so depth-limited play only sees forced
            results within the horizon.
        seed: Seed for the agent's private random generator.
    """

    def __init__(self, max_depth: int | None = None, seed: int = 0) -> None:
        super().__init__(seed)
        self.max_depth = max_depth
        self._stats = SearchStats()
        self._nodes = 0
        self._deepest = 0
        self._deadline = 0.0

    @property
    def name(self) -> str:
        return "Backtracking" if self.max_depth is None else f"Backtracking(d={self.max_depth})"

    def select_move(self, board: Board, time_budget_s: float) -> int:
        """Return the minimax-best move; on timeout the best fully searched one.

        If the budget runs out before any root move has been fully searched,
        the first legal move is returned. `extra["timed_out"]` is 1.0 then.

        Raises:
            ValueError: If the game is already over.
        """
        moves = board.legal_moves()
        if not moves:
            raise ValueError("no legal moves: game is over")
        t0 = perf_counter()
        self._deadline = t0 + time_budget_s
        self._nodes = 1
        self._deepest = 0
        best_move, best_score = moves[0], -2 * _WIN
        timed_out = False
        pushed = 0
        try:
            for m in moves:
                board.make(m)
                pushed += 1
                score = -self._negamax(board, 1)
                board.unmake_move()
                pushed -= 1
                if score > best_score:
                    best_move, best_score = m, score
        except _Timeout:
            timed_out = True
            if best_score == -2 * _WIN:
                best_move = moves[0]
        finally:
            for _ in range(pushed):
                board.unmake_move()
        self._stats = SearchStats(
            nodes=self._nodes,
            time_s=perf_counter() - t0,
            depth_reached=self._deepest,
            extra={"timed_out": 1.0 if timed_out else 0.0, "score": float(best_score)},
        )
        return best_move

    def _negamax(self, board: Board, ply: int) -> int:
        self._nodes += 1
        if not self._nodes & _CLOCK_MASK and perf_counter() > self._deadline:
            raise _Timeout
        if ply > self._deepest:
            self._deepest = ply
        if board.winner:
            return -(_WIN - ply)
        if self.max_depth is not None and ply >= self.max_depth:
            return 0
        moves = board.legal_moves()
        if not moves:
            return 0
        best = -2 * _WIN
        for m in moves:
            board.make(m)
            try:
                score = -self._negamax(board, ply + 1)
            finally:
                board.unmake_move()
            if score > best:
                best = score
        return best

    def last_stats(self) -> SearchStats:
        return self._stats
