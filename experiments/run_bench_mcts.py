"""MCTS simulations per second: rollout variants and hybrids on 9x9 and 11x11 (k=5).

Run: python -m experiments.run_bench_mcts [--seconds 3] [--out results/bench_mcts.csv]

The measured position is an opening with a few central stones, so that tree
expansion, candidate tracking and rollouts all have realistic work to do.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from agents.presets import AGENT_REGISTRY
from core.board import Board
from core.rules import GameConfig

SIZES = [9, 11]
VARIANTS = {
    "random": "mcts_random",
    "heuristic": "mcts_heuristic",
    "heuristic+rave": "mcts_rave",
    "eval (hybrid)": "mcts_eval",
    "ab-leaf (hybrid)": "mcts_ab",
}


def opening(n: int) -> Board:
    """Four central stones (X, O, X, O) on an n x n, k=5 board."""
    b = Board(GameConfig(n, 5))
    c = n // 2
    for r, col in [(c, c), (c, c + 1), (c - 1, c), (c + 1, c + 1)]:
        b.make(b.from_rc(r, col))
    return b


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--out", type=Path, default=Path("results/bench_mcts.csv"))
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n", "k", "config", "sims", "time_s", "sims_per_s", "max_tree_depth"])
        for n in SIZES:
            for name, key in VARIANTS.items():
                agent = AGENT_REGISTRY[key](0)
                agent.select_move(opening(n), args.seconds)
                st = agent.last_stats()
                print(f"{n}x{n} {name:17s} {st.nodes:7d} sims in {st.time_s:.2f}s "
                      f"= {st.extra['sims_per_s']:.0f} sims/s", flush=True)
                w.writerow([n, 5, name, st.nodes, f"{st.time_s:.3f}",
                            f"{st.extra['sims_per_s']:.1f}", int(st.extra["max_tree_depth"])])


if __name__ == "__main__":
    main()
