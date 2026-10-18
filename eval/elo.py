"""Bradley-Terry maximum-likelihood Elo with bootstrap confidence intervals.

Model: P(i beats j) = g_i / (g_i + g_j), Elo_i = 400 log10(g_i) - Elo_anchor.
A draw counts as half a win for each side. The fit uses the MM iteration
(Zermelo / Hunter 2004). To keep the MLE finite for agents that never lost, every
pair of agents receives ``PRIOR`` virtual drawn games, which is negligible for
real sample sizes.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np

from eval.tournament import GameRecord

Game = tuple[str, str, float]
PRIOR = 0.1


def games_from_records(records: Iterable[GameRecord]) -> list[Game]:
    """Convert records to ``(agent_x, agent_o, score_of_x)`` triples."""
    return [(r.agent_x, r.agent_o, {1: 1.0, 0: 0.5, -1: 0.0}[r.result]) for r in records]


def fit_elo(games: Sequence[Game], anchor: str | None = "random") -> dict[str, float]:
    """Maximum-likelihood Elo ratings.

    Args:
        games: ``(a, b, score_a)`` with score_a in {0, 0.5, 1}.
        anchor: Agent whose rating is fixed to 0. If None or absent from the
            games, ratings are centred on their mean.

    Returns:
        Elo rating per agent.
    """
    names = sorted({x for g in games for x in g[:2]})
    idx = {n: i for i, n in enumerate(names)}
    m = len(names)
    wins = np.zeros(m)
    played = np.zeros((m, m))
    for a, b, s in games:
        i, j = idx[a], idx[b]
        wins[i] += s
        wins[j] += 1.0 - s
        played[i, j] += 1
        played[j, i] += 1
    off = PRIOR * (np.ones((m, m)) - np.eye(m))
    played = played + off
    wins = wins + 0.5 * off.sum(axis=1)
    g = np.ones(m)
    for _ in range(20000):
        denom = (played / (g[:, None] + g[None, :])).sum(axis=1)
        new = wins / denom
        new /= np.exp(np.log(new).mean())
        if np.max(np.abs(np.log(new) - np.log(g))) < 1e-12:
            g = new
            break
        g = new
    elo = 400.0 * np.log10(g)
    shift = elo[idx[anchor]] if anchor in idx else elo.mean()
    return {n: float(elo[idx[n]] - shift) for n in names}


def bootstrap_elo(
    games: Sequence[Game],
    anchor: str | None = "random",
    n_boot: int = 200,
    seed: int = 0,
) -> dict[str, tuple[float, float, float]]:
    """Point estimate and 95% percentile interval per agent.

    Games are resampled with replacement ``n_boot`` times and the model refitted.

    Returns:
        ``{agent: (rating, low, high)}``.
    """
    point = fit_elo(games, anchor)
    rng = np.random.default_rng(seed)
    n = len(games)
    samples: dict[str, list[float]] = {k: [] for k in point}
    for _ in range(n_boot):
        pick = rng.integers(0, n, size=n)
        fit = fit_elo([games[i] for i in pick], anchor)
        for k in point:
            if k in fit:
                samples[k].append(fit[k])
    out: dict[str, tuple[float, float, float]] = {}
    for k, rating in point.items():
        vals = samples[k]
        if len(vals) >= 2:
            lo, hi = np.percentile(vals, [2.5, 97.5])
            out[k] = (rating, float(lo), float(hi))
        else:
            out[k] = (rating, rating, rating)
    return out


def expected_score(rating_a: float, rating_b: float) -> float:
    """Model probability-equivalent score of a against b."""
    return float(1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0)))

