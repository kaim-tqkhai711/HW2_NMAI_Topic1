"""Confidence intervals and outcome summaries for game results."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from math import sqrt

from eval.tournament import GameRecord


def wilson_ci(successes: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a proportion.

    Args:
        successes: Number of successes; may be fractional (a draw counts 0.5).
        n: Number of trials.
        z: Normal quantile (1.96 for 95%).

    Returns:
        (low, high); (0.0, 1.0) when n is 0.
    """
    if n <= 0:
        return 0.0, 1.0
    p = successes / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


@dataclass(frozen=True)
class Outcome:
    """Win/draw/loss tally from one side's point of view.

    Attributes:
        wins: Games won.
        draws: Games drawn.
        losses: Games lost.
        score: (wins + draws / 2) / games.
        ci: Wilson 95% interval of ``score`` with draws counted as half a win.
    """

    wins: int
    draws: int
    losses: int
    score: float
    ci: tuple[float, float]

    @property
    def games(self) -> int:
        return self.wins + self.draws + self.losses


def outcome(wins: int, draws: int, losses: int) -> Outcome:
    """Build an `Outcome` from counts."""
    n = wins + draws + losses
    s = wins + 0.5 * draws
    return Outcome(wins, draws, losses, s / n if n else 0.0, wilson_ci(s, n))


def head_to_head(records: Iterable[GameRecord], a: str, b: str) -> Outcome:
    """Result of agent ``a`` against ``b`` over all their games, from a's view."""
    w = d = l = 0
    for r in records:
        if {r.agent_x, r.agent_o} != {a, b}:
            continue
        if r.result == 0:
            d += 1
        elif (r.result == 1) == (r.agent_x == a):
            w += 1
        else:
            l += 1
    return outcome(w, d, l)


def first_move_win_rate(records: Iterable[GameRecord]) -> dict[str, Outcome]:
    """First-player (X) outcome per game configuration, keyed ``"NxN k=K"``.

    The score is X's, with draws as half; ``wins`` are X wins.
    """
    tally: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for r in records:
        c = r.config
        key = f"{c['n']}x{c['n']} k={c['k']}" + (" exact" if c.get("exact_k") else "")
        tally[key][0 if r.result == 1 else 1 if r.result == 0 else 2] += 1
    return {k: outcome(*v) for k, v in sorted(tally.items())}
