"""LaTeX (booktabs) tables for the report.

Run: python -m experiments.tables [--results results] [--out results/tables]

Writes solve.tex, ab_ablation.tex, mcts_ablation.tex, elo_ranking.tex and
puzzle_accuracy.tex for the data that exists.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np

from experiments.plots import Row, latest_runs, read_csv

_ESCAPES = {"_": r"\_", "%": r"\%", "&": r"\&", "#": r"\#"}


def esc(text: str) -> str:
    """Escape LaTeX special characters in table text."""
    return "".join(_ESCAPES.get(c, c) for c in str(text))


def latex_table(
    headers: list[str], rows: list[list[str]], caption: str, label: str, align: str | None = None
) -> str:
    """A booktabs table environment.

    Args:
        headers: Column titles.
        rows: Cell strings; they are escaped here.
        caption: Table caption (escaped).
        label: LaTeX label.
        align: Column spec; defaults to left for the first column, right for the rest.
    """
    spec = align or "l" + "r" * (len(headers) - 1)
    lines = [
        r"\begin{table}[ht]",
        r"\centering",
        rf"\begin{{tabular}}{{{spec}}}",
        r"\toprule",
        " & ".join(esc(h) for h in headers) + r" \\",
        r"\midrule",
    ]
    lines += [" & ".join(esc(c) for c in r) + r" \\" for r in rows]
    lines += [r"\bottomrule", r"\end{tabular}",
              rf"\caption{{{esc(caption)}}}", rf"\label{{{label}}}", r"\end{table}"]
    return "\n".join(lines) + "\n"


def solve_table(results_root: Path) -> str | None:
    """Exact solving results (results/solve.csv)."""
    f = results_root / "solve.csv"
    if not f.exists():
        return None
    rows = []
    for r in read_csv(f):
        value = {"1": "X wins", "0": "draw", "-1": "O wins"}.get(r["value"], "not solved")
        rows.append([f"{r['n']}x{r['n']}", r["k"], r["variant"],
                     "yes" if r["early_stop"] == "1" else "no", value,
                     f"{int(r['nodes']):,}", f"{float(r['time_s']):.1f}"])
    return latex_table(["board", "k", "memo", "early stop", "value", "nodes", "time (s)"], rows,
                       "Exact game values by full minimax.", "tab:solve")


def ab_ablation_table(runs: dict[str, Path]) -> str | None:
    """Mean nodes, time and cutoffs per AB preset at fixed depth."""
    if "ablation_ab" not in runs or not (runs["ablation_ab"] / "ab_depth.csv").exists():
        return None
    rows = read_csv(runs["ablation_ab"] / "ab_depth.csv")
    out = []
    for p in dict.fromkeys(r["preset"] for r in rows):
        sub = [r for r in rows if r["preset"] == p]
        out.append([p, f"{np.mean([float(r['nodes']) for r in sub]):,.0f}",
                    f"{np.mean([float(r['time_s']) for r in sub]):.2f}",
                    f"{np.mean([float(r['cutoffs']) for r in sub]):,.0f}",
                    f"{np.mean([float(r['tt_hits']) for r in sub]):,.0f}"])
    d = rows[0]["depth"]
    return latex_table(["preset", "nodes", "time (s)", "cutoffs", "TT hits"], out,
                       f"Alpha-beta ablation at depth {d} (mean over three 9x9 midgames).",
                       "tab:ab-ablation")


def _elo_rows(summary: list[Row], board: tuple[int, int], budget: float | None = None
              ) -> list[list[str]]:
    sub = [r for r in summary if (int(r["n"]), int(r["k"])) == board]
    b = budget if budget is not None else max(float(r["budget"]) for r in sub)
    sub = sorted((r for r in sub if float(r["budget"]) == b), key=lambda r: -float(r["elo"]))
    return [[str(i + 1), r["agent"], f"{float(r['elo']):.0f}",
             f"[{float(r['elo_lo']):.0f}, {float(r['elo_hi']):.0f}]",
             f"{float(r['score']):.2f}", f"{int(r['games'])}"] for i, r in enumerate(sub)]


def mcts_ablation_table(runs: dict[str, Path]) -> str | None:
    """Elo of every variant of the MCTS ablation."""
    if "ablation_mcts" not in runs:
        return None
    summ = read_csv(runs["ablation_mcts"] / "summary.csv")
    board = sorted({(int(r["n"]), int(r["k"])) for r in summ})[0]
    return latex_table(["rank", "variant", "Elo", "95\\% CI", "score", "games"],
                       _elo_rows(summ, board), "MCTS ablation (Elo against Random = 0).",
                       "tab:mcts-ablation")


def elo_table(runs: dict[str, Path]) -> str | None:
    """Elo ranking of the main tournament, one block per board at the largest budget."""
    if "main_tournament" not in runs:
        return None
    summ = read_csv(runs["main_tournament"] / "summary.csv")
    parts = []
    for board in sorted({(int(r["n"]), int(r["k"])) for r in summ}):
        sub = [r for r in summ if (int(r["n"]), int(r["k"])) == board]
        b = max(float(r["budget"]) for r in sub)
        parts.append(latex_table(
            ["rank", "agent", "Elo", "95\\% CI", "score", "games"], _elo_rows(summ, board),
            f"Elo ranking, {board[0]}x{board[0]} k={board[1]}, {b:g} s per move.",
            f"tab:elo-{board[0]}x{board[1]}"))
    return "\n".join(parts)


def puzzle_table(runs: dict[str, Path]) -> str | None:
    """Puzzle accuracy per agent and category."""
    if "main_tournament" not in runs or not (runs["main_tournament"] / "puzzles.csv").exists():
        return None
    rows = read_csv(runs["main_tournament"] / "puzzles.csv")
    acc: dict[str, dict[str, str]] = defaultdict(dict)
    for r in rows:
        acc[r["agent"]][r["category"]] = f"{float(r['accuracy']):.2f}"
    out = [[a, d["win_in_1"], d["block"], d["win_in_3"], d["all"]] for a, d in acc.items()]
    return latex_table(["agent", "win in 1", "block", "win in 3", "all"], out,
                       "Puzzle accuracy (30 positions).", "tab:puzzles")


def make_all(results_root: Path, out_dir: Path) -> list[Path]:
    """Write every table whose data exists; returns the files written."""
    runs = latest_runs(results_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    tables = {
        "solve": solve_table(results_root),
        "ab_ablation": ab_ablation_table(runs),
        "mcts_ablation": mcts_ablation_table(runs),
        "elo_ranking": elo_table(runs),
        "puzzle_accuracy": puzzle_table(runs),
    }
    written = []
    for name, text in tables.items():
        if text is None:
            print(f"{name}: skipped (no data)")
            continue
        p = out_dir / f"{name}.tex"
        p.write_text(text, encoding="utf-8")
        written.append(p)
        print(f"{name}: wrote {p}")
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=Path("results"))
    ap.add_argument("--out", type=Path, default=Path("results/tables"))
    args = ap.parse_args()
    make_all(args.results, args.out)


if __name__ == "__main__":
    main()
