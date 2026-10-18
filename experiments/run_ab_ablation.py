"""Alpha-beta ablation table: each preset on three fixed 9x9 k=5 midgames at depth 4.

Run: python -m experiments.run_ab_ablation [--depth 4] [--budget 600]

Columns: nodes, time, cutoffs, and the value/move found (identical values across
presets with candidate_radius=None are the correctness check; AB_FULL restricts
moves to a radius-2 neighbourhood and may differ).
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import replace
from pathlib import Path
from typing import Any

from agents.alphabeta import AlphaBetaAgent
from agents.presets import AB_PRESETS
from core.board import Board
from tests.positions import midgame_positions_95

FIELDS = ["preset", "position", "depth", "nodes", "time_s", "cutoffs",
          "tt_hits", "ebf", "score", "move", "timed_out"]


def measure(
    depth: int, budget: float, boards: list[Board] | None = None, verbose: bool = False
) -> list[dict[str, Any]]:
    """Run every AB preset at ``depth`` on each board and return one row per run."""
    boards = boards if boards is not None else midgame_positions_95()
    rows: list[dict[str, Any]] = []
    for name, cfg in AB_PRESETS.items():
        for i, b in enumerate(boards):
            agent = AlphaBetaAgent(replace(cfg, max_depth=depth))
            move = agent.select_move(b, budget)
            st = agent.last_stats()
            x = st.extra
            rows.append({
                "preset": name, "position": i, "depth": depth, "nodes": st.nodes,
                "time_s": round(st.time_s, 3), "cutoffs": int(x["cutoffs"]),
                "tt_hits": int(x["tt_hits"]), "ebf": round(x["ebf"], 2),
                "score": int(x["score"]), "move": move, "timed_out": int(x["timed_out"]),
            })
            if verbose:
                r = rows[-1]
                print(f"{name:15s} pos{i} nodes={r['nodes']:8d} t={r['time_s']:6.2f}s "
                      f"cut={r['cutoffs']} score={r['score']} move={move}", flush=True)
    return rows


def write_rows(rows: list[dict[str, Any]], path: Path) -> None:
    """Write measurement rows as CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--budget", type=float, default=600.0)
    ap.add_argument("--out", type=Path, default=Path("results/ab_ablation.csv"))
    args = ap.parse_args()
    write_rows(measure(args.depth, args.budget, verbose=True), args.out)


if __name__ == "__main__":
    main()
