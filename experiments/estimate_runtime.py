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
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from math import ceil
from pathlib import Path
from statistics import mean
from typing import Any

from eval.tournament import GameRecord, max_workers, read_records
from experiments.run import cell_list, load_config

CONFIG_DIR = Path("experiments/configs")
BUDGET_BOUND = 0.85
OVERSHOOT = 1.2
OVERHEAD_S = 0.05
OPENING_PLIES = 3.0
# Sequential extras that run after the games of a config (seconds, from the quick runs).
EXTRAS_S = {"main_9x9": 16 * 30 * 0.5, "ablation_ab": 8 * 60.0}
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
    return (pilot / "games.jsonl").stat().st_mtime - datetime.fromisoformat(start).timestamp()


def run(pilots: list[Path], chunk_hours: float) -> tuple[str, list[Chunk]]:
    """Build the markdown report and the chunk list."""
    per_pilot = [(p, read_records(p / "games.jsonl")) for p in pilots]
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
            secs = cell_seconds(cfg, n, float(b), prof, plies, b0) / (workers * eff)
            cells.append((name, f"{n}x{k}@{b:g}", secs / 3600))
            per_cfg[name] += secs / 3600
    extras_h = {k: v / 3600 for k, v in EXTRAS_S.items()}
    lines += ["", "## Per cell (hours)", "", "| config | cell | hours |", "|---|---|---|"]
    lines += [f"| {c} | {cell} | {h:.2f} |" for c, cell, h in cells]
    lines += ["", "## Per config", "", "| config | games hours | + extras | total |", "|---|---|---|---|"]
    for name in FULL_ORDER:
        e = extras_h.get(name, 0.0)
        lines.append(f"| {name} | {per_cfg[name]:.2f} | {e:.2f} | {per_cfg[name] + e:.2f} |")
    lines.append(f"| **all** | | | **{sum(per_cfg.values()) + sum(extras_h.values()):.1f}** |")
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

