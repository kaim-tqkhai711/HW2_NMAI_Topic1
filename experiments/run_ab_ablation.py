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

from agents.alphabeta import AlphaBetaAgent
from agents.presets import AB_PRESETS
from tests.positions import midgame_positions_95


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--budget", type=float, default=600.0)
    ap.add_argument("--out", type=Path, default=Path("results/ab_ablation.csv"))
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    boards = midgame_positions_95()
    with args.out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["preset", "position", "depth", "nodes", "time_s", "cutoffs",
                    "tt_hits", "ebf", "score", "move", "timed_out"])
        for name, cfg in AB_PRESETS.items():
            for i, b in enumerate(boards):
                agent = AlphaBetaAgent(replace(cfg, max_depth=args.depth))
                move = agent.select_move(b, args.budget)
                st = agent.last_stats()
                x = st.extra
                print(f"{name:15s} pos{i} nodes={st.nodes:8d} t={st.time_s:6.2f}s "
                      f"cut={x['cutoffs']:.0f} score={x['score']:.0f} move={move}", flush=True)
                w.writerow([name, i, args.depth, st.nodes, f"{st.time_s:.3f}",
                            int(x["cutoffs"]), int(x["tt_hits"]), f"{x['ebf']:.2f}",
                            int(x["score"]), move, int(x["timed_out"])])


if __name__ == "__main__":
    main()
