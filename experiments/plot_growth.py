"""Node explosion of plain backtracking on 7x7 k=4 (log scale), against the closed form.

Reads ``results/backtracking_growth.csv`` (written by ``experiments.run_backtracking_growth``)
and draws the measured nodes per depth next to the closed-form upper bound
``sum_{j<=d} N^2 (N^2-1) ... (N^2-j+1)`` (root included). Depths that hit the time limit
are drawn hollow: their count is a lower bound on the full search.

Run: python -m experiments.plot_growth [--csv results/backtracking_growth.csv] [--out results/figures]
Writes node_explosion_7x7.{png,pdf}.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from experiments.plots import DPI, PALETTE  # noqa: E402
from experiments.run_backtracking_growth import node_bound  # noqa: E402

NAME = "node_explosion_7x7"
N = 7
MAX_FORMULA_DEPTH = 8


def plot(rows: list[dict[str, str]], out_dir: Path) -> list[Path]:
    """Draw the figure from CSV rows; returns the written files."""
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    depths = list(range(1, MAX_FORMULA_DEPTH + 1))
    ax.plot(depths, [node_bound(N, d) for d in depths], color=PALETTE[1], lw=1.4, ls="--",
            label="closed-form upper bound")
    done = [r for r in rows if r["timed_out"] == "0"]
    cut = [r for r in rows if r["timed_out"] == "1"]
    ax.plot([int(r["depth"]) for r in done], [int(r["nodes"]) for r in done], "o", color=PALETTE[0],
            label="measured (search completed)")
    ax.plot([int(r["depth"]) for r in cut], [int(r["nodes"]) for r in cut], "o", mfc="none",
            color=PALETTE[0], label="measured (time limit hit; lower bound)")
    ax.set_yscale("log")
    ax.set_xlabel("search depth (plies)")
    ax.set_ylabel("nodes visited")
    ax.set_title("Plain backtracking, 7x7 k=4")
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8)
    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in ("png", "pdf"):
        p = out_dir / f"{NAME}.{ext}"
        fig.savefig(p, dpi=DPI, metadata={"CreationDate": None} if ext == "pdf" else None)
        paths.append(p)
    plt.close(fig)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=Path("results/backtracking_growth.csv"))
    ap.add_argument("--out", type=Path, default=Path("results/figures"))
    args = ap.parse_args()
    if not args.csv.exists():
        print(f"plot_growth: skipped ({args.csv} not found)")
        return
    with args.csv.open(newline="") as f:
        rows = list(csv.DictReader(f))
    print("wrote", ", ".join(p.name for p in plot(rows, args.out)))


if __name__ == "__main__":
    main()
