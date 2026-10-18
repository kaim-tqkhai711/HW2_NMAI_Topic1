"""Named agent configurations and the seed -> agent registry used by tournaments."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from agents.alphabeta import ABConfig, AlphaBetaAgent
from agents.backtracking import BacktrackingAgent
from agents.base import Agent
from agents.hybrid import HybridConfig, HybridMCTSAgent
from agents.mcts import MCTSAgent, MCTSConfig
from agents.random_agent import RandomAgent

_DEPTH = 4

AB_PLAIN = ABConfig(False, False, False, None, _DEPTH)
AB_ORDER = ABConfig(True, False, False, None, _DEPTH)
AB_ORDER_ID = ABConfig(True, True, False, None, _DEPTH)
AB_ORDER_ID_TT = ABConfig(True, True, True, None, _DEPTH)
AB_FULL = ABConfig(True, True, True, 2, _DEPTH, killer_moves=True)

AB_PRESETS: dict[str, ABConfig] = {
    "AB_PLAIN": AB_PLAIN,
    "AB_ORDER": AB_ORDER,
    "AB_ORDER_ID": AB_ORDER_ID,
    "AB_ORDER_ID_TT": AB_ORDER_ID_TT,
    "AB_FULL": AB_FULL,
}

MCTS_RANDOM = MCTSConfig(rollout="random")
MCTS_HEURISTIC = MCTSConfig(rollout="heuristic")
MCTS_RAVE = MCTSConfig(rollout="heuristic", rave=True)

MCTS_HEURISTIC_TAC = replace(MCTS_HEURISTIC, tactical_root_check=True)
MCTS_RAVE_TAC = replace(MCTS_RAVE, tactical_root_check=True)

MCTS_EVAL = HybridConfig(leaf="eval")
MCTS_AB = HybridConfig(leaf="ab")
MCTS_EVAL_TAC = replace(MCTS_EVAL, tactical_root_check=True)
MCTS_AB_TAC = replace(MCTS_AB, tactical_root_check=True)

HYBRID_PRESETS: dict[str, HybridConfig] = {"MCTS_EVAL": MCTS_EVAL, "MCTS_AB": MCTS_AB}

MCTS_PRESETS: dict[str, MCTSConfig] = {
    "MCTS_RANDOM": MCTS_RANDOM,
    "MCTS_HEURISTIC": MCTS_HEURISTIC,
    "MCTS_RAVE": MCTS_RAVE,
}

# Same algorithms plus the root tactical check (separate dicts keep the originals unchanged).
MCTS_TAC_PRESETS: dict[str, MCTSConfig] = {
    "MCTS_HEURISTIC_TAC": MCTS_HEURISTIC_TAC,
    "MCTS_RAVE_TAC": MCTS_RAVE_TAC,
}
HYBRID_TAC_PRESETS: dict[str, HybridConfig] = {
    "MCTS_EVAL_TAC": MCTS_EVAL_TAC,
    "MCTS_AB_TAC": MCTS_AB_TAC,
}

# Depth cap for time-limited play: iterative deepening stops on the clock first.
_TIMED_DEPTH = 64


def _ab_factory(cfg: ABConfig) -> Callable[[int], Agent]:
    return lambda seed: AlphaBetaAgent(cfg, seed=seed)


def _mcts_factory(cfg: MCTSConfig) -> Callable[[int], Agent]:
    return lambda seed: MCTSAgent(replace(cfg, seed=seed))


def _hybrid_factory(cfg: HybridConfig) -> Callable[[int], Agent]:
    return lambda seed: HybridMCTSAgent(replace(cfg, seed=seed))


AGENT_REGISTRY: dict[str, Callable[[int], Agent]] = {
    "random": lambda seed: RandomAgent(seed=seed),
    "backtracking_d2": lambda seed: BacktrackingAgent(max_depth=2, seed=seed),
    **{name.lower(): _ab_factory(cfg) for name, cfg in AB_PRESETS.items()},
    **{name.lower(): _mcts_factory(cfg) for name, cfg in MCTS_PRESETS.items()},
    **{name.lower(): _hybrid_factory(cfg) for name, cfg in HYBRID_PRESETS.items()},
    **{name.lower(): _mcts_factory(cfg) for name, cfg in MCTS_TAC_PRESETS.items()},
    **{name.lower(): _hybrid_factory(cfg) for name, cfg in HYBRID_TAC_PRESETS.items()},
    "ab_full_timed": _ab_factory(replace(AB_FULL, max_depth=_TIMED_DEPTH)),
}
