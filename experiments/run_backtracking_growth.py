"""Node explosion of depth-limited plain backtracking on an empty 7x7 (k=4) board.

Run: python -m experiments.run_backtracking_growth [--limit 60] [--max-depth 12]
"""
from __future__ import annotations

import argparse
import csv
from math import prod
from pathlib import Path

from agents.backtracking import BacktrackingAgent
from core.board import Board
from core.rules import GameConfig


def leaf_bound(n: int, d: int) -> int:
    """Number of move sequences of length d: prod_{i<d} (n^2 - i)."""
    return prod(n * n - i for i in range(d))


def node_bound(n: int, d: int) -> int:
    """Upper bound on nodes visited by a depth-d search, root included."""
    return sum(leaf_bound(n, j) for j in range(d + 1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=float, default=60.0, help="per-call seconds")
    ap.add_argument("--max-depth", type=int, default=12)
    ap.add_argument("--out", type=Path, default=Path("results/backtracking_growth.csv"))
    args = ap.parse_args()
    n = 7
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n", "k", "depth", "nodes", "time_s", "timed_out",
                    "bound_sequences", "bound_nodes"])
        for d in range(1, args.max_depth + 1):
            agent = BacktrackingAgent(max_depth=d)
            agent.select_move(Board(GameConfig(n, 4)), args.limit)
            st = agent.last_stats()
            timed_out = int(st.extra["timed_out"])
            print(f"depth {d}: nodes={st.nodes} t={st.time_s:.2f}s timed_out={timed_out}")
            w.writerow([n, 4, d, st.nodes, f"{st.time_s:.3f}", timed_out,
                        leaf_bound(n, d), node_bound(n, d)])
            f.flush()
            if timed_out or st.time_s > args.limit:
                break


if __name__ == "__main__":
    main()
