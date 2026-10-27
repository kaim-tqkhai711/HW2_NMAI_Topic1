"""Experiment runner.

Run: python -m experiments.run --config experiments/configs/main_tournament.yaml
         [--quick] [--dry-run] [--workers N]

Creates ``results/<config name>/<timestamp>/`` with ``games.jsonl``,
``config.yaml`` (the effective config), ``summary.csv``, ``environment.txt`` and,
depending on the config, ``puzzles.csv``, ``ab_depth.csv``, ``nodes_vs_depth.csv``.

`--quick` plays 4 games per pair at the first budget on the first board only (and
applies the config's optional ``quick:`` overrides). Before any run the game count
and a rough wall-time estimate are printed; `--dry-run` stops after that.
"""
from __future__ import annotations

import argparse
import copy
import csv
import platform
import subprocess
import sys
from dataclasses import dataclass, field, replace
from datetime import datetime
from math import prod
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from agents.alphabeta import AlphaBetaAgent
from agents.backtracking import BacktrackingAgent
from agents.base import Agent
from agents.hybrid import HybridMCTSAgent
from agents.mcts import MCTSAgent
from agents.presets import (
    AB_PRESETS,
    HYBRID_PRESETS,
    HYBRID_TAC_PRESETS,
    MCTS_PRESETS,
    MCTS_TAC_PRESETS,
)
from core.board import Board
from core.rules import GameConfig
from eval.elo import bootstrap_elo, games_from_records
from eval.puzzles import load_puzzles, run_puzzles
from eval.stats import outcome
from eval.tournament import (
    AgentFactory,
    GameRecord,
    RegistryFactory,
    max_workers,
    read_records,
    round_robin,
)
from experiments.run_ab_ablation import measure, write_rows
from tests.positions import QUIET_74

SUMMARY_FIELDS = ["n", "k", "budget_mode", "budget", "agent", "games", "wins", "draws",
                  "losses", "score", "score_lo", "score_hi", "elo", "elo_lo", "elo_hi",
                  "violations", "mean_nodes_per_s"]
PUZZLE_FILE = Path("experiments/puzzles.json")


@dataclass(frozen=True)
class ConfigFactory:
    """Picklable factory for an agent defined by a preset plus parameter overrides."""

    kind: str
    base: str
    params: dict[str, Any] = field(default_factory=dict)

    def __call__(self, seed: int) -> Agent:
        if self.kind == "mcts":
            return MCTSAgent(replace({**MCTS_PRESETS, **MCTS_TAC_PRESETS}[self.base], seed=seed, **self.params))
        if self.kind == "hybrid":
            return HybridMCTSAgent(
                replace({**HYBRID_PRESETS, **HYBRID_TAC_PRESETS}[self.base], seed=seed, **self.params))
        if self.kind == "ab":
            return AlphaBetaAgent(replace(AB_PRESETS[self.base], **self.params), seed=seed)
        raise ValueError(f"unknown agent type {self.kind!r}")


def load_config(path: Path) -> dict[str, Any]:
    """Read a YAML experiment config."""
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    for key in ("name", "seed", "boards", "budgets", "games_per_pair", "agents"):
        if key not in cfg:
            raise ValueError(f"{path}: missing key {key!r}")
    cfg.setdefault("budget_mode", "time")
    cfg.setdefault("anchor", "random")
    return dict(cfg)


def apply_quick(cfg: dict[str, Any]) -> dict[str, Any]:
    """Quick variant: 4 games per pair, first budget, first board, plus ``quick:`` overrides."""
    q = copy.deepcopy(cfg)
    q["games_per_pair"] = 4
    q["budgets"] = q["budgets"][:1]
    q["boards"] = q["boards"][:1]
    for key, val in (q.pop("quick", None) or {}).items():
        if isinstance(val, dict) and isinstance(q.get(key), dict):
            q[key].update(val)
        else:
            q[key] = val
    return q


def parse_agents(specs: list[Any]) -> dict[str, AgentFactory]:
    """Turn the ``agents:`` list into ``name -> picklable factory``.

    An entry is a registry name or ``{name, type, base, params}``.
    """
    out: dict[str, AgentFactory] = {}
    for s in specs:
        if isinstance(s, str):
            out[s] = RegistryFactory(s)
        else:
            out[s["name"]] = ConfigFactory(s["type"], s["base"], dict(s.get("params") or {}))
    return out


def estimate(cfg: dict[str, Any], workers: int) -> tuple[int, float]:
    """(number of games, rough wall seconds) of a tournament config."""
    a = len(cfg["agents"])
    pairs = a * (a - 1) // 2
    names = [s if isinstance(s, str) else s["name"] for s in cfg["agents"]]
    search_frac = sum(1 for n in names if n != "random") / max(1, a)
    games = pairs * cfg["games_per_pair"] * len(cfg["boards"]) * len(cfg["budgets"])
    seconds = 0.0
    for n, _k in cfg["boards"]:
        plies = 3.5 * n
        for b in cfg["budgets"]:
            per_move = b if cfg["budget_mode"] == "time" else b / 3000.0
            seconds += pairs * cfg["games_per_pair"] * plies * per_move * search_frac
    return games, seconds / max(1, workers)


def git_info() -> str:
    """Commit hash and dirty flag, or a note if git is unavailable."""
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True,
                               check=True).stdout.strip()
        return head + (" (uncommitted changes)" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def write_environment(path: Path, argv: list[str]) -> None:
    """Record interpreter, machine, library versions and the git commit."""
    import os

    import matplotlib

    lines = [
        f"python: {sys.version.replace(chr(10), ' ')}",
        f"platform: {platform.platform()}",
        f"processor: {platform.processor()}",
        f"logical_cpus: {os.cpu_count()}",
        f"max_workers: {max_workers()}",
        f"numpy: {np.__version__}",
        f"pyyaml: {yaml.__version__}",
        f"matplotlib: {matplotlib.__version__}",
        f"git_commit: {git_info()}",
        f"command: {' '.join(argv)}",
        f"started: {datetime.now().isoformat(timespec='seconds')}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarise(
    records: list[GameRecord], mode: str, anchor: str | None
) -> list[dict[str, Any]]:
    """One summary row per (board, budget, agent) with W/D/L, score CI and bootstrap Elo."""
    groups: dict[tuple[int, int, float, str], list[GameRecord]] = {}
    for r in records:
        c = r.config
        budget = r.time_budget_s if r.budget_mode == "time" else _node_budget(r)
        groups.setdefault((c["n"], c["k"], budget, r.budget_mode), []).append(r)
    rows: list[dict[str, Any]] = []
    for (n, k, budget, bm), recs in sorted(groups.items()):
        games = games_from_records(recs)
        present = {g[0] for g in games} | {g[1] for g in games}
        elo = bootstrap_elo(games, anchor if anchor in present else None, n_boot=200, seed=0)
        for agent in sorted(elo):
            w = d = lo = 0
            viol = 0
            nps: list[float] = []
            for r in recs:
                for side, name in ((1, r.agent_x), (-1, r.agent_o)):
                    if name != agent:
                        continue
                    res = r.result * side
                    w += res == 1
                    d += res == 0
                    lo += res == -1
                vx, vo = r.violations_by_side()
                viol += (vx if r.agent_x == agent else 0) + (vo if r.agent_o == agent else 0)
                if agent in (r.agent_x, r.agent_o):
                    nps += [m.nodes_per_s for i, m in enumerate(r.moves)
                            if (r.agent_x if i % 2 == _first_mover(r) else r.agent_o) == agent]
            o = outcome(int(w), int(d), int(lo))
            rating, rlo, rhi = elo[agent]
            rows.append({
                "n": n, "k": k, "budget_mode": bm, "budget": budget, "agent": agent,
                "games": o.games, "wins": o.wins, "draws": o.draws, "losses": o.losses,
                "score": round(o.score, 4), "score_lo": round(o.ci[0], 4),
                "score_hi": round(o.ci[1], 4), "elo": round(rating, 1),
                "elo_lo": round(rlo, 1), "elo_hi": round(rhi, 1), "violations": viol,
                "mean_nodes_per_s": round(float(np.mean(nps)), 1) if nps else 0.0,
            })
    return rows


def _first_mover(r: GameRecord) -> int:
    """Index parity of the first agent move: X moves first after an even-length opening."""
    return 0 if len(r.opening) % 2 == 0 else 1


def _node_budget(r: GameRecord) -> float:
    return float(r.game_id.split("|")[1].lstrip("n"))


def write_summary(run_dir: Path, cfg: dict[str, Any]) -> None:
    """Rebuild ``summary.csv`` from every game stored in the run directory."""
    records = read_records(run_dir / "games.jsonl")
    rows = summarise(records, cfg["budget_mode"], cfg.get("anchor")) if records else []
    with (run_dir / "summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        w.writeheader()
        w.writerows(rows)


def run_puzzle_table(cfg: dict[str, Any], out: Path) -> None:
    """Accuracy of every agent per puzzle category -> puzzles.csv."""
    puzzles = load_puzzles(PUZZLE_FILE)
    budget = float(cfg["puzzles"]["budget"])
    factories = parse_agents(cfg["agents"])
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["agent", "category", "accuracy", "n"])
        for name, fac in factories.items():
            acc = run_puzzles(fac(0), budget, puzzles)
            for cat in ("win_in_1", "block", "win_in_3", "all"):
                n = len(puzzles) if cat == "all" else sum(p.category == cat for p in puzzles)
                w.writerow([name, cat, round(acc[cat], 4), n])
            print(f"  puzzles {name}: {acc['all']:.2f}", flush=True)


def run_depth_scaling(spec: dict[str, Any], out: Path) -> None:
    """Nodes (and time) per depth for backtracking and AB presets -> nodes_vs_depth.csv."""
    n, k = int(spec["n"]), int(spec["k"])
    board = QUIET_74.board() if (n, k) == (7, 4) else Board(GameConfig(n, k))
    empties = board.n_empty
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["agent", "n", "k", "depth", "nodes", "time_s", "timed_out",
                    "bound_sequences"])
        for name in spec["agents"]:
            for d in spec["depths"]:
                if name == "backtracking":
                    agent: Agent = BacktrackingAgent(max_depth=d)
                else:
                    agent = AlphaBetaAgent(replace(AB_PRESETS[name.upper()], max_depth=d))
                agent.select_move(board, float(spec["cap_s"]))
                st = agent.last_stats()
                to = int(st.extra.get("timed_out", 0))
                w.writerow([name, n, k, d, st.nodes, round(st.time_s, 3), to,
                            prod(empties - i for i in range(d))])
                f.flush()
                print(f"  depth {name} d={d}: {st.nodes} nodes {st.time_s:.1f}s "
                      f"timed_out={to}", flush=True)
                if to:
                    break


def run_experiment(
    config_path: Path,
    quick: bool = False,
    results_root: Path = Path("results"),
    dry_run: bool = False,
    n_workers: int | None = None,
    timestamp: str | None = None,
    only: list[str] | None = None,
    run_dir: Path | None = None,
    part: tuple[int, int] = (1, 1),
    extras: bool | None = None,
) -> Path | None:
    """Run one config (or one chunk of it) and return its run directory.

    Args:
        config_path: YAML config.
        quick: Apply the quick reductions.
        results_root: Parent of ``<config name>/<timestamp>``.
        dry_run: Only print the estimate; returns None.
        n_workers: Worker processes (capped at `max_workers()`).
        timestamp: Fixed run-directory name (tests).
        only: Cells to play, as ``"NxK@budget"`` (e.g. ``"9x5@0.5"``); default all.
        run_dir: Continue in this existing run directory instead of a new one.
        part: ``(i, m)``: play only the i-th of m interleaved opening slices.
        extras: Run puzzle/depth tables; default only for an unchunked run.

    The summary is always rebuilt from every game in the run directory's
    ``games.jsonl``, so chunks can be run in any order and resumed.
    """
    cfg = load_config(config_path)
    if quick:
        cfg = apply_quick(cfg)
    cfg.pop("quick", None)
    workers = min(n_workers or max_workers(), max_workers())
    games, secs = estimate(cfg, workers)
    print(f"[{cfg['name']}] {games} games, estimated wall time ~{secs / 60:.1f} min "
          f"on {workers} workers (rough)", flush=True)
    if dry_run:
        return None
    if run_dir is None:
        stamp = timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = results_root / str(cfg["name"]) / stamp
    run_dir.mkdir(parents=True, exist_ok=True)
    if not (run_dir / "config.yaml").exists():
        (run_dir / "config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False),
                                             encoding="utf-8")
        write_environment(run_dir / "environment.txt", sys.argv)
    with (run_dir / "commands.log").open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {' '.join(sys.argv)}\n")
    factories = parse_agents(cfg["agents"])
    mode = cfg["budget_mode"]
    games_file = run_dir / "games.jsonl"
    for n, k in cfg["boards"]:
        for b in cfg["budgets"]:
            if only is not None and f"{n}x{k}@{b:g}" not in only:
                continue
            print(f"  {n}x{n} k={k} budget={b} ({mode}) part {part[0]}/{part[1]}", flush=True)
            round_robin(
                factories, GameConfig(n, k), float(b) if mode == "time" else 0.0,
                cfg["games_per_pair"], n_workers=workers, seed=cfg["seed"],
                budget_mode=mode, out_path=games_file,
                node_budget=int(b) if mode == "nodes" else 20000,
                opening_part=part,
            )
    write_summary(run_dir, cfg)
    if extras if extras is not None else (only is None and part == (1, 1)):
        if "puzzles" in cfg:
            run_puzzle_table(cfg, run_dir / "puzzles.csv")
        if "depth_table" in cfg:
            d = int(cfg["depth_table"]["depth"])
            write_rows(measure(d, 600.0, verbose=True), run_dir / "ab_depth.csv")
        if "depth_scaling" in cfg:
            run_depth_scaling(cfg["depth_scaling"], run_dir / "nodes_vs_depth.csv")
    print(f"[{cfg['name']}] done -> {run_dir}", flush=True)
    return run_dir


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--results", type=Path, default=Path("results"))
    ap.add_argument("--only", nargs="+", default=None,
                    help="cells to play, e.g. 9x5@0.5 7x4@1 (default: all)")
    ap.add_argument("--run-dir", type=Path, default=None,
                    help="continue in this existing run directory")
    ap.add_argument("--part", default="1/1", help="i/m: play the i-th of m opening slices")
    ap.add_argument("--extras", action="store_true", default=None,
                    help="also run puzzle/depth tables (default: only for unchunked runs)")
    args = ap.parse_args()
    i, m = (int(x) for x in args.part.split("/"))
    run_experiment(args.config, args.quick, args.results, args.dry_run, args.workers,
                   only=args.only, run_dir=args.run_dir, part=(i, m), extras=args.extras)


if __name__ == "__main__":
    main()
