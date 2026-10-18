r"""Monte-Carlo tree search: UCT with optional heuristic rollouts and RAVE.

Selection value of child c of node s (all values from the point of view of the
player to move at s)::

    Q(c) = (1 - \beta) W(c)/N(c) + \beta W_amaf(c)/N_amaf(c)
    \beta = \sqrt{ rave_k / (3 N(s) + rave_k) }
    score(c) = Q(c) + c_uct \sqrt{ \ln N(s) / N(c) }

Without RAVE, :math:`\beta = 0`. AMAF statistics are kept on the child that
corresponds to the move, and updated for every move the node's player makes
later in the same simulation (tree part and rollout), as in Gelly & Silver.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log, sqrt
from time import perf_counter
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from agents.alphabeta import WindowTracker
from agents.base import Agent, SearchStats
from core.board import Board
from core.rules import EMPTY, GameConfig

_DRAWS = 1 << 14


@dataclass(frozen=True)
class MCTSConfig:
    """Parameters of `MCTSAgent`.

    Attributes:
        c_uct: Exploration constant of UCB1.
        rollout: "random" plays uniformly over empty cells; "heuristic" first
            plays an immediate win, else blocks an immediate opponent win.
        rave: Blend in AMAF statistics.
        rave_k: RAVE equivalence parameter.
        candidate_radius: Tree expansion considers only empty cells within this
            Chebyshev distance of a stone (None = all). Rollouts ignore it.
        max_rollout_depth: Stop a rollout after this many moves and score it a
            draw (None = play to the end).
        reuse_tree: Keep the subtree below the opponent's reply between calls.
        max_iterations: Hard cap on simulations per call (for deterministic tests).
        seed: Seed of the agent's random generator.
    """

    c_uct: float = 1.414
    rollout: Literal["random", "heuristic"] = "random"
    rave: bool = False
    rave_k: float = 1000.0
    candidate_radius: int | None = 2
    max_rollout_depth: int | None = None
    reuse_tree: bool = True
    max_iterations: int | None = None
    seed: int = 0


class Node:
    """A tree node. Statistics are stored from the viewpoint of the mover into it.

    ``player`` is the side that made ``move`` to reach this node; ``W`` is the
    sum of rewards (1 win, 0.5 draw, 0 loss) *for that player*, so a parent
    choosing among its children maximises ``W / N`` directly. The root has no
    incoming move; its ``player`` is the opponent of the side to move.
    ``rn``/``rw`` are the AMAF visit count and reward for the same player.
    ``proven`` marks a position known to be a win for ``player`` (set only by
    hybrid leaf evaluators; plain MCTS never sets it).
    """

    __slots__ = ("move", "parent", "children", "untried", "N", "W", "rn", "rw",
                 "player", "terminal", "proven")

    def __init__(self, move: int, parent: Node | None, player: int, terminal: bool) -> None:
        self.move = move
        self.parent = parent
        self.children: dict[int, Node] = {}
        self.untried: list[int] | None = None
        self.N = 0
        self.W = 0.0
        self.rn = 0
        self.rw = 0.0
        self.player = player
        self.terminal = terminal
        self.proven = False


class MCTSAgent(Agent):
    """UCT Monte-Carlo tree search; see `MCTSConfig`.

    Args:
        config: Search configuration; ``config.seed`` seeds the agent.
    """

    def __init__(self, config: MCTSConfig | None = None) -> None:
        self.config = config or MCTSConfig()
        super().__init__(self.config.seed)
        self._stats = SearchStats()
        self._root: Node | None = None
        self._root_hist: tuple[int, ...] = ()
        self._root_board = Board(GameConfig(1, 1))
        self._root_n = 0
        self._root_cfg: object = None
        self._draws: list[float] = []
        self._di = _DRAWS
        self._max_depth = 0

    @property
    def name(self) -> str:
        c = self.config
        return f"MCTS({c.rollout}{',rave' if c.rave else ''})"

    def last_stats(self) -> SearchStats:
        return self._stats

    def root_visit_map(self) -> NDArray[np.float64]:
        """[N, N] array of root-child visit counts (0 where never expanded)."""
        out = np.zeros(self._root_n * self._root_n)
        if self._root is not None:
            for m, ch in self._root.children.items():
                out[m] = ch.N
        return out.reshape(self._root_n, self._root_n)

    def root_value_map(self) -> NDArray[np.float64]:
        """[N, N] mean reward of root children for the side to move (NaN if unvisited)."""
        out = np.full(self._root_n * self._root_n, np.nan)
        if self._root is not None:
            for m, ch in self._root.children.items():
                if ch.N:
                    out[m] = ch.W / ch.N
        return out.reshape(self._root_n, self._root_n)

    def _next_draw(self) -> float:
        if self._di >= _DRAWS:
            self._draws = self.rng.random(_DRAWS).tolist()
            self._di = 0
        v = self._draws[self._di]
        self._di += 1
        return v

    def _reuse_root(self, board: Board) -> Node | None:
        old = self._root
        if (
            old is None
            or not self.config.reuse_tree
            or self._root_cfg != board.config
            or board.move_history[: len(self._root_hist)] != self._root_hist
        ):
            return None
        ref = self._root_board.copy()
        node = old
        for m in board.move_history[len(self._root_hist):]:
            nxt = node.children.get(m)
            if nxt is None or ref.is_terminal or m not in ref.empty_cells:
                return None
            ref.make(m)
            node = nxt
        if ref.hash != board.hash or ref.to_move != board.to_move:
            return None
        node.parent = None
        return node

    def select_move(self, board: Board, time_budget_s: float) -> int:
        """Run MCTS for at most `time_budget_s` seconds and return the most visited move.

        The clock is checked every 64 simulations, so at least 64 run unless
        ``max_iterations`` is smaller.

        Raises:
            ValueError: If the game is already over.
        """
        legal = board.legal_moves()
        if not legal:
            raise ValueError("no legal moves: game is over")
        cfg = self.config
        t0 = perf_counter()
        deadline = t0 + time_budget_s
        self._root_n = board.n
        root = self._reuse_root(board)
        if root is None:
            root = Node(-1, None, -board.to_move, False)
        self._root = root
        self._root_hist = board.move_history
        self._root_board = board.copy()
        self._root_cfg = board.config
        self._tb = board.copy(track_candidates=True)
        self._sb = board.copy()
        self._win = WindowTracker(self._sb) if cfg.rollout == "heuristic" else None
        self._max_depth = 0
        sims = 0
        if len(legal) > 1:
            while True:
                if cfg.max_iterations is not None and sims >= cfg.max_iterations:
                    break
                if sims and not sims & 63 and perf_counter() > deadline:
                    break
                self._simulate(root)
                sims += 1
        best = self._most_visited(root, legal)
        elapsed = perf_counter() - t0
        self._stats = SearchStats(
            nodes=sims,
            time_s=elapsed,
            depth_reached=self._max_depth,
            extra={
                "sims_per_s": sims / elapsed if elapsed > 0 else 0.0,
                "max_tree_depth": float(self._max_depth),
            },
        )
        return best

    @staticmethod
    def _most_visited(root: Node, legal: list[int]) -> int:
        best_m, best_n = legal[0], -1
        for m, ch in root.children.items():
            if ch.N > best_n:
                best_m, best_n = m, ch.N
        return best_m

    def _candidates(self) -> list[int]:
        r = self.config.candidate_radius
        moves = self._tb.legal_moves() if r is None else self._tb.candidate_moves(r)
        return moves or self._tb.legal_moves()

    def _select_child(self, node: Node) -> Node:
        cfg = self.config
        explore = cfg.c_uct * sqrt(log(node.N))
        best: Node | None = None
        best_score = -1.0
        if cfg.rave:
            beta = sqrt(cfg.rave_k / (3 * node.N + cfg.rave_k))
            for ch in node.children.values():
                q = ch.W / ch.N
                if ch.rn:
                    q = (1 - beta) * q + beta * (ch.rw / ch.rn)
                s = q + explore / sqrt(ch.N)
                if s > best_score:
                    best, best_score = ch, s
        else:
            for ch in node.children.values():
                s = ch.W / ch.N + explore / sqrt(ch.N)
                if s > best_score:
                    best, best_score = ch, s
        assert best is not None
        return best

    def _simulate(self, root: Node) -> None:
        tb, sb, win = self._tb, self._sb, self._win
        node = root
        seq: list[int] = []
        while not node.terminal:
            if node.untried is None:
                node.untried = self._candidates()
            if node.untried:
                u = node.untried
                i = int(self._next_draw() * len(u))
                m = u[i]
                u[i] = u[-1]
                u.pop()
                mover = tb.to_move
                tb.make(m)
                sb.make(m)
                if win is not None:
                    win.place(m, mover, 1)
                child = Node(m, node, mover, tb.is_terminal)
                node.children[m] = child
                seq.append(m)
                node = child
                break
            node = self._select_child(node)
            m = node.move
            mover = tb.to_move
            tb.make(m)
            sb.make(m)
            if win is not None:
                win.place(m, mover, 1)
            seq.append(m)
        depth = len(seq)
        if depth > self._max_depth:
            self._max_depth = depth
        self._backprop(node, seq, depth, self._evaluate_leaf(node, seq))
        for m in reversed(seq):
            sb.unmake_move()
            if win is not None:
                win.place(m, sb.to_move, -1)
        for _ in range(depth):
            tb.unmake_move()

    def _evaluate_leaf(self, node: Node, seq: list[int]) -> float:
        """Reward in [0, 1] for ``node.player`` of the position at the leaf.

        Subclasses override this to replace the rollout. The scratch board
        `self._sb` and the tree board `self._tb` both sit at the leaf position
        and must be left unchanged. ``seq`` holds the moves played from the
        root and may be extended with simulated moves for AMAF updates.
        """
        if not node.terminal:
            self._rollout(seq)
        winner = self._sb.winner
        return 1.0 if winner == node.player else 0.5 if winner == EMPTY else 0.0

    def _rollout(self, seq: list[int]) -> None:
        sb, win = self._sb, self._win
        cap = self.config.max_rollout_depth
        empties = sb.empty_cells
        draws, di = self._draws, self._di
        steps = 0
        while not sb.is_terminal and (cap is None or steps < cap):
            player = sb.to_move
            m = -1
            if win is not None and (win.tx or win.to):
                cells = win.winning_cells(player) or win.winning_cells(-player)
                if cells:
                    m = cells[0]
            if m < 0:
                if di >= _DRAWS:
                    draws = self._draws = self.rng.random(_DRAWS).tolist()
                    di = 0
                m = empties[int(draws[di] * len(empties))]
                di += 1
            sb.make(m)
            if win is not None:
                win.place(m, player, 1)
            seq.append(m)
            steps += 1
        self._di = di

    def _backprop(self, leaf: Node, seq: list[int], depth: int, reward: float) -> None:
        rave = self.config.rave
        lp = leaf.player
        node: Node | None = leaf
        d = depth
        while node is not None:
            node.N += 1
            r = reward if node.player == lp else 1.0 - reward
            node.W += r
            if rave and node.children:
                rt = 1.0 - r
                kids = node.children
                for m in seq[d::2]:
                    c = kids.get(m)
                    if c is not None:
                        c.rn += 1
                        c.rw += rt
            node = node.parent
            d -= 1
