"""Figures for the report (matplotlib, PDF + PNG at 300 dpi).

Run: python -m experiments.plots [--results results] [--out results/figures]

Each figure reads the latest run of the config it needs (see `latest_runs`) and
is skipped with a message if that run does not exist.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from numpy.typing import NDArray  # noqa: E402

from eval.stats import head_to_head  # noqa: E402
from eval.tournament import GameRecord, games_file, read_records  # noqa: E402

DPI = 300
# Okabe-Ito colour-blind-safe palette; markers disambiguate beyond eight series.
PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000",
           "#F0E442"]
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*", "<", ">"]
Row = dict[str, str]


def latest_runs(results_root: Path) -> dict[str, Path]:
    """Run directory (one containing summary.csv) per config name.

    A directory named ``full`` wins; otherwise the newest. Replicate runs such as
    ``full_w6_0.1`` are never picked over ``full``.
    """
    out: dict[str, Path] = {}
    if not results_root.exists():
        return out
    for cfg_dir in sorted(results_root.iterdir()):
        if not cfg_dir.is_dir():
            continue
        runs = sorted(d for d in cfg_dir.iterdir() if (d / "summary.csv").exists())
        if runs:
            out[cfg_dir.name] = next((d for d in runs if d.name == "full"), runs[-1])
    return out


def read_csv(path: Path) -> list[Row]:
    """Read a CSV into a list of string dicts."""
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _err(below: Any, above: Any) -> Any:
    """Asymmetric error bars as the 2 x N array matplotlib expects."""
    return np.vstack([np.asarray(below, dtype=float), np.asarray(above, dtype=float)])


def _style(names: list[str]) -> dict[str, tuple[str, str]]:
    return {n: (PALETTE[i % len(PALETTE)], MARKERS[i % len(MARKERS)]) for i, n in enumerate(names)}


def _save(fig: Any, name: str, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in ("pdf", "png"):
        p = out_dir / f"{name}.{ext}"
        fig.savefig(p, dpi=DPI, bbox_inches="tight")
        paths.append(p)
    plt.close(fig)
    return paths


MAIN_CONFIGS = ("main_7x7", "main_9x9", "main_11x11")


def main_summary(runs: dict[str, Path]) -> list[Row]:
    """summary.csv rows of every main-tournament config that has a run (Elo is per cell)."""
    return [r for c in MAIN_CONFIGS if c in runs for r in read_csv(runs[c] / "summary.csv")]


def main_records(runs: dict[str, Path]) -> list[GameRecord]:
    """All games of the main-tournament configs that have a run."""
    return [g for c in MAIN_CONFIGS if c in runs for g in read_records(games_file(runs[c]))]


def main_puzzles(runs: dict[str, Path]) -> list[Row]:
    """Puzzle accuracy rows (written by the config that ran with extras), or []."""
    return [r for c in MAIN_CONFIGS if c in runs and (runs[c] / "puzzles.csv").exists()
            for r in read_csv(runs[c] / "puzzles.csv")]


def _boards(rows: list[Row]) -> list[tuple[int, int]]:
    return sorted({(int(r["n"]), int(r["k"])) for r in rows})


def plot_elo_vs_budget(runs: dict[str, Path], out_dir: Path) -> list[Path]:
    """Elo of every agent against the per-move time budget, one panel per board."""
    rows = main_summary(runs)
    if not rows:
        return []
    boards = _boards(rows)
    agents = sorted({r["agent"] for r in rows})
    sty = _style(agents)
    fig, axes = plt.subplots(1, len(boards), figsize=(5.2 * len(boards), 4.2), squeeze=False)
    for ax, (n, k) in zip(axes[0], boards):
        for a in agents:
            pts = sorted((float(r["budget"]), float(r["elo"]), float(r["elo_lo"]),
                          float(r["elo_hi"])) for r in rows
                         if r["agent"] == a and (int(r["n"]), int(r["k"])) == (n, k))
            if not pts:
                continue
            x, y, lo, hi = (np.array(v) for v in zip(*pts))
            c, m = sty[a]
            ax.errorbar(x, y, yerr=_err(y - lo, hi - y), color=c, marker=m, ms=5, capsize=3,
                        lw=1.2, label=a)
        ax.set_xscale("log")
        ax.set_title(f"{n}x{n}, k={k}")
        ax.set_xlabel("time budget per move (s)")
        ax.set_ylabel("Elo (Random = 0)")
        ax.grid(alpha=0.3)
    axes[0][-1].legend(fontsize=7, loc="center left", bbox_to_anchor=(1.02, 0.5))
    return _save(fig, "elo_vs_budget", out_dir)


def plot_nodes_vs_depth(runs: dict[str, Path], out_dir: Path) -> list[Path]:
    """Nodes against search depth (log y) for backtracking and AB presets plus the bound."""
    if "ablation_ab" not in runs or not (runs["ablation_ab"] / "nodes_vs_depth.csv").exists():
        return []
    rows = read_csv(runs["ablation_ab"] / "nodes_vs_depth.csv")
    agents = list(dict.fromkeys(r["agent"] for r in rows))
    sty = _style(agents)
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    for a in agents:
        pts = [r for r in rows if r["agent"] == a]
        d = [int(r["depth"]) for r in pts]
        nodes = [max(1, int(r["nodes"])) for r in pts]
        c, m = sty[a]
        ax.plot(d, nodes, color=c, marker=m, lw=1.3, label=a)
        for r in pts:
            if int(r["timed_out"]):
                ax.plot(int(r["depth"]), max(1, int(r["nodes"])), marker=m, mfc="white",
                        mec=c, ms=9, ls="")
    bound = {int(r["depth"]): int(r["bound_sequences"]) for r in rows}
    ds = sorted(bound)
    ax.plot(ds, [bound[d] for d in ds], "k--", lw=1, label="bound  prod(N^2-i)")
    ax.set_yscale("log")
    ax.set_xticks(ds)
    ax.set_xlabel("search depth (plies)")
    ax.set_ylabel("nodes visited")
    ax.set_title("Node growth (hollow marker = hit the time cap)")
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8)
    return _save(fig, "nodes_vs_depth", out_dir)


def plot_scaling(runs: dict[str, Path], out_dir: Path) -> list[Path]:
    """Score of the best alpha-beta against each MCTS-family agent for N = 7, 9, 11."""
    if "scaling" not in runs:
        return []
    recs = read_records(games_file(runs["scaling"]))
    ab = "ab_full_timed"
    others = sorted({a for r in recs for a in (r.agent_x, r.agent_o)} - {ab, "random"})
    sizes = sorted({r.config["n"] for r in recs})
    sty = _style(others)
    fig, ax = plt.subplots(figsize=(5.2, 4.0))
    for j, o in enumerate(others):
        xs, ys, los, his = [], [], [], []
        for n in sizes:
            sub = [r for r in recs if r.config["n"] == n]
            h = head_to_head(sub, ab, o)
            if h.games:
                xs.append(n + 0.1 * (j - (len(others) - 1) / 2))
                ys.append(h.score)
                los.append(h.score - h.ci[0])
                his.append(h.ci[1] - h.score)
        c, m = sty[o]
        ax.errorbar(xs, ys, yerr=_err(los, his), color=c, marker=m, capsize=3, lw=1.2,
                    label=f"{ab} vs {o}")
    ax.axhline(0.5, color="grey", lw=0.8, ls=":")
    ax.set_xticks(sizes)
    ax.set_xlabel("board size N")
    ax.set_ylabel("alpha-beta score (draw = 0.5), Wilson 95% CI")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    return _save(fig, "scaling_winrate", out_dir)


def plot_ablation_ab(runs: dict[str, Path], out_dir: Path) -> list[Path]:
    """Nodes at fixed depth per AB preset, and Elo delta against AB_PLAIN."""
    if "ablation_ab" not in runs:
        return []
    run = runs["ablation_ab"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    f = run / "ab_depth.csv"
    if f.exists():
        rows = read_csv(f)
        presets = list(dict.fromkeys(r["preset"] for r in rows))
        mean = [np.mean([float(r["nodes"]) for r in rows if r["preset"] == p]) for p in presets]
        axes[0].bar(range(len(presets)), mean, color=PALETTE[0])
        axes[0].set_yscale("log")
        axes[0].set_xticks(range(len(presets)), presets, rotation=30, ha="right", fontsize=8)
        axes[0].set_ylabel(f"mean nodes at depth {rows[0]['depth']} (9x9 midgames)")
        axes[0].set_title("Search effort")
    summ = read_csv(run / "summary.csv")
    board = _boards(summ)[0]
    elo = {r["agent"]: float(r["elo"]) for r in summ if (int(r["n"]), int(r["k"])) == board}
    base = elo.get("ab_plain", min(elo.values()))
    names = [a for a in elo if a != "random"]
    axes[1].bar(range(len(names)), [elo[a] - base for a in names], color=PALETTE[1])
    axes[1].set_xticks(range(len(names)), names, rotation=30, ha="right", fontsize=8)
    axes[1].set_ylabel("Elo difference to ab_plain")
    axes[1].set_title("Playing strength at the tournament budget")
    axes[1].axhline(0, color="k", lw=0.8)
    for ax in axes:
        ax.grid(alpha=0.3, axis="y")
    return _save(fig, "ablation_ab", out_dir)


def plot_ablation_mcts(runs: dict[str, Path], out_dir: Path) -> list[Path]:
    """Elo (95% CI) of every MCTS variant of the ablation."""
    if "ablation_mcts" not in runs:
        return []
    summ = read_csv(runs["ablation_mcts"] / "summary.csv")
    board = _boards(summ)[0]
    rows = [r for r in summ if (int(r["n"]), int(r["k"])) == board and r["agent"] != "random"]
    fig, ax = plt.subplots(figsize=(6.5, 4))
    y = np.array([float(r["elo"]) for r in rows])
    lo = np.array([float(r["elo_lo"]) for r in rows])
    hi = np.array([float(r["elo_hi"]) for r in rows])
    ax.bar(range(len(rows)), y, yerr=_err(y - lo, hi - y), color=PALETTE[2], capsize=3)
    ax.set_xticks(range(len(rows)), [r["agent"] for r in rows], rotation=30, ha="right",
                  fontsize=8)
    ax.set_ylabel("Elo (Random = 0)")
    ax.set_title("MCTS ablation")
    ax.grid(alpha=0.3, axis="y")
    return _save(fig, "ablation_mcts", out_dir)


def plot_puzzles(runs: dict[str, Path], out_dir: Path) -> list[Path]:
    """Puzzle accuracy per agent and category."""
    rows = main_puzzles(runs)
    if not rows:
        return []
    agents = list(dict.fromkeys(r["agent"] for r in rows))
    cats = ["win_in_1", "block", "win_in_3"]
    fig, ax = plt.subplots(figsize=(9, 4))
    w = 0.8 / len(cats)
    for j, c in enumerate(cats):
        acc = [next(float(r["accuracy"]) for r in rows if r["agent"] == a and r["category"] == c)
               for a in agents]
        ax.bar(np.arange(len(agents)) + j * w, acc, w, label=c, color=PALETTE[j])
    ax.set_xticks(np.arange(len(agents)) + w, agents, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("accuracy")
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    return _save(fig, "puzzle_accuracy", out_dir)


def h2h_matrix(recs: list[GameRecord]) -> tuple[list[str], NDArray[np.float64]]:
    """Row-agent score (draw = 0.5) against column agent; NaN where no games."""
    agents = sorted({a for r in recs for a in (r.agent_x, r.agent_o)})
    m = np.full((len(agents), len(agents)), np.nan)
    for i, a in enumerate(agents):
        for j, b in enumerate(agents):
            if i != j:
                h = head_to_head(recs, a, b)
                if h.games:
                    m[i, j] = h.score
    order = np.argsort(-np.nan_to_num(m, nan=0.5).mean(axis=1))
    agents = [agents[i] for i in order]
    return agents, m[np.ix_(order, order)]


def plot_h2h_heatmap(runs: dict[str, Path], out_dir: Path) -> list[Path]:
    """Head-to-head score matrix on the first board, pooled over budgets."""
    recs = main_records(runs)
    if not recs:
        return []
    n0 = min(r.config["n"] for r in recs)
    agents, m = h2h_matrix([r for r in recs if r.config["n"] == n0])
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    im = ax.imshow(m, vmin=0, vmax=1, cmap="RdBu")
    ax.set_xticks(range(len(agents)), agents, rotation=60, ha="right", fontsize=7)
    ax.set_yticks(range(len(agents)), agents, fontsize=7)
    for i in range(len(agents)):
        for j in range(len(agents)):
            if not np.isnan(m[i, j]):
                ax.text(j, i, f"{m[i, j]:.2f}", ha="center", va="center", fontsize=6,
                        color="white" if abs(m[i, j] - 0.5) > 0.35 else "black")
    fig.colorbar(im, ax=ax, label="row agent's score vs column agent")
    ax.set_title(f"Head-to-head, {n0}x{n0}")
    return _save(fig, "h2h_heatmap", out_dir)


def spearman(a: list[float], b: list[float]) -> float:
    """Spearman rank correlation (no tie correction needed for the use here)."""
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def plot_budget_modes(runs: dict[str, Path], out_dir: Path) -> list[Path]:
    """Elo ranking under a time budget next to the ranking under a node budget."""
    t_rows = main_summary(runs)
    if not t_rows or "nodes_budget" not in runs:
        return []
    n_rows = read_csv(runs["nodes_budget"] / "summary.csv")
    board = _boards(t_rows)[0]

    def pick(rows: list[Row]) -> dict[str, tuple[float, float, float]]:
        sub = [r for r in rows if (int(r["n"]), int(r["k"])) == board]
        b = max(float(r["budget"]) for r in sub)
        return {r["agent"]: (float(r["elo"]), float(r["elo_lo"]), float(r["elo_hi"]))
                for r in sub if float(r["budget"]) == b}

    t, nd = pick(t_rows), pick(n_rows)
    common = sorted(set(t) & set(nd), key=lambda a: -t[a][0])
    rho = spearman([t[a][0] for a in common], [nd[a][0] for a in common])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    for ax, data, title in ((axes[0], t, "time budget"), (axes[1], nd, "node budget")):
        y = np.array([data[a][0] for a in common])
        lo = np.array([data[a][1] for a in common])
        hi = np.array([data[a][2] for a in common])
        ax.bar(range(len(common)), y, yerr=_err(y - lo, hi - y), color=PALETTE[0], capsize=2)
        ax.set_xticks(range(len(common)), common, rotation=60, ha="right", fontsize=7)
        ax.set_title(title)
        ax.grid(alpha=0.3, axis="y")
    axes[0].set_ylabel("Elo (Random = 0)")
    fig.suptitle(f"{board[0]}x{board[0]} k={board[1]}: ranking agreement "
                 f"(Spearman rho = {rho:.2f})")
    return _save(fig, "budget_modes", out_dir)


PLOTS = [plot_elo_vs_budget, plot_nodes_vs_depth, plot_scaling, plot_ablation_ab,
         plot_ablation_mcts, plot_puzzles, plot_h2h_heatmap, plot_budget_modes]


def make_all(results_root: Path, out_dir: Path) -> dict[str, list[Path]]:
    """Draw every figure whose data exists; returns the files written per figure."""
    runs = latest_runs(results_root)
    done: dict[str, list[Path]] = defaultdict(list)
    for fn in PLOTS:
        paths = fn(runs, out_dir)
        done[fn.__name__] = paths
        print(f"{fn.__name__}: {'wrote ' + ', '.join(p.name for p in paths) if paths else 'skipped (no data)'}")
    return dict(done)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=Path("results"))
    ap.add_argument("--out", type=Path, default=Path("results/figures"))
    args = ap.parse_args()
    make_all(args.results, args.out)


if __name__ == "__main__":
    main()

