"""Extrapolate full-run times from a pilot and plan <= 6 h chunks.

Run: python -m experiments.estimate_runtime [--pilot results/pilot_main/pilot2
         --pilot results/pilot_11x11/pilot] [--out results/runtime_estimate.md] [--chunk-hours 6]

Model (all numbers measured in the pilot, nothing assumed except the scaling rules):

* per agent and board: mean wall time per move ``m_a`` at the pilot budget ``b0``;
  an agent is *budget-bound* if ``m_a / b0 >= 0.85`` (time per move scales with the
  budget), *fixed-cost* if lower (stops early, e.g. random, depth-capped search) and
  *overshooting* if above 1.2 (coarse clock checks, so ``max(budget, m_a)``);
* node budgets: time per move = nodes / measured nodes-per-second of that agent;
* plies per game per board from the pilots (a board without a pilot is scaled from 9x9);
* parallel efficiency = total game wall time / sum of (pilot elapsed x pilot workers); the
  planned runs use the pilots' worker count (``--workers`` is written into every command).

A game costs ``(plies - opening) / 2 * (t_x + t_o) + overhead``; a cell costs
games x that / (workers x efficiency).

Calibration against chunks 1-6 of the full runs (see ``calibration_report``): the cell
cost of the model is multiplied by ``calibration_factor`` (actual / predicted summed game
wall time, per time budget).
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from itertools import combinations
from math import ceil, log
from pathlib import Path
from statistics import mean
from typing import Any

from eval.tournament import GameRecord, games_file, max_workers, read_records
from experiments.run import cell_list, load_config

CONFIG_DIR = Path("experiments/configs")
BUDGET_BOUND = 0.85
OVERSHOOT = 1.2
OVERHEAD_S = 0.05
OPENING_PLIES = 3.0
# Sequential extras that run after the games of a config (seconds, from the quick runs).
EXTRAS_S = {"main_9x9": 16 * 30 * 0.5, "ablation_ab": 8 * 60.0}
# Actual / predicted summed game wall time per time budget, measured on the full runs of
# chunks 2-6 (main_9x9 0.1 s 1.20, 0.5 s 0.90, 1 s 0.90; ablation_mcts 0.93, main_7x7 0.93, scaling
# 0.77-0.99). 0.1 s cells run long (about 60 ms of clock overshoot per search move), 0.5 s and
# 1 s cells short. Node budgets, from the full 7x4 run of chunk 9 (18,190 games): 2,000 nodes 0.90,
# 10,000 nodes 1.21. The ratio grows with the budget because MCTS nodes/s drop as the tree grows
# (pilot 2,200/s at 0.5 s, 1,500-1,800/s at 10,000 simulations) while alpha-beta agents stop below
# the node budget (iterative deepening finishes first: 0.4-0.7 of the pilot cost). Rosters made only of
# alpha-beta agents play longer games than the pilot's mixed roster (ablation_ab: 1.36); that is not modelled.
TIME_CAL = ((0.1, 1.20), (0.5, 0.90), (1.0, 0.90))
NODES_CAL = ((2000.0, 0.90), (10000.0, 1.21))
# Measured parallel efficiency of chunks of 15 min or more: 0.98-0.99 (pilot: 0.98).
PILOTS = (Path("results/pilot_main/pilot2"), Path("results/pilot_11x11/pilot"))
FULL_ORDER = ["ablation_ab", "ablation_mcts", "scaling", "main_7x7", "main_9x9", "main_11x11",
              "failure_mining", "nodes_budget"]


@dataclass
class AgentProfile:
    """Pilot measurements of one agent on one board."""

    per_move_s: float
    fill: float
    nps: float


def agent_key(spec: Any) -> str:
    """Pilot agent name an entry of a config's agent list behaves like."""
    return spec.lower() if isinstance(spec, str) else str(spec["base"]).lower()


def profiles(recs: list[GameRecord], b0: float) -> tuple[dict[tuple[int, str], AgentProfile],
                                                         dict[int, float]]:
    """(board n, agent) -> profile, and board n -> mean plies per game."""
    walls: dict[tuple[int, str], list[float]] = {}
    nps: dict[tuple[int, str], list[float]] = {}
    plies: dict[int, list[int]] = {}
    for r in recs:
        n = r.config["n"]
        plies.setdefault(n, []).append(len(r.opening) + len(r.moves))
        first = 0 if len(r.opening) % 2 == 0 else 1
        for i, m in enumerate(r.moves):
            who = r.agent_x if i % 2 == first else r.agent_o
            walls.setdefault((n, who), []).append(m.wall_s)
            if m.nodes_per_s > 0:
                nps.setdefault((n, who), []).append(m.nodes_per_s)
    prof = {k: AgentProfile(mean(v), mean(v) / b0, mean(nps[k]) if k in nps else 0.0)
            for k, v in walls.items()}
    return prof, {n: mean(v) for n, v in plies.items()}


def move_time(p: AgentProfile, mode: str, budget: float, b0: float) -> float:
    """Expected seconds per move of an agent at ``budget``."""
    if mode == "nodes":
        return budget / p.nps if p.nps > 0 else 0.0
    if p.fill > OVERSHOOT:
        return max(budget, p.per_move_s)  # coarse clock checks: a fixed batch time dominates
    if p.fill >= BUDGET_BOUND:
        return p.fill * budget
    return min(p.per_move_s, budget)


def calibration_factor(mode: str, budget: float) -> float:
    """Correction of a cell's predicted CPU seconds (log-linear in the budget, clamped)."""
    knots = NODES_CAL if mode == "nodes" else TIME_CAL
    if budget <= knots[0][0]:
        return knots[0][1]
    for (b0, f0), (b1, f1) in zip(knots, knots[1:]):
        if budget <= b1:
            return f0 + (f1 - f0) * (log(budget) - log(b0)) / (log(b1) - log(b0))
    return knots[-1][1]


# Agents absent from the pilot roster are costed like their closest measured sibling.
PROXY = {"ab_order_id": "ab_order_id_tt"}


def lookup(prof: dict[tuple[int, str], AgentProfile], n: int, key: str) -> AgentProfile:
    """Profile of ``key`` on board ``n`` (falling back to 9x9 and to a proxy agent)."""
    key = PROXY.get(key, key)
    return prof.get((n, key)) or prof[(9, key)]


def cell_seconds(cfg: dict[str, Any], n: int, budget: float, prof: dict[tuple[int, str], AgentProfile],
                 plies: dict[int, float], b0: float) -> float:
    """CPU seconds of one (board, budget) cell, before dividing by the workers."""
    ref = n if n in plies else 9
    length = plies[ref] * (n / ref if n not in plies else 1.0)
    agents = cfg["agents"]
    total = 0.0
    for a, b in combinations(agents, 2):
        pa, pb = lookup(prof, ref, agent_key(a)), lookup(prof, ref, agent_key(b))
        per_pair = (length - OPENING_PLIES) / 2 * (
            move_time(pa, cfg["budget_mode"], budget, b0)
            + move_time(pb, cfg["budget_mode"], budget, b0)) + OVERHEAD_S
        total += cfg["games_per_pair"] * per_pair
    return total


@lru_cache(maxsize=1)
def pilot_model(pilots: tuple[Path, ...] = PILOTS) -> tuple[
        dict[tuple[int, str], AgentProfile], dict[int, float], float, float]:
    """(profiles, plies per board, pilot budget, parallel efficiency) from the pilots."""
    per_pilot = [(p, read_records(games_file(p))) for p in pilots]
    recs = [r for _, rs in per_pilot for r in rs]
    b0 = recs[0].time_budget_s
    prof, plies = profiles(recs, b0)
    eff = sum(r.wall_time_s for r in recs) / sum(pilot_elapsed(p) * pilot_workers(p) for p in pilots)
    return prof, plies, b0, eff


def estimated_hours(cfg: dict[str, Any], cells: list[tuple[int, int, float]], workers: int) -> float:
    """Calibrated wall hours of ``cells`` of a config on ``workers`` workers."""
    prof, plies, b0, eff = pilot_model()
    secs = sum(cell_seconds(cfg, n, float(b), prof, plies, b0)
               * calibration_factor(cfg["budget_mode"], float(b)) for n, _k, b in cells)
    return secs / (workers * eff) / 3600


def chunk_times(progress: Path) -> dict[int, float]:
    """Chunk number -> seconds from the last START to the matching END in a progress log."""
    start: dict[int, datetime] = {}
    out: dict[int, float] = {}
    for line in progress.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"(\S+ \S+)\s+chunk (\d+) .*?(START|END)", line)
        if not m:
            continue
        t, n = datetime.fromisoformat(m.group(1)), int(m.group(2))
        if m.group(3) == "START":
            start[n] = t
        elif n in start:
            out[n] = (t - start[n]).total_seconds()
    return out


def calibration_report(run_root: Path = Path("results"), progress: Path | None = None) -> list[str]:
    """Markdown: predicted vs actual summed game wall time per cell of the full runs, and
    actual parallel efficiency per chunk (needs ``results/<config>/full`` and the progress log)."""
    prof, plies, b0, _ = pilot_model()
    lines = ["", "## Calibration on the full runs", "",
             "| config | cell | games | predicted CPU h | actual CPU h | actual / predicted |",
             "|---|---|---|---|---|---|"]
    for name in FULL_ORDER:
        f = games_file(run_root / name / "full")
        if not f.exists():
            continue
        cfg = load_config(CONFIG_DIR / f"{name}.yaml")
        actual: dict[tuple[int, int, float], list[float]] = defaultdict(list)
        for r in read_records(f):
            budget = float(r.game_id.split("|")[1][1:]) if cfg["budget_mode"] == "nodes" else r.time_budget_s
            actual[(r.config["n"], r.config["k"], budget)].append(r.wall_time_s)
        pairs = len(cfg["agents"]) * (len(cfg["agents"]) - 1) // 2
        for n, k, b in cell_list(cfg):
            a = actual.get((n, k, float(b)))
            if a:
                pred = cell_seconds(cfg, n, float(b), prof, plies, b0)
                if cfg["budget_mode"] == "nodes":
                    pred *= len(a) / (pairs * cfg["games_per_pair"])
                lines.append(f"| {name} | {n}x{k}@{b:g} | {len(a)} | {pred / 3600:.2f} | "
                             f"{sum(a) / 3600:.2f} | {sum(a) / pred:.2f} |")
    if progress is not None and progress.exists():
        lines += ["", "Elapsed time per chunk (progress log):", "",
                  "| chunk | elapsed min |", "|---|---|"]
        lines += [f"| {n} | {t / 60:.1f} |" for n, t in sorted(chunk_times(progress).items())]
    return lines


@dataclass
class Chunk:
    """One resumable command."""

    config: str
    cells: list[str]
    part: tuple[int, int]
    hours: float
    extras: bool


def plan_chunks(cells: list[tuple[str, str, float]], extras_h: dict[str, float],
                limit_h: float) -> list[Chunk]:
    """Pack (config, cell, hours) units into chunks of at most ``limit_h`` hours.

    A cell longer than the limit is split into interleaved opening slices; small
    cells of one config are merged. The last chunk of a config also runs its extras.
    """
    chunks: list[Chunk] = []
    for cfg in dict.fromkeys(c for c, _, _ in cells):
        units = [(cell, h) for c, cell, h in cells if c == cfg]
        cur: list[tuple[str, float]] = []
        for cell, h in units:
            if h > limit_h:
                m = ceil(h / limit_h)
                for i in range(1, m + 1):
                    chunks.append(Chunk(cfg, [cell], (i, m), h / m, False))
                continue
            if cur and sum(x for _, x in cur) + h > limit_h:
                chunks.append(Chunk(cfg, [c for c, _ in cur], (1, 1), sum(x for _, x in cur),
                                    False))
                cur = []
            cur.append((cell, h))
        if cur:
            chunks.append(Chunk(cfg, [c for c, _ in cur], (1, 1), sum(x for _, x in cur), False))
        chunks[-1].extras = cfg in extras_h
        chunks[-1].hours += extras_h.get(cfg, 0.0)
    return chunks


def command(ch: Chunk, workers: int | None = None) -> str:
    """The shell command that runs one chunk (idempotent and resumable)."""
    cmd = (f"python -m experiments.run --config experiments/configs/{ch.config}.yaml "
           f"--run-dir results/{ch.config}/full --only {' '.join(ch.cells)}")
    if workers is not None:
        cmd += f" --workers {workers}"
    if ch.part != (1, 1):
        cmd += f" --part {ch.part[0]}/{ch.part[1]}"
    if ch.extras:
        cmd += " --extras"
    return cmd


def pilot_workers(pilot: Path) -> int:
    """Worker count a pilot ran with (``max_workers`` line of its environment.txt)."""
    for line in (pilot / "environment.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("max_workers:"):
            return int(line.split(":")[1])
    return max_workers()


def pilot_elapsed(pilot: Path) -> float:
    """Seconds from the first logged command to the last written game."""
    start = (pilot / "commands.log").read_text().splitlines()[0].split()[0]
    return games_file(pilot).stat().st_mtime - datetime.fromisoformat(start).timestamp()


def node_budget_notes(cells: list[tuple[str, str, float]], workers: int, eff: float) -> list[str]:
    """Markdown: how the node-budget factors were obtained and what they predict for 9x5@2000."""
    h = {(c, cell): v for c, cell, v in cells}.get(("nodes_budget", "9x5@2000"))
    if h is None:
        return []
    return ["", "## Node-budget calibration (chunk 9, 7x4, 18,190 games)", "",
            "Method: for each node-budget cell the summed `wall_time_s` of its games is divided by the pilot",
            "model's prediction for the same games (`cell_seconds`, per-agent nodes / pilot nodes-per-second).",
            "The two ratios (0.90 at 2,000 nodes, 1.21 at 10,000) are the knots of `NODES_CAL` and are",
            "interpolated log-linearly in the budget. By pair class at 2,000 nodes the ratio is 0.96 for",
            "alpha-beta vs MCTS, 0.85 for MCTS vs MCTS, 0.66 for alpha-beta vs alpha-beta (iterative deepening",
            "stops below the node budget); at 10,000 nodes MCTS vs MCTS is 1.65 (tree growth lowers nodes/s).",
            "Chunk 9 used 10 workers for 61.5 CPU hours, i.e. the 6.15 h from 14:37 to its last game at 20:46",
            "(parallel efficiency 1.00); the run was then stalled with the last 10 games unfinished until it",
            "was interrupted at 00:04 (cause unknown, the 10 games replay in under 25 s each).", "",
            f"Prediction for 9x5@2000 on {workers} workers: **{h:.1f} h** (uncalibrated model 3.9 h;",
            "pessimistic bound with the 10,000-node factor 4.7 h). Caveat: on 9x5 alpha-beta agents fill more of",
            "the node budget than on 7x4, so the true value is likely between the calibrated and the pessimistic figure.",
            f"(parallel efficiency used: {eff:.2f})"]


def run(pilots: list[Path], chunk_hours: float) -> tuple[str, list[Chunk]]:
    """Build the markdown report and the chunk list."""
    per_pilot = [(p, read_records(games_file(p))) for p in pilots]
    recs = [r for _, rs in per_pilot for r in rs]
    workers = pilot_workers(pilots[0])
    b0 = recs[0].time_budget_s
    prof, plies = profiles(recs, b0)
    game_wall = sum(r.wall_time_s for r in recs)
    capacity = sum(pilot_elapsed(p) * pilot_workers(p) for p in pilots)
    eff = game_wall / capacity
    lines = [
        "# Runtime estimate", "",
        "Pilots: " + "; ".join(f"`{p}` ({len(rs)} games, {pilot_elapsed(p) / 60:.1f} min, "
                               f"{pilot_workers(p)} workers)" for p, rs in per_pilot) + ".",
        f"Budget {b0} s, summed game wall time {game_wall / 3600:.2f} h, "
        f"parallel efficiency {eff:.2f}. Planned runs use {workers} workers.", "",
        "Mean plies per game: " + ", ".join(f"{n}x{n}: {v:.1f}" for n, v in sorted(plies.items())) + ".",
    ]
    for size in sorted(plies):
        lines += ["", f"Per-agent time per move at the pilot budget ({size}x{size}):", "",
                  "| agent | s/move | fill | nodes/s |", "|---|---|---|---|"]
        for (n, a), p in sorted(prof.items()):
            if n == size:
                lines.append(f"| {a} | {p.per_move_s:.3f} | {p.fill:.2f} | {p.nps:,.0f} |")
    for pilot, rs in per_pilot:
        pcfg = load_config(pilot / "config.yaml")
        predicted = sum(cell_seconds(pcfg, n, b0, prof, plies, b0) for n, _k, _b in cell_list(pcfg))
        elapsed = pilot_elapsed(pilot)
        lines += ["", f"Model check on `{pilot}` (in-sample, so it only tests the plumbing): "
                  f"predicted {predicted / (workers * eff) / 60:.1f} min vs measured "
                  f"{elapsed / 60:.1f} min."]
    cells: list[tuple[str, str, float]] = []
    per_cfg: dict[str, float] = {}
    for name in FULL_ORDER:
        cfg = load_config(CONFIG_DIR / f"{name}.yaml")
        per_cfg[name] = 0.0
        for n, k, b in cell_list(cfg):
            secs = (cell_seconds(cfg, n, float(b), prof, plies, b0)
                    * calibration_factor(cfg["budget_mode"], float(b)) / (workers * eff))
            cells.append((name, f"{n}x{k}@{b:g}", secs / 3600))
            per_cfg[name] += secs / 3600
    extras_h = {k: v / 3600 for k, v in EXTRAS_S.items()}
    lines += ["", "## Per cell (hours, calibrated)", ""]
    lines += ["Pilot-profile model times `calibration_factor` (time budgets: 1.20 at 0.1 s, 0.90 at "
              "0.5 s and 1 s; node budgets: 0.90 at 2,000 and 1.21 at 10,000 nodes, log-linear in "
              "between; both measured on full runs).", ""]
    lines += ["| config | cell | hours |", "|---|---|---|"]
    lines += [f"| {c} | {cell} | {h:.2f} |" for c, cell, h in cells]
    lines += ["", "## Per config", "", "| config | games hours | + extras | total |", "|---|---|---|---|"]
    for name in FULL_ORDER:
        e = extras_h.get(name, 0.0)
        lines.append(f"| {name} | {per_cfg[name]:.2f} | {e:.2f} | {per_cfg[name] + e:.2f} |")
    lines.append(f"| **all** | | | **{sum(per_cfg.values()) + sum(extras_h.values()):.1f}** |")
    lines += calibration_report(progress=Path("results/logs/progress.txt"))
    lines += node_budget_notes(cells, workers, eff)
    chunks = plan_chunks(cells, extras_h, chunk_hours)
    lines += ["", f"## Chunks (each <= {chunk_hours:g} h, run in this order; all resumable)", "",
              "| # | est. h | command |", "|---|---|---|"]
    for i, ch in enumerate(chunks, 1):
        lines.append(f"| {i} | {ch.hours:.1f} | `{command(ch, workers)}` |")
    lines += ["", "Resume after an interruption by re-running the same command: finished game ids",
              "are skipped and a truncated last JSONL line is repaired. When all chunks of a",
              "config are done, `python -m experiments.plots` etc. pick up `results/<config>/full`.", ""]
    return "\n".join(lines), chunks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=Path, action="append",
                    help="pilot run directory (repeat for several boards)")
    ap.add_argument("--out", type=Path, default=Path("results/runtime_estimate.md"))
    ap.add_argument("--chunk-hours", type=float, default=6.0)
    args = ap.parse_args()
    pilots = args.pilot or [Path("results/pilot_main/pilot2"), Path("results/pilot_11x11/pilot")]
    text, _ = run(pilots, args.chunk_hours)
    args.out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

