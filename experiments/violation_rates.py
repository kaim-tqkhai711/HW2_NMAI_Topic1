"""Per-agent, per-board rate of moves that exceeded 1.5 x the time budget.

Computed from the wall time of every move in ``games.jsonl`` (not from the
``violations`` counters), so it also works on records written by older code.

Usage:
    python -m experiments.violation_rates results/pilot_main/pilot2 [--md]
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from eval.tournament import VIOLATION_FACTOR, GameRecord, read_records


def violation_table(records: list[GameRecord]) -> dict[tuple[int, str], tuple[int, int, float]]:
    """Map (board size, agent) to (moves, over-budget moves, max wall / budget)."""
    acc: dict[tuple[int, str], list[float]] = defaultdict(lambda: [0, 0, 0.0])
    for r in records:
        if r.budget_mode != "time":
            continue
        for i, m in enumerate(r.moves):
            who = r.agent_x if (len(r.opening) + i) % 2 == 0 else r.agent_o
            a = acc[(r.config["n"], who)]
            ratio = m.wall_s / r.time_budget_s
            a[0] += 1
            a[1] += ratio > VIOLATION_FACTOR
            a[2] = max(a[2], ratio)
    return {k: (int(v[0]), int(v[1]), v[2]) for k, v in acc.items()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--md", action="store_true", help="print a Markdown table")
    args = ap.parse_args(argv)
    table = violation_table(read_records(args.run_dir / "games.jsonl"))
    sizes = sorted({n for n, _ in table})
    agents = sorted({a for _, a in table})
    worst = 0.0
    head = ["agent"] + [f"{n}x{n} viol %" for n in sizes] + [f"{n}x{n} max x" for n in sizes]
    rows = []
    for a in agents:
        cells, maxes = [], []
        for n in sizes:
            moves, bad, mx = table.get((n, a), (0, 0, 0.0))
            rate = 100.0 * bad / moves if moves else 0.0
            worst = max(worst, rate)
            cells.append(f"{rate:.2f}")
            maxes.append(f"{mx:.2f}")
        rows.append([a] + cells + maxes)
    sep = " | " if args.md else "  "
    for r in [head] + rows:
        line = sep.join(r)
        print(f"| {line} |" if args.md else line)
        if args.md and r is head:
            print("|" + "---|" * len(head))
    print(f"worst rate: {worst:.2f} %", file=sys.stderr)
    return 0 if worst < 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
