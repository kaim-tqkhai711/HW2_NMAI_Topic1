"""Common agent interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np

from core.board import Board


@dataclass
class SearchStats:
    """Statistics of one `select_move` call.

    Attributes:
        nodes: Search nodes (or simulations) expanded.
        time_s: Wall-clock seconds spent.
        depth_reached: Deepest completed search depth, None if not applicable.
        extra: Agent-specific numeric counters (e.g. TT hits, root visits).
    """

    nodes: int = 0
    time_s: float = 0.0
    depth_reached: int | None = None
    extra: dict[str, float] = field(default_factory=dict)


class Agent(ABC):
    """A player that picks a move for the side to move.

    Args:
        seed: Seed for the agent's private random generator.
    """

    def __init__(self, seed: int = 0) -> None:
        self.rng = np.random.default_rng(seed)

    @property
    def name(self) -> str:
        """Display name used in tournaments and plots."""
        return type(self).__name__

    @abstractmethod
    def select_move(self, board: Board, time_budget_s: float) -> int:
        """Return a legal flat move index within roughly `time_budget_s` seconds.

        The board must be returned unmodified. The budget is per call, so one
        instance can be used with different budgets.
        """

    @abstractmethod
    def last_stats(self) -> SearchStats:
        """Statistics of the most recent `select_move` call."""
