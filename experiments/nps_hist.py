"""Histogram of nodes (or simulations) per second per move, 9x9 k=5 at 0.5 s.

Three agents side by side. Only each agent's first three moves of a game count (same board
size; pooling every move would mix game phases) and only moves that used at least 0.25 s of
the 0.5 s budget (so that early-stopped searches do not dilute the speed estimate).

Run: python -m experiments.nps_hist [--run results/main_9x9/full] [--out results/figures]
Writes nps_hist_9x9_0.5.{png,pdf} and prints n and p5 / p50 / p95 per agent.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from numpy.typing import NDArray  # noqa: E402

from eval.tournament import GameRecord, games_file, read_records  # noqa: E402
from experiments.plots import PALETTE  # noqa: E402

BUDGET_S = 0.5
AGENTS = ("ab_order_id_tt", "mcts_eval", "mcts_random")
FIRST_MOVES = 3
MIN_WALL_S = 0.25
BINS = 70
NAME = "nps_hist_9x9_0.5"


def collect(records: list[GameRecord], agent: str, budget_s: float = BUDGET_S,
            first_moves: int = FIRST_MOVES, min_wall_s: float = MIN_WALL_S) -> NDArray[np.float64]:
    """``nodes_per_s`` of the agent's first ``first_moves`` moves per game that took >= ``min_wall_s``."""
    out: list[float] = []
    for r in records:
        if r.budget_mode != "time" or abs(r.time_budget_s - budget_s) > 1e-9:
            continue
        seen = 0
        for i, m in enumerate(r.moves):
            who = r.agent_x if (len(r.opening) + i) % 2 == 0 else r.agent_o
            if who != agent:
                continue
            seen += 1
            if seen > first_moves:
                break
            if m.wall_s >= min_wall_s:
                out.append(m.nodes_per_s)
    return np.array(out, dtype=float)


def plot(records: list[GameRecord], out_dir: Path) -> list[Path]:
    """Draw the figure; returns the written files."""
    fig, axes = plt.subplots(1, len(AGENTS), figsize=(12, 3.4))
    for ax, agent in zip(axes, AGENTS):
        v = collect(records, agent)
        ax.hist(v, bins=BINS, color=PALETTE[0])
        ax.set_title(f"{agent}, agent moves 1-{FIRST_MOVES} (n={len(v):,})", fontsize=9)
        ax.set_xlabel("nodes/s per move")
        if len(v):
            p5, p50, p95 = np.percentile(v, [5, 50, 95])
            print(f"{agent}: n={len(v)} p5/p50/p95 = {p5:.0f} / {p50:.0f} / {p95:.0f}")
    axes[0].set_ylabel("moves")
    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in ("png", "pdf"):
        p = out_dir / f"{NAME}.{ext}"
        fig.savefig(p, dpi=150, metadata={"CreationDate": None} if ext == "pdf" else None)
        paths.append(p)
    plt.close(fig)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, default=Path("results/main_9x9/full"))
    ap.add_argument("--out", type=Path, default=Path("results/figures"))
    args = ap.parse_args()
    records = read_records(games_file(args.run))
    if not records:
        print(f"nps_hist: skipped (no games in {args.run})")
        return
    print("wrote", ", ".join(p.name for p in plot(records, args.out)))


if __name__ == "__main__":
    main()
