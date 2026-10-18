"""GUI game logic: pure Python, no pygame, safe to test headless.

`GameController` owns the board, move history, per-move statistics and the AI
worker thread. The AI always thinks on a *copy* of the board, so the live board
is only ever touched from the caller's thread (`poll` applies finished moves).
A generation counter discards results that became stale through undo, restart or
cancel; a cancelled agent keeps running to the end of its budget in the
background, so the side gets a fresh agent instance instead of sharing the old one.
"""
from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from time import perf_counter

import numpy as np
from numpy.typing import NDArray

from agents.alphabeta import ABConfig, AlphaBetaAgent
from agents.base import Agent
from agents.presets import AGENT_REGISTRY
from core.board import Board
from core.rules import EMPTY, O, X, GameConfig
from eval.tournament import GameRecord, MoveRecord

AgentFactory = Callable[[int], Agent]
HUMAN = "human"
BUDGET_RANGE = (0.1, 5.0)
OVERLAYS = ("off", "mcts_visits", "mcts_values", "ab_scores")


class Mode(Enum):
    """Who controls each side."""

    HUMAN_VS_AI = "Human vs AI"
    AI_VS_HUMAN = "AI vs Human"
    AI_VS_AI = "AI vs AI"
    HUMAN_VS_HUMAN = "Human vs Human"

    def is_human(self, player: int) -> bool:
        """Whether ``player`` (X=1 / O=-1) is controlled by a person in this mode."""
        if self is Mode.HUMAN_VS_HUMAN:
            return True
        if self is Mode.AI_VS_AI:
            return False
        return (player == X) == (self is Mode.HUMAN_VS_AI)


@dataclass(frozen=True)
class Setup:
    """Everything chosen on the setup screen."""

    n: int = 9
    k: int = 5
    exact_k: bool = False
    mode: Mode = Mode.HUMAN_VS_AI
    agent_x: str = "ab_full_timed"
    agent_o: str = "mcts_heuristic"
    time_budget_s: float = 1.0
    seed: int = 0

    def validate(self) -> None:
        """Raise ValueError for impossible settings."""
        GameConfig(self.n, self.k, self.exact_k)
        if not BUDGET_RANGE[0] <= self.time_budget_s <= BUDGET_RANGE[1]:
            raise ValueError(f"time budget must be within {BUDGET_RANGE}")


@dataclass
class MoveInfo:
    """One played move with what the side panel shows about it."""

    ply: int
    player: int
    move: int
    human: bool
    nodes: int = 0
    depth: int | None = None
    time_s: float = 0.0
    nodes_per_s: float = 0.0
    pv: list[int] = field(default_factory=list)
    win_prob: float | None = None
    extra: dict[str, float] = field(default_factory=dict)


@dataclass
class _AIResult:
    gen: int
    move: int
    info: MoveInfo
    visits: NDArray[np.float64] | None
    values: NDArray[np.float64] | None
    error: str | None = None


class GameController:
    """State machine behind the GUI.

    Args:
        setup: Initial settings.
        registry: Agent factories by name (defaults to `AGENT_REGISTRY`).
    """

    def __init__(self, setup: Setup | None = None,
                 registry: Mapping[str, AgentFactory] | None = None) -> None:
        self.registry: Mapping[str, AgentFactory] = registry or AGENT_REGISTRY
        self._lock = threading.Lock()
        self._gen = 0
        self._result: _AIResult | None = None
        self._thinking = False
        self.autoplay = False
        self.autoplay_delay_s = 0.5
        self._last_move_time = 0.0
        self.last_error: str | None = None
        self.start(setup or Setup())

    # ------------------------------------------------------------ lifecycle
    def start(self, setup: Setup) -> None:
        """(Re)start a game with ``setup``; cancels any running AI."""
        setup.validate()
        self._invalidate()
        self.setup = setup
        self.config = GameConfig(setup.n, setup.k, setup.exact_k)
        self.board = Board(self.config)
        self.infos: list[MoveInfo] = []
        self.last_maps: tuple[int, NDArray[np.float64] | None, NDArray[np.float64] | None] = (
            -1, None, None)
        self.agents: dict[int, Agent | None] = {
            X: self._make_agent(setup.agent_x, X), O: self._make_agent(setup.agent_o, O)}
        self.autoplay = False
        self.last_error = None

    def restart(self) -> None:
        """Start over with the same settings."""
        self.start(self.setup)

    def _make_agent(self, name: str, player: int) -> Agent | None:
        if self.setup.mode.is_human(player):
            return None
        if name not in self.registry:
            raise ValueError(f"unknown agent {name!r}")
        return self.registry[name](self.setup.seed + (0 if player == X else 1))

    def _invalidate(self) -> None:
        """Drop any in-flight AI result (the worker thread just finishes unseen)."""
        with self._lock:
            self._gen += 1
            self._result = None
            self._thinking = False

    # ----------------------------------------------------------------- state
    @property
    def moves(self) -> tuple[int, ...]:
        """All moves played so far."""
        return self.board.move_history

    @property
    def to_move(self) -> int:
        return self.board.to_move

    @property
    def is_over(self) -> bool:
        return self.board.is_terminal

    @property
    def winner(self) -> int:
        return self.board.winner

    @property
    def thinking(self) -> bool:
        """True while an AI move is being computed."""
        return self._thinking

    def is_human_turn(self) -> bool:
        """Whether the side to move is a person and the game is running."""
        return not self.is_over and self.setup.mode.is_human(self.board.to_move)

    def is_ai_turn(self) -> bool:
        return not self.is_over and not self.setup.mode.is_human(self.board.to_move)

    @property
    def last_move(self) -> int | None:
        return self.board.last_move

    def winning_line(self) -> list[int]:
        """Cells of the winning run through the last move (empty if nobody won)."""
        b = self.board
        m = b.last_move
        if not b.winner or m is None:
            return []
        n, k = b.n, b.config.k
        r0, c0 = divmod(m, n)
        for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
            run = [m]
            for sgn in (1, -1):
                r, c = r0 + sgn * dr, c0 + sgn * dc
                while 0 <= r < n and 0 <= c < n and b.cells_list[r * n + c] == b.winner:
                    run.append(r * n + c)
                    r, c = r + sgn * dr, c + sgn * dc
            if len(run) == k or (len(run) > k and not b.config.exact_k):
                return sorted(run)
        return []

    # ----------------------------------------------------------------- moves
    def _apply(self, move: int, info: MoveInfo) -> None:
        self.board.make(move)
        self.infos.append(info)
        self._last_move_time = perf_counter()

    def human_move(self, r: int, c: int) -> bool:
        """Play a person's move at (r, c); False if it is not allowed right now."""
        if not self.is_human_turn() or not (0 <= r < self.config.n and 0 <= c < self.config.n):
            return False
        move = self.board.from_rc(r, c)
        if self.board.cells_list[move] != EMPTY:
            return False
        self._apply(move, MoveInfo(self.board.ply, self.board.to_move, move, True))
        return True

    def request_ai_move(self) -> bool:
        """Start the AI for the side to move in a background thread.

        Returns False if it is not an AI's turn or the AI is already thinking.
        """
        if not self.is_ai_turn() or self._thinking:
            return False
        player = self.board.to_move
        agent = self.agents[player]
        assert agent is not None
        with self._lock:
            self._thinking = True
            gen = self._gen
        snapshot = self.board.copy()
        threading.Thread(
            target=self._think,
            args=(agent, snapshot, self.setup.time_budget_s, gen, player),
            daemon=True,
        ).start()
        return True

    def _think(self, agent: Agent, board: Board, budget: float, gen: int, player: int) -> None:
        ply = board.ply
        t0 = perf_counter()
        try:
            move = agent.select_move(board, budget)
            wall = perf_counter() - t0
            st = agent.last_stats()
            pv = list(agent.last_pv()) if hasattr(agent, "last_pv") else []
            visits = values = None
            win_prob = None
            if hasattr(agent, "root_visit_map") and hasattr(agent, "root_value_map"):
                visits = agent.root_visit_map()
                values = agent.root_value_map()
                if visits is not None and visits.max() > 0:
                    win_prob = float(values.ravel()[int(visits.argmax())])
            elif "score" in st.extra:
                win_prob = None
            info = MoveInfo(ply, player, move, False, st.nodes, st.depth_reached, wall,
                            st.nodes / wall if wall > 0 else 0.0, pv, win_prob, dict(st.extra))
            res = _AIResult(gen, move, info, visits, values)
        except Exception as exc:  # surfaced in the UI instead of killing the thread silently
            res = _AIResult(gen, -1, MoveInfo(ply, player, -1, False), None, None, repr(exc))
        with self._lock:
            if gen == self._gen:
                self._result = res

    def poll(self) -> bool:
        """Apply a finished AI move (call regularly from the UI thread).

        Returns True if the board changed.
        """
        with self._lock:
            res, self._result = self._result, None
            if res is None or res.gen != self._gen:
                return False
            self._thinking = False
        if res.error is not None:
            self.last_error = res.error
            self.autoplay = False
            return False
        if not self.is_ai_turn() or res.move not in self.board.legal_moves():
            return False
        self._apply(res.move, res.info)
        self.last_maps = (res.info.ply, res.visits, res.values)
        return True

    def cancel_ai(self) -> None:
        """Abandon the running AI computation and stop autoplay."""
        was_thinking = self._thinking
        self._invalidate()
        self.autoplay = False
        if was_thinking:
            p = self.board.to_move
            name = self.setup.agent_x if p == X else self.setup.agent_o
            self.agents[p] = self._make_agent(name, p)

    def undo(self) -> bool:
        """Take back the last move; False if there is none."""
        if not self.board.ply:
            return False
        self.cancel_ai()
        self.board.unmake_move()
        self.infos.pop()
        if self.last_maps[0] >= self.board.ply:
            self.last_maps = (-1, None, None)
        return True

    def undo_turn(self) -> bool:
        """Undo until it is a person's turn again (or the start) -- one 'take back' for HvA."""
        if not self.undo():
            return False
        while self.board.ply and not self.is_human_turn() and self.setup.mode is not Mode.AI_VS_AI:
            self.undo()
        return True

    # ------------------------------------------------------------- autoplay
    def tick(self, now: float | None = None) -> bool:
        """Drive AI moves: poll results and start the next AI move when due.

        In AI-vs-AI mode a move is started only while ``autoplay`` is on, spaced by
        ``autoplay_delay_s``; with a human opponent the AI replies at once.
        Returns True if the board changed.
        """
        changed = self.poll()
        if self._thinking or not self.is_ai_turn():
            return changed
        now = perf_counter() if now is None else now
        if self.setup.mode is Mode.AI_VS_AI:
            if self.autoplay and now - self._last_move_time >= self.autoplay_delay_s:
                self.request_ai_move()
        elif self.last_error is None:
            self.request_ai_move()
        return changed

    def step(self) -> bool:
        """AI-vs-AI single step (starts the move; apply it via `poll`/`tick`)."""
        return self.request_ai_move()

    # --------------------------------------------------------------- overlay
    def overlay(self, kind: str) -> NDArray[np.float64] | None:
        """[N, N] heat values for the chosen overlay, or None.

        ``mcts_visits`` / ``mcts_values`` come from the last MCTS move; ``ab_scores``
        scores every candidate of the current position with a depth-2 alpha-beta
        reply search (computed on demand, from the mover's point of view).
        """
        n = self.config.n
        if kind == "mcts_visits":
            v = self.last_maps[1]
            return None if v is None else np.asarray(v, dtype=float).reshape(n, n)
        if kind == "mcts_values":
            v = self.last_maps[2]
            return None if v is None else np.asarray(v, dtype=float).reshape(n, n)
        if kind == "ab_scores":
            return self._ab_scores() if not self.is_over else None
        return None

    def _ab_scores(self, per_move_s: float = 0.05) -> NDArray[np.float64]:
        n = self.config.n
        out = np.full(n * n, np.nan)
        probe = AlphaBetaAgent(ABConfig(True, False, False, 2, 1))
        b = self.board.copy()
        for m in b.candidate_moves(2):
            b.make(m)
            if b.winner:
                out[m] = 1e6
            elif not b.is_terminal:
                probe.select_move(b, per_move_s)
                out[m] = -probe.last_stats().extra["score"]
            else:
                out[m] = 0.0
            b.unmake_move()
        return out.reshape(n, n)

    # ------------------------------------------------------------- save/load
    def to_record(self) -> GameRecord:
        """The game so far as a tournament-format `GameRecord`."""
        mv = []
        for i in self.infos:
            r, c = self.board.to_rc(i.move)
            extra = dict(i.extra)
            if i.win_prob is not None:
                extra["win_prob"] = i.win_prob
            mv.append(MoveRecord([r, c], i.nodes, i.time_s, i.time_s, i.nodes_per_s, i.depth,
                                 extra))
        s = self.setup

        def name(who: str, p: int) -> str:
            return HUMAN if s.mode.is_human(p) else who

        return GameRecord(
            game_id=f"gui-{int(perf_counter() * 1000)}",
            config={"n": s.n, "k": s.k, "exact_k": s.exact_k},
            agent_x=name(s.agent_x, X), agent_o=name(s.agent_o, O), seed=s.seed,
            opening=[], moves=mv, result=self.board.winner, wall_time_s=0.0, violations=0,
            time_budget_s=s.time_budget_s, budget_mode="time",
        )

    def save(self, path: Path) -> None:
        """Write the game as one JSON line (tournament `GameRecord` format)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_record().to_json() + "\n", encoding="utf-8")

    def load(self, path: Path) -> None:
        """Replace the current game with the one stored in ``path``."""
        line = next(ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())
        self.load_record(GameRecord.from_json(line))

    def load_record(self, rec: GameRecord) -> None:
        """Replace the current game with ``rec`` (a saved or tournament game).

        Opening stones and agent moves are replayed as one move list. A side whose
        recorded agent name is in the registry becomes an AI player again, so play
        can continue from the loaded position; anything else becomes human.

        Raises:
            ValueError: If a recorded move is illegal.
        """
        ax = rec.agent_x if rec.agent_x in self.registry else None
        ao = rec.agent_o if rec.agent_o in self.registry else None
        mode = (Mode.AI_VS_AI if ax and ao else Mode.AI_VS_HUMAN if ax
                else Mode.HUMAN_VS_AI if ao else Mode.HUMAN_VS_HUMAN)
        budget = rec.time_budget_s if BUDGET_RANGE[0] <= rec.time_budget_s <= BUDGET_RANGE[1] \
            else self.setup.time_budget_s
        c = rec.config
        setup = Setup(c["n"], c["k"], c.get("exact_k", False), mode,
                      ax or self.setup.agent_x, ao or self.setup.agent_o, budget, rec.seed)
        self.start(setup)
        for r, col in rec.opening:
            self._apply(self.board.from_rc(r, col),
                        MoveInfo(self.board.ply, self.board.to_move, self.board.from_rc(r, col),
                                 True))
        for mr in rec.moves:
            m = self.board.from_rc(*mr.move)
            if m not in self.board.legal_moves():
                raise ValueError(f"illegal move {mr.move} at ply {self.board.ply}")
            wp = mr.extra.get("win_prob")
            self._apply(m, MoveInfo(
                self.board.ply, self.board.to_move, m, False, mr.nodes, mr.depth, mr.wall_s,
                mr.nodes_per_s, [], wp, {k: v for k, v in mr.extra.items() if k != "win_prob"}))


def with_budget(setup: Setup, seconds: float) -> Setup:
    """Copy of ``setup`` with the time budget clamped into the slider range."""
    lo, hi = BUDGET_RANGE
    return replace(setup, time_budget_s=min(hi, max(lo, seconds)))

