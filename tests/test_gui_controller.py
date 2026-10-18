import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from agents.alphabeta import AlphaBetaAgent
from agents.base import Agent, SearchStats
from agents.mcts import MCTSAgent, MCTSConfig
from agents.presets import AB_FULL
from agents.random_agent import RandomAgent
from core.board import Board
from core.rules import GameConfig, O, X
from eval.tournament import play_game
from gui.controller import (
    BUDGET_RANGE,
    GameController,
    Mode,
    Setup,
    with_budget,
)


class Slow(Agent):
    """Agent that sleeps, then plays the first legal move."""

    def __init__(self, delay: float) -> None:
        super().__init__(0)
        self.delay = delay

    def select_move(self, board: Board, time_budget_s: float) -> int:
        time.sleep(self.delay)
        return board.legal_moves()[0]

    def last_stats(self) -> SearchStats:
        return SearchStats(nodes=1)


class Broken(Agent):
    def select_move(self, board: Board, time_budget_s: float) -> int:
        raise RuntimeError("boom")

    def last_stats(self) -> SearchStats:
        return SearchStats()


REG: dict[str, Callable[[int], Agent]] = {
    "random": lambda seed: RandomAgent(seed=seed),
    "slow": lambda seed: Slow(0.4),
    "broken": lambda seed: Broken(0),
    "mcts": lambda seed: MCTSAgent(MCTSConfig(max_iterations=200, seed=seed)),
    "ab": lambda seed: AlphaBetaAgent(replace(AB_FULL, max_depth=3), seed=seed),
}


def ctl(mode: Mode = Mode.HUMAN_VS_AI, n: int = 5, k: int = 4, ax: str = "random",
        ao: str = "random") -> GameController:
    return GameController(Setup(n, k, False, mode, ax, ao, 0.2, 1), REG)


def wait_until(c: GameController, cond: Callable[[], bool], timeout: float = 10.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        c.tick()
        if cond():
            return True
        time.sleep(0.005)
    return False


def test_mode_ownership() -> None:
    assert Mode.HUMAN_VS_AI.is_human(X) and not Mode.HUMAN_VS_AI.is_human(O)
    assert not Mode.AI_VS_HUMAN.is_human(X) and Mode.AI_VS_HUMAN.is_human(O)
    assert not Mode.AI_VS_AI.is_human(X) and not Mode.AI_VS_AI.is_human(O)
    assert Mode.HUMAN_VS_HUMAN.is_human(X) and Mode.HUMAN_VS_HUMAN.is_human(O)


def test_human_move_legality() -> None:
    c = ctl(Mode.HUMAN_VS_HUMAN)
    assert c.human_move(2, 2) and c.board.cells_list[12] == X and c.to_move == O
    assert not c.human_move(2, 2)  # occupied
    assert not c.human_move(-1, 0) and not c.human_move(0, 5) and not c.human_move(5, 0)
    assert c.human_move(0, 0) and c.board.cells_list[0] == O
    assert c.moves == (12, 0) and [i.human for i in c.infos] == [True, True]


def test_human_cannot_move_on_ai_turn_or_after_game_over() -> None:
    c = ctl(Mode.AI_VS_HUMAN)
    assert not c.human_move(0, 0) and c.board.ply == 0
    h = ctl(Mode.HUMAN_VS_HUMAN, n=3, k=3)
    for rc in [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2)]:
        assert h.human_move(*rc)
    assert h.is_over and h.winner == X and not h.human_move(2, 2)


def test_ai_replies_through_background_thread() -> None:
    c = ctl(Mode.HUMAN_VS_AI)
    assert not c.request_ai_move()  # human's turn
    assert c.human_move(2, 2)
    assert c.request_ai_move() and c.thinking
    assert not c.request_ai_move()  # already thinking
    assert wait_until(c, lambda: c.board.ply == 2)
    assert not c.thinking and c.infos[1].human is False and c.infos[1].player == O
    assert c.is_human_turn() and c.last_error is None


def test_tick_makes_the_ai_answer_automatically_in_human_modes() -> None:
    c = ctl(Mode.AI_VS_HUMAN)
    assert wait_until(c, lambda: c.board.ply == 1)  # AI (X) opens by itself
    assert c.human_move(0, 0) and wait_until(c, lambda: c.board.ply == 3)


def test_ui_thread_stays_responsive_while_ai_thinks() -> None:
    c = ctl(Mode.HUMAN_VS_AI, ao="slow")
    c.human_move(0, 0)
    t0 = time.time()
    c.request_ai_move()
    assert time.time() - t0 < 0.1 and c.thinking
    assert not c.human_move(1, 1)  # not the human's turn
    assert wait_until(c, lambda: c.board.ply == 2)


def test_cancel_discards_the_result_and_replaces_the_agent() -> None:
    c = ctl(Mode.HUMAN_VS_AI, ao="slow")
    c.human_move(0, 0)
    old = c.agents[O]
    c.request_ai_move()
    c.cancel_ai()
    assert not c.thinking and c.agents[O] is not old
    time.sleep(0.6)  # the abandoned thread finishes meanwhile
    assert not c.poll() and c.board.ply == 1


def test_undo_during_thinking_and_after_moves() -> None:
    c = ctl(Mode.HUMAN_VS_AI, ao="slow")
    assert not c.undo()
    c.human_move(0, 0)
    c.request_ai_move()
    assert c.undo()
    time.sleep(0.6)
    assert not c.poll() and c.board.ply == 0 and c.infos == []
    h = ctl(Mode.HUMAN_VS_HUMAN)
    h.human_move(1, 1)
    h.human_move(2, 2)
    assert h.undo() and h.moves == (6,) and h.to_move == O
    assert h.undo() and h.board.ply == 0 and h.to_move == X


def test_undo_turn_returns_to_the_humans_turn() -> None:
    c = ctl(Mode.HUMAN_VS_AI)
    c.human_move(2, 2)
    c.request_ai_move()
    assert wait_until(c, lambda: c.board.ply == 2)
    c.human_move(0, 0)
    c.request_ai_move()
    assert wait_until(c, lambda: c.board.ply == 4)
    assert c.undo_turn() and c.board.ply == 2 and c.is_human_turn()
    assert c.undo_turn() and c.board.ply == 0 and c.is_human_turn()
    assert not c.undo_turn()


def test_restart_and_mode_switching() -> None:
    c = ctl(Mode.HUMAN_VS_HUMAN)
    c.human_move(0, 0)
    c.restart()
    assert c.board.ply == 0 and c.infos == []
    c.start(Setup(7, 4, False, Mode.AI_VS_AI, "random", "random", 0.2, 2, ))
    assert c.config == GameConfig(7, 4) and c.agents[X] is not None and c.agents[O] is not None
    assert not c.is_human_turn() and c.is_ai_turn()
    c.start(Setup(5, 4, False, Mode.HUMAN_VS_HUMAN, "random", "random", 0.2))
    assert c.agents[X] is None and c.is_human_turn() and not c.request_ai_move()
    with pytest.raises(ValueError):
        c.start(Setup(5, 6, False))  # k > n
    with pytest.raises(ValueError):
        c.start(Setup(5, 4, False, Mode.AI_VS_AI, "nope", "random", 0.2))
    with pytest.raises(ValueError):
        c.start(Setup(5, 4, False, time_budget_s=99.0))


def test_autoplay_runs_ai_vs_ai_to_the_end() -> None:
    c = ctl(Mode.AI_VS_AI)
    c.autoplay_delay_s = 0.0
    c.tick()
    assert c.board.ply == 0 and not c.thinking  # nothing happens without autoplay
    c.autoplay = True
    assert wait_until(c, lambda: c.is_over, timeout=30)
    assert c.winner in (X, O, 0) and all(not i.human for i in c.infos)
    assert not c.request_ai_move()


def test_step_plays_exactly_one_ai_move() -> None:
    c = ctl(Mode.AI_VS_AI)
    assert c.step()
    assert wait_until(c, lambda: c.board.ply == 1)
    time.sleep(0.1)
    c.tick()
    assert c.board.ply == 1


def test_agent_errors_are_reported_not_fatal() -> None:
    c = ctl(Mode.AI_VS_AI, ax="broken", ao="random")
    c.autoplay = True
    c.autoplay_delay_s = 0.0
    assert wait_until(c, lambda: c.last_error is not None)
    assert "boom" in (c.last_error or "") and not c.autoplay and c.board.ply == 0


def test_winning_line_for_all_directions() -> None:
    for moves, expect in [
        ([(0, 0), (4, 4), (0, 1), (4, 3), (0, 2), (3, 3), (0, 3)], [0, 1, 2, 3]),
        ([(0, 0), (0, 4), (1, 0), (1, 4), (2, 0), (2, 3), (3, 0)], [0, 5, 10, 15]),
        ([(0, 0), (0, 4), (1, 1), (1, 4), (2, 2), (2, 3), (3, 3)], [0, 6, 12, 18]),
        ([(0, 3), (0, 0), (1, 2), (1, 0), (2, 1), (2, 4), (3, 0)], [3, 7, 11, 15]),
    ]:
        c = ctl(Mode.HUMAN_VS_HUMAN, n=5, k=4)
        for rc in moves:
            assert c.human_move(*rc)
        assert c.is_over and c.winning_line() == expect, moves
    c = ctl(Mode.HUMAN_VS_HUMAN)
    c.human_move(0, 0)
    assert c.winning_line() == []


def test_save_load_replay_equality(tmp_path: Path) -> None:
    c = ctl(Mode.HUMAN_VS_AI)
    for _ in range(3):
        if c.is_over:
            break
        r, col = divmod(c.board.legal_moves()[0], 5)
        c.human_move(r, col)
        c.request_ai_move()
        wait_until(c, lambda: c.is_human_turn() or c.is_over)
    path = tmp_path / "g.json"
    c.save(path)
    d = ctl(Mode.HUMAN_VS_HUMAN, n=9, k=5)
    d.load(path)
    assert d.moves == c.moves and d.board.hash == c.board.hash
    assert d.config == c.config and d.winner == c.winner
    assert [(i.nodes, i.player) for i in d.infos] == [(i.nodes, i.player) for i in c.infos]
    d.save(tmp_path / "g2.json")
    assert (tmp_path / "g2.json").read_text().count("\n") == 1
    e = ctl()
    e.load(tmp_path / "g2.json")
    assert e.moves == c.moves
    # the side recorded as "human" is a person again, the other one an AI
    assert e.setup.mode is Mode.HUMAN_VS_AI


def test_load_a_tournament_game_record() -> None:
    cfg = GameConfig(6, 4)
    rec = play_game(RandomAgent(1), RandomAgent(2), cfg, 0.1, 5, opening=(14, 15, 21),
                    names=("random", "random"), game_id="t1")
    c = ctl(Mode.HUMAN_VS_HUMAN)
    c.load_record(rec)
    b = Board(cfg)
    for m in (14, 15, 21):
        b.make(m)
    for mv in rec.moves:
        b.make(b.from_rc(*mv.move))
    assert c.moves == b.move_history and c.board.hash == b.hash
    assert c.winner == rec.result and c.is_over
    assert c.setup.mode is Mode.AI_VS_AI and (c.setup.n, c.setup.k) == (6, 4)
    assert len(c.infos) == 3 + len(rec.moves)


def test_loading_rejects_illegal_records_and_unknown_agents_become_human() -> None:
    cfg = GameConfig(5, 4)
    rec = play_game(RandomAgent(1), RandomAgent(2), cfg, 0.1, 5, names=("someone", "other"))
    c = ctl()
    c.load_record(rec)
    assert c.setup.mode is Mode.HUMAN_VS_HUMAN
    rec.moves[1].move = list(rec.moves[0].move)
    with pytest.raises(ValueError):
        c.load_record(rec)


def test_mcts_overlay_and_win_probability() -> None:
    c = ctl(Mode.AI_VS_HUMAN, ax="mcts")
    assert c.overlay("mcts_visits") is None and c.overlay("off") is None
    assert wait_until(c, lambda: c.board.ply == 1)
    visits, values = c.overlay("mcts_visits"), c.overlay("mcts_values")
    assert visits is not None and visits.shape == (5, 5) and visits.sum() > 0
    assert values is not None and np.nanmax(values) <= 1.0
    wp = c.infos[0].win_prob
    assert wp is not None and 0.0 <= wp <= 1.0
    assert c.infos[0].nodes > 0 and c.infos[0].nodes_per_s > 0
    c.human_move(0, 0)  # maps are about an earlier position, but stay available
    assert c.overlay("mcts_visits") is not None
    c.undo()
    c.undo()
    assert c.overlay("mcts_visits") is None


def test_alpha_beta_exposes_pv_and_ab_score_overlay() -> None:
    c = ctl(Mode.AI_VS_HUMAN, ax="ab")
    assert wait_until(c, lambda: c.board.ply == 1)
    info = c.infos[0]
    assert info.pv and info.pv[0] == info.move and info.depth is not None
    h = ctl(Mode.HUMAN_VS_HUMAN, n=7, k=4)
    for rc in [(3, 1), (0, 0), (3, 2), (0, 6), (3, 3), (6, 0)]:
        h.human_move(*rc)
    scores = h.overlay("ab_scores")
    assert scores is not None and scores.shape == (7, 7)
    best = int(np.nanargmax(scores))
    assert best in (3 * 7 + 0, 3 * 7 + 4) and np.nanmax(scores) >= 1e5
    h.human_move(3, 4)
    assert h.overlay("ab_scores") is None  # game over


def test_budget_clamping() -> None:
    s = Setup()
    assert with_budget(s, 99).time_budget_s == BUDGET_RANGE[1]
    assert with_budget(s, 0.0).time_budget_s == BUDGET_RANGE[0]
    assert with_budget(s, 2.5).time_budget_s == 2.5
