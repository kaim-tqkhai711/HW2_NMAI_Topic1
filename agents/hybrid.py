r"""Hybrid MCTS: the random playout is replaced by a knowledge-based leaf value.

Both variants reuse the whole UCT machinery of `MCTSAgent` and only override how
a freshly expanded leaf is valued. With :math:`s` the evaluation score (from the
side to move at the leaf, positive = good for it) and :math:`\sigma` the scale::

    v = \tanh(s / \sigma)          in [-1, 1]
    reward(mover into leaf) = (1 - v) / 2     in [0, 1]

``eval``: :math:`s` is the static pattern evaluation of `agents.evaluation`.
``ab``: :math:`s` is the value of a shallow alpha-beta search from the leaf
(depth `ab_depth`, candidate radius `ab_radius`); a proven win or loss is passed
on as the exact value :math:`v = \pm 1` instead of being squashed. Squashed
values are clamped to :math:`\pm 0.999`, so an exact reward of 0 or 1 always
means a proof. Terminal leaves get the exact game result, and at the root a
proven win is chosen over any other move.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import tanh
from typing import Literal

from agents.alphabeta import WIN_SCORE, ABConfig, AlphaBetaAgent
from agents.evaluation import EvalWeights, evaluate
from agents.mcts import MCTSAgent, MCTSConfig, Node
from core.rules import EMPTY


_CLAMP = 0.999


@dataclass(frozen=True)
class HybridConfig(MCTSConfig):
    """`MCTSConfig` plus the leaf-valuation settings (``rollout`` is ignored).

    Attributes:
        leaf: "eval" for static evaluation, "ab" for a shallow alpha-beta.
        eval_scale: Scale of the tanh squashing; None means ``10 ** (k - 1)``.
        ab_depth: Plies of the leaf alpha-beta search ("ab" only).
        ab_radius: Candidate radius of the leaf alpha-beta search ("ab" only).
    """

    leaf: Literal["eval", "ab"] = "eval"
    eval_scale: float | None = None
    ab_depth: int = 2
    ab_radius: int = 1


class HybridMCTSAgent(MCTSAgent):
    """MCTS whose leaf value comes from evaluation or shallow alpha-beta.

    Args:
        config: Hybrid configuration; ``config.seed`` seeds the agent.
        weights: Evaluation weights; defaults to `EvalWeights.default(k)`.
    """

    def __init__(
        self, config: HybridConfig | None = None, weights: EvalWeights | None = None
    ) -> None:
        cfg = config or HybridConfig()
        super().__init__(cfg)
        self.hconfig = cfg
        self.weights = weights
        self._ab: AlphaBetaAgent | None = None
        if cfg.leaf == "ab":
            ab_cfg = ABConfig(True, False, False, cfg.ab_radius, cfg.ab_depth)
            self._ab = AlphaBetaAgent(ab_cfg, seed=cfg.seed, weights=weights)

    @property
    def name(self) -> str:
        return "MCTS-AB" if self.hconfig.leaf == "ab" else "MCTS-Eval"

    @staticmethod
    def _most_visited(root: Node, legal: list[int]) -> int:
        """Most visited child, except that a proven win is always taken.

        Squashed leaf values saturate near 1 for many strong moves, so visit
        counts alone can prefer a merely "very good" move over a certain win.
        A child is a proven win if it ends the game in the mover's favour (taken
        first, being the fastest) or its leaf search proved the opponent lost.
        """
        for m, ch in root.children.items():
            if ch.terminal and ch.N and ch.W == ch.N:
                return m
        for m, ch in root.children.items():
            if ch.proven:
                return m
        return MCTSAgent._most_visited(root, legal)

    def _evaluate_leaf(self, node: Node, seq: list[int]) -> float:
        sb = self._sb
        if node.terminal:
            winner = sb.winner
            return 1.0 if winner == node.player else 0.5 if winner == EMPTY else 0.0
        cfg = sb.config
        if self._ab is not None:
            self._ab.select_move(self._tb, 1e9)
            score = self._ab.last_stats().extra["score"]
            if abs(score) > WIN_SCORE // 2:
                node.proven = score < 0
                return 0.0 if score > 0 else 1.0
        else:
            w = self.weights or EvalWeights.default(cfg.k)
            score = float(evaluate(sb.cells_list, cfg, sb.to_move, w))
        scale = self.hconfig.eval_scale or float(10 ** (cfg.k - 1))
        v = max(-_CLAMP, min(_CLAMP, tanh(score / scale)))
        return 0.5 * (1.0 - v)
