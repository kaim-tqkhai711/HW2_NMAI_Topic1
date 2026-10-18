"""Uniformly random baseline agent."""
from __future__ import annotations

from time import perf_counter

from agents.base import Agent, SearchStats
from core.board import Board


class RandomAgent(Agent):
    """Plays a uniformly random legal move; ignores the time budget."""

    def __init__(self, seed: int = 0) -> None:
        super().__init__(seed)
        self._stats = SearchStats()

    def select_move(self, board: Board, time_budget_s: float) -> int:
        """Pick a uniformly random legal move.

        Raises:
            ValueError: If the game is already over.
        """
        t0 = perf_counter()
        moves = board.legal_moves()
        if not moves:
            raise ValueError("no legal moves: game is over")
        move = moves[int(self.rng.integers(len(moves)))]
        self._stats = SearchStats(nodes=0, time_s=perf_counter() - t0)
        return move

    def last_stats(self) -> SearchStats:
        return self._stats
