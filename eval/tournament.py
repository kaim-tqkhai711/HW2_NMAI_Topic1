"""Game playing, balanced openings and a resumable parallel round-robin.

Moves are stored as ``[row, col]`` pairs in the JSONL records (flat indices are
used only inside the program). Agents are rebuilt from picklable factories inside
worker processes, so ``round_robin`` works under the Windows ``spawn`` start
method; use `RegistryFactory` for entries of ``AGENT_REGISTRY``.
"""
from __future__ import annotations

import json
import os
import zlib
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field, replace
from itertools import combinations
from multiprocessing import get_context
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from agents.alphabeta import AlphaBetaAgent
from agents.alphabeta import _Timeout as _ABTimeout
from agents.backtracking import BacktrackingAgent
from agents.backtracking import _Timeout as _BTTimeout
from agents.base import Agent
from agents.mcts import MCTSAgent
from agents.presets import AGENT_REGISTRY
from agents.random_agent import RandomAgent
from core.board import Board
from core.rules import GameConfig, X

AgentFactory = Callable[[int], Agent]
VIOLATION_FACTOR = 1.5
_NO_LIMIT_S = 1e9


@dataclass(frozen=True)
class RegistryFactory:
    """Picklable factory for a named entry of ``AGENT_REGISTRY``."""

    name: str

    def __call__(self, seed: int) -> Agent:
        return AGENT_REGISTRY[self.name](seed)


@dataclass
class MoveRecord:
    """One move with the search statistics reported by the agent.

    Attributes:
        move: ``[row, col]``.
        nodes: Nodes (or simulations) the agent reported.
        stat_time_s: Time the agent reported.
        wall_s: Wall-clock time measured around ``select_move``.
        nodes_per_s: ``nodes / wall_s``.
        depth: Depth reached, or None.
        extra: Agent-specific counters.
    """

    move: list[int]
    nodes: int
    stat_time_s: float
    wall_s: float
    nodes_per_s: float
    depth: int | None
    extra: dict[str, float] = field(default_factory=dict)


@dataclass
class GameRecord:
    """Everything needed to analyse and replay one game.

    Attributes:
        game_id: Unique id (also the resume key).
        config: ``{"n": .., "k": .., "exact_k": ..}``.
        agent_x / agent_o: Names of the two sides.
        seed: Tournament seed.
        opening: Pre-placed stones as ``[row, col]``, played alternately from X.
        moves: Agent moves after the opening.
        result: +1 X won, -1 O won, 0 draw.
        wall_time_s: Total wall time of the game.
        violations: Moves that took more than 1.5 x the budget (time mode).
        time_budget_s: Per-move budget (time mode) or 0 in node mode.
        budget_mode: "time" or "nodes".
    """

    game_id: str
    config: dict[str, Any]
    agent_x: str
    agent_o: str
    seed: int
    opening: list[list[int]]
    moves: list[MoveRecord]
    result: int
    wall_time_s: float
    violations: int
    time_budget_s: float
    budget_mode: str = "time"

    def to_json(self) -> str:
        """Serialise to one JSON line (no trailing newline)."""
        return json.dumps(asdict(self), separators=(",", ":"))

    @staticmethod
    def from_json(line: str) -> GameRecord:
        """Inverse of `to_json`."""
        d = json.loads(line)
        d["moves"] = [MoveRecord(**m) for m in d["moves"]]
        return GameRecord(**d)


class _NodeLimitedAB(AlphaBetaAgent):
    """Alpha-beta that stops after a fixed number of nodes instead of time."""

    node_limit = 0

    def _search(self, depth: int, alpha: int, beta: int, ply: int) -> int:
        if self._nodes >= self.node_limit:
            raise _ABTimeout
        return super()._search(depth, alpha, beta, ply)


class _NodeLimitedBT(BacktrackingAgent):
    """Backtracking that stops after a fixed number of nodes instead of time."""

    node_limit = 0

    def _negamax(self, board: Board, ply: int) -> int:
        if self._nodes >= self.node_limit:
            raise _BTTimeout
        return super()._negamax(board, ply)


def adapt_for_nodes(agent: Agent, node_budget: int) -> Agent:
    """Return an agent limited to ``node_budget`` nodes/simulations per move.

    The Agent interface is untouched: MCTS agents get ``max_iterations``;
    search agents are replaced by a subclass that counts nodes. Callers should
    pass a huge time budget to ``select_move``.

    Raises:
        TypeError: For agent types without a node notion (other than Random).
    """
    if isinstance(agent, MCTSAgent):
        agent.config = replace(agent.config, max_iterations=node_budget)
        return agent
    if isinstance(agent, AlphaBetaAgent):
        ab = _NodeLimitedAB(agent.config, weights=agent.weights)
        ab.node_limit = node_budget
        return ab
    if isinstance(agent, BacktrackingAgent):
        bt = _NodeLimitedBT(agent.max_depth)
        bt.node_limit = node_budget
        return bt
    if isinstance(agent, RandomAgent):
        return agent
    raise TypeError(f"no node budget for {type(agent).__name__}")


def make_opening(config: GameConfig, seed: int, index: int) -> tuple[int, ...]:
    """2-4 random central stones (flat moves), deterministic in the arguments."""
    rng = np.random.default_rng([seed, index, config.n, config.k])
    n = config.n
    radius = max(1, n // 4)
    centre = n // 2
    cells = [
        r * n + c
        for r in range(max(0, centre - radius), min(n, centre + radius + 1))
        for c in range(max(0, centre - radius), min(n, centre + radius + 1))
    ]
    while True:
        size = int(rng.integers(2, 5))
        pick = rng.choice(len(cells), size=min(size, len(cells)), replace=False)
        stones = tuple(cells[int(i)] for i in pick)
        b = Board(config)
        for m in stones:
            b.make(m)
        if not b.is_terminal:
            return stones


def play_game(
    agent_x: Agent,
    agent_o: Agent,
    config: GameConfig,
    time_budget_s: float,
    seed: int,
    opening: tuple[int, ...] | None = None,
    names: tuple[str, str] | None = None,
    game_id: str = "",
    budget_mode: str = "time",
) -> GameRecord:
    """Play one game and record it.

    Args:
        agent_x: Agent playing X (moves first).
        agent_o: Agent playing O.
        config: Game configuration.
        time_budget_s: Per-move budget passed to ``select_move``.
        seed: Seed recorded in the result (agents carry their own seeds).
        opening: Flat moves pre-placed alternately starting with X.
        names: Display names; defaults to the agents' ``name``.
        game_id: Identifier stored in the record.
        budget_mode: Stored in the record; violations are only counted in
            "time" mode.

    Returns:
        The finished `GameRecord`.

    Raises:
        RuntimeError: If an agent returns an illegal move or changes the board.
    """
    board = Board(config)
    for m in opening or ():
        board.make(m)
    nx, no = names or (agent_x.name, agent_o.name)
    moves: list[MoveRecord] = []
    violations = 0
    t_game = perf_counter()
    while not board.is_terminal:
        agent = agent_x if board.to_move == X else agent_o
        h, ply = board.hash, board.ply
        t0 = perf_counter()
        move = agent.select_move(board, time_budget_s)
        wall = perf_counter() - t0
        if board.hash != h or board.ply != ply:
            raise RuntimeError(f"{agent.name} modified the board")
        if move not in board.legal_moves():
            raise RuntimeError(f"{agent.name} returned illegal move {move}")
        st = agent.last_stats()
        if budget_mode == "time" and wall > VIOLATION_FACTOR * time_budget_s:
            violations += 1
        r, c = board.to_rc(move)
        moves.append(
            MoveRecord(
                move=[r, c],
                nodes=st.nodes,
                stat_time_s=st.time_s,
                wall_s=wall,
                nodes_per_s=st.nodes / wall if wall > 0 else 0.0,
                depth=st.depth_reached,
                extra=dict(st.extra),
            )
        )
        board.make(move)
    return GameRecord(
        game_id=game_id,
        config={"n": config.n, "k": config.k, "exact_k": config.exact_k},
        agent_x=nx,
        agent_o=no,
        seed=seed,
        opening=[list(Board(config).to_rc(m)) for m in (opening or ())],
        moves=moves,
        result=board.winner,
        wall_time_s=perf_counter() - t_game,
        violations=violations,
        time_budget_s=time_budget_s if budget_mode == "time" else 0.0,
        budget_mode=budget_mode,
    )


@dataclass(frozen=True)
class _Task:
    game_id: str
    name_x: str
    name_o: str
    factory_x: AgentFactory
    factory_o: AgentFactory
    n: int
    k: int
    exact_k: bool
    time_budget_s: float
    budget_mode: str
    node_budget: int
    seed: int
    opening: tuple[int, ...]


def _agent_seed(seed: int, game_id: str, role: str) -> int:
    return zlib.crc32(f"{seed}|{game_id}|{role}".encode()) & 0x7FFFFFFF


def _run_task(task: _Task) -> GameRecord:
    ax = task.factory_x(_agent_seed(task.seed, task.game_id, "x"))
    ao = task.factory_o(_agent_seed(task.seed, task.game_id, "o"))
    budget = task.time_budget_s
    if task.budget_mode == "nodes":
        ax = adapt_for_nodes(ax, task.node_budget)
        ao = adapt_for_nodes(ao, task.node_budget)
        budget = _NO_LIMIT_S
    rec = play_game(
        ax,
        ao,
        GameConfig(task.n, task.k, task.exact_k),
        budget,
        task.seed,
        task.opening,
        names=(task.name_x, task.name_o),
        game_id=task.game_id,
        budget_mode=task.budget_mode,
    )
    rec.time_budget_s = task.time_budget_s if task.budget_mode == "time" else 0.0
    return rec


def max_workers() -> int:
    """Physical cores minus one (at least 1); estimated from logical cores without psutil."""
    try:
        import psutil

        cores = psutil.cpu_count(logical=False) or (os.cpu_count() or 2) // 2
    except ImportError:
        cores = (os.cpu_count() or 2) // 2
    return max(1, cores - 1)


def _repair_jsonl(path: Path) -> None:
    """Drop a partially written final line left by a killed run."""
    if not path.exists():
        return
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        path.write_bytes(data[: data.rfind(b"\n") + 1])


def read_records(path: Path) -> list[GameRecord]:
    """Read all complete records from a JSONL file (missing file -> empty)."""
    if not path.exists():
        return []
    out: list[GameRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(GameRecord.from_json(line))
    return out


def round_robin(
    agent_factories: Mapping[str, AgentFactory],
    config: GameConfig,
    time_budget_s: float,
    games_per_pair: int,
    n_workers: int | None = None,
    seed: int = 0,
    budget_mode: str = "time",
    out_path: Path | None = None,
    node_budget: int = 20000,
) -> list[GameRecord]:
    """Play every pair of agents and return all records.

    Each pair plays ``games_per_pair`` games: ``games_per_pair / 2`` random
    openings (identical for all pairs), each played with colours swapped. Results
    are appended to ``out_path`` (JSONL) as they finish; games whose id is
    already in the file are skipped, so an interrupted run can be restarted.

    Args:
        agent_factories: Name -> picklable ``seed -> Agent`` factory.
        config: Game configuration.
        time_budget_s: Per-move time budget (time mode).
        games_per_pair: Even number of games per unordered pair.
        n_workers: Worker processes; capped at `max_workers()`.
        seed: Tournament seed (openings and agent seeds derive from it).
        budget_mode: "time", or "nodes" for a fixed per-move node/simulation
            budget (see `adapt_for_nodes`).
        out_path: JSONL file; None keeps results in memory only.
        node_budget: Nodes or simulations per move in "nodes" mode.

    Returns:
        Records of exactly this tournament's games (resumed ones included).

    Raises:
        ValueError: On odd ``games_per_pair`` or an unknown ``budget_mode``.
    """
    if games_per_pair % 2 or games_per_pair < 2:
        raise ValueError("games_per_pair must be an even number >= 2")
    if budget_mode not in ("time", "nodes"):
        raise ValueError(f"unknown budget_mode {budget_mode!r}")
    workers = min(n_workers or max_workers(), max_workers())
    names = list(agent_factories)
    budget_tag = f"t{time_budget_s:g}" if budget_mode == "time" else f"n{node_budget}"
    tag = f"{config.n}x{config.k}{'e' if config.exact_k else ''}|{budget_tag}|{seed}"
    tasks: list[_Task] = []
    for a, b in combinations(names, 2):
        for o in range(games_per_pair // 2):
            opening = make_opening(config, seed, o)
            for swap in (0, 1):
                x, oo = (a, b) if swap == 0 else (b, a)
                tasks.append(
                    _Task(
                        f"{tag}|{a}|{b}|o{o}|s{swap}", x, oo,
                        agent_factories[x], agent_factories[oo],
                        config.n, config.k, config.exact_k,
                        time_budget_s, budget_mode, node_budget, seed, opening,
                    )
                )
    wanted = {t.game_id for t in tasks}
    done: dict[str, GameRecord] = {}
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _repair_jsonl(out_path)
        for r in read_records(out_path):
            if r.game_id in wanted:
                done[r.game_id] = r
    todo = [t for t in tasks if t.game_id not in done]

    def run(sink: Any) -> None:
        if workers <= 1 or len(todo) <= 1:
            for t in todo:
                sink(_run_task(t))
            return
        with get_context("spawn").Pool(min(workers, len(todo))) as pool:
            for rec in pool.imap_unordered(_run_task, todo, chunksize=1):
                sink(rec)

    if out_path is not None:
        with out_path.open("a", encoding="utf-8", newline="\n") as f:

            def sink(rec: GameRecord) -> None:
                f.write(rec.to_json() + "\n")
                f.flush()
                done[rec.game_id] = rec

            run(sink)
    else:
        run(lambda rec: done.__setitem__(rec.game_id, rec))
    return [done[t.game_id] for t in tasks]
