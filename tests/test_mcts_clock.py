"""The MCTS clock check adapts to the cost of a simulation."""
from time import perf_counter, sleep

from agents.mcts import MCTSAgent, Node
from agents.presets import MCTS_RANDOM
from core.board import Board
from core.rules import GameConfig


class _FakeSim(MCTSAgent):
    """MCTS whose simulation costs a fixed time and does no search."""

    def __init__(self, cost_s: float) -> None:
        super().__init__(MCTS_RANDOM)
        self.cost_s = cost_s

    def _simulate(self, root: Node) -> None:
        if self.cost_s:
            sleep(self.cost_s)


def test_slow_simulations_stop_within_budget_times_1_2() -> None:
    for budget in (0.3, 0.5):
        agent = _FakeSim(0.01)
        b = Board(GameConfig(7, 4))
        t0 = perf_counter()
        agent.select_move(b, budget)
        assert perf_counter() - t0 <= budget * 1.2
        assert 2 <= agent.last_stats().nodes <= budget / 0.01 + 2


def test_slow_simulations_check_the_clock_after_every_one() -> None:
    agent = _FakeSim(0.005)
    agent.select_move(Board(GameConfig(7, 4)), 0.0)
    assert agent.last_stats().nodes == 1


def test_fast_simulations_keep_the_64_simulation_cycle() -> None:
    agent = _FakeSim(0.0)
    agent.select_move(Board(GameConfig(7, 4)), 0.02)
    nodes = agent.last_stats().nodes
    assert nodes >= 64 and nodes % 64 == 0


def test_real_slow_leaf_hybrid_respects_budget() -> None:
    from agents.presets import AGENT_REGISTRY

    agent = AGENT_REGISTRY["mcts_ab"](0)
    b = Board(GameConfig(9, 5))
    for m in (40, 41, 31):
        b.make(m)
    t0 = perf_counter()
    agent.select_move(b, 0.3)
    assert perf_counter() - t0 <= 0.3 * 1.2
