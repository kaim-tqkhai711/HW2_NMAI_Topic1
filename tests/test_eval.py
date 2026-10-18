import subprocess
import sys
import textwrap
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from agents.alphabeta import AlphaBetaAgent
from agents.base import Agent, SearchStats
from agents.mcts import MCTSAgent
from agents.presets import AB_FULL, AB_PLAIN, MCTS_RANDOM
from agents.random_agent import RandomAgent
from core.board import Board
from core.rules import GameConfig
from eval.elo import bootstrap_elo, fit_elo, games_from_records
from eval.puzzles import (
    CATEGORIES,
    Puzzle,
    classify,
    load_puzzles,
    run_puzzles,
    save_puzzles,
)
from eval.stats import first_move_win_rate, head_to_head, outcome, wilson_ci
from eval.tournament import (
    GameRecord,
    RegistryFactory,
    adapt_for_nodes,
    make_opening,
    max_workers,
    play_game,
    read_records,
    round_robin,
)
from tests.positions import (
    MUST_BLOCK_74,
    WIN_IN_1_74,
    WIN_IN_3_A_74,
    WIN_IN_3_B_95,
)

ROOT = Path(__file__).resolve().parent.parent
SMALL = GameConfig(4, 3)


# ---------------------------------------------------------------- stats
def test_wilson_reference_values() -> None:
    lo, hi = wilson_ci(50, 100)
    assert (round(lo, 3), round(hi, 3)) == (0.404, 0.596)
    lo, hi = wilson_ci(0, 10)
    assert lo == 0.0 and 0.25 < hi < 0.30
    lo, hi = wilson_ci(10, 10)
    assert hi == 1.0 and 0.70 < lo < 0.75
    assert wilson_ci(0, 0) == (0.0, 1.0)


def test_outcome_counts_draws_as_half() -> None:
    o = outcome(30, 40, 30)
    assert o.score == 0.5 and o.games == 100
    assert o.ci == wilson_ci(50, 100)


def _rec(x: str, o: str, result: int, n: int = 7) -> GameRecord:
    return GameRecord("g", {"n": n, "k": 4, "exact_k": False}, x, o, 0, [], [], result, 0.0, 0, 1.0)


def test_head_to_head_and_first_move_rates() -> None:
    recs = [_rec("a", "b", 1), _rec("b", "a", 1), _rec("a", "b", 0), _rec("b", "a", -1),
            _rec("a", "c", 1)]
    h = head_to_head(recs, "a", "b")
    assert (h.wins, h.draws, h.losses) == (2, 1, 1)
    fm = first_move_win_rate(recs + [_rec("a", "b", -1, n=9)])
    assert fm["7x7 k=4"].wins == 3 and fm["7x7 k=4"].draws == 1 and fm["7x7 k=4"].losses == 1
    assert fm["9x9 k=4"].losses == 1


# ----------------------------------------------------------------- elo
def _simulate(true: dict[str, float], per_pair: int, seed: int) -> list[tuple[str, str, float]]:
    rng = np.random.default_rng(seed)
    games = []
    names = list(true)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            p = 1 / (1 + 10 ** ((true[b] - true[a]) / 400))
            q = (p - 0.1) / 0.8
            for _ in range(per_pair):
                u = rng.random()
                s = 0.5 if u < 0.2 else (1.0 if rng.random() < q else 0.0)
                games.append((a, b, s))
    return games


def test_elo_recovers_synthetic_ratings() -> None:
    true = {"random": 0.0, "a": 120.0, "b": 260.0, "c": 330.0, "d": -40.0}
    fit = fit_elo(_simulate(true, 1500, seed=1), anchor="random")
    assert fit["random"] == 0.0
    for k, v in true.items():
        assert abs(fit[k] - v) <= 25, (k, fit[k], v)


def test_elo_unanchored_is_centred_and_finite_for_unbeaten_agent() -> None:
    games = [("a", "b", 1.0)] * 10 + [("b", "c", 0.5)] * 10 + [("a", "c", 1.0)] * 10
    fit = fit_elo(games, anchor=None)
    assert abs(sum(fit.values())) < 1e-6
    assert all(np.isfinite(v) for v in fit.values()) and fit["a"] > fit["b"]


def test_bootstrap_interval_brackets_estimate_and_truth() -> None:
    true = {"random": 0.0, "a": 150.0, "b": 300.0}
    games = _simulate(true, 400, seed=2)
    res = bootstrap_elo(games, anchor="random", n_boot=200, seed=3)
    for k, (r, lo, hi) in res.items():
        assert lo <= r <= hi
        assert lo - 5 <= true[k] <= hi + 5
    assert res["random"][1:] == (0.0, 0.0)
    assert res == bootstrap_elo(games, anchor="random", n_boot=200, seed=3)


# ---------------------------------------------------------- tournament
class _Sleeper(Agent):
    """Agent that always takes `delay` seconds."""

    def __init__(self, delay: float) -> None:
        super().__init__(0)
        self.delay = delay

    def select_move(self, board: Board, time_budget_s: float) -> int:
        time.sleep(self.delay)
        return board.legal_moves()[0]

    def last_stats(self) -> SearchStats:
        return SearchStats(nodes=10, time_s=self.delay)


def test_play_game_records_everything() -> None:
    cfg = GameConfig(5, 4)
    opening = make_opening(cfg, 0, 0)
    rec = play_game(RandomAgent(1), RandomAgent(2), cfg, 0.1, 7, opening, game_id="g1")
    b = Board(cfg)
    for m in opening:
        b.make(m)
    assert rec.opening == [list(b.to_rc(m)) for m in opening]
    for r, c in (mv.move for mv in rec.moves):
        b.make(b.from_rc(r, c))
    assert b.is_terminal and rec.result == b.winner
    assert rec.violations == 0 and rec.wall_time_s >= 0 and rec.game_id == "g1"
    assert all(m.nodes_per_s >= 0 for m in rec.moves)
    again = GameRecord.from_json(rec.to_json())
    assert again == rec


def test_budget_violation_is_flagged_at_one_and_a_half_times() -> None:
    cfg = GameConfig(3, 3)
    slow = play_game(_Sleeper(0.08), RandomAgent(0), cfg, 0.04, 0)
    n_slow = sum(1 for i in range(len(slow.moves)) if i % 2 == 0)
    assert slow.violations == n_slow > 0
    ok = play_game(_Sleeper(0.04), RandomAgent(0), cfg, 0.04, 0)
    assert ok.violations == 0


def test_illegal_or_board_mutating_agents_are_rejected() -> None:
    class Cheater(Agent):
        def select_move(self, board: Board, time_budget_s: float) -> int:
            board.make(board.legal_moves()[0])
            return board.legal_moves()[0]

        def last_stats(self) -> SearchStats:
            return SearchStats()

    with pytest.raises(RuntimeError):
        play_game(Cheater(), RandomAgent(0), GameConfig(3, 3), 1.0, 0)


def test_openings_are_deterministic_central_and_not_terminal() -> None:
    for cfg in (GameConfig(7, 4), GameConfig(9, 5), GameConfig(3, 3)):
        sizes = set()
        for i in range(30):
            o = make_opening(cfg, 5, i)
            assert o == make_opening(cfg, 5, i)
            assert 2 <= len(o) <= 4 and len(set(o)) == len(o)
            sizes.add(len(o))
            r = max(1, cfg.n // 4)
            for m in o:
                assert abs(m // cfg.n - cfg.n // 2) <= r and abs(m % cfg.n - cfg.n // 2) <= r
        assert sizes == {2, 3, 4}
    assert make_opening(GameConfig(7, 4), 5, 0) != make_opening(GameConfig(7, 4), 6, 0)


FACTORIES = {"random": RegistryFactory("random"), "mcts_random": RegistryFactory("mcts_random")}


def test_mini_tournament_runs_end_to_end_with_two_workers(tmp_path: Path) -> None:
    assert max_workers() >= 1
    out = tmp_path / "games.jsonl"
    recs = round_robin(FACTORIES, SMALL, 0.05, 4, n_workers=2, seed=1, out_path=out)
    assert len(recs) == 4 and len({r.game_id for r in recs}) == 4
    assert sorted((r.agent_x, r.agent_o) for r in recs).count(("random", "mcts_random")) == 2
    assert len(read_records(out)) == 4
    # each opening appears with both colour assignments
    by_opening: dict[str, set[str]] = {}
    for r in recs:
        by_opening.setdefault(str(r.opening), set()).add(r.agent_x)
    assert all(v == {"random", "mcts_random"} for v in by_opening.values())
    again = round_robin(FACTORIES, SMALL, 0.05, 4, n_workers=2, seed=1, out_path=out)
    assert [r.game_id for r in again] == [r.game_id for r in recs]
    assert len(out.read_text().splitlines()) == 4


def test_resume_repairs_truncated_line_and_adds_only_missing_games(tmp_path: Path) -> None:
    out = tmp_path / "g.jsonl"
    full = round_robin(FACTORIES, SMALL, 0.05, 4, n_workers=1, seed=2, out_path=out)
    lines = out.read_text().splitlines()
    out.write_text("\n".join(lines[:2]) + "\n" + lines[2][: len(lines[2]) // 2], encoding="utf-8")
    resumed = round_robin(FACTORIES, SMALL, 0.05, 4, n_workers=1, seed=2, out_path=out)
    ids = [r.game_id for r in read_records(out)]
    assert len(ids) == 4 and len(set(ids)) == 4
    assert {r.game_id for r in resumed} == {r.game_id for r in full}


def test_killing_a_running_tournament_and_restarting_completes_without_duplicates(
    tmp_path: Path,
) -> None:
    out = tmp_path / "killed.jsonl"
    script = tmp_path / "run.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(ROOT)!r})
            from pathlib import Path
            from core.rules import GameConfig
            from eval.tournament import RegistryFactory, round_robin

            if __name__ == "__main__":
                f = {{"random": RegistryFactory("random"),
                      "mcts_random": RegistryFactory("mcts_random")}}
                round_robin(f, GameConfig(4, 3), 0.4, 8, n_workers=1, seed=3,
                            out_path=Path({str(out)!r}))
            """
        ),
        encoding="utf-8",
    )
    proc = subprocess.Popen([sys.executable, str(script)], cwd=ROOT)
    deadline = time.time() + 60
    while time.time() < deadline:
        if out.exists() and out.read_text().count("\n") >= 2:
            break
        time.sleep(0.05)
    proc.kill()
    proc.wait()
    done_before = len(out.read_text().splitlines())
    assert 1 <= done_before < 8
    recs = round_robin(FACTORIES, SMALL, 0.4, 8, n_workers=1, seed=3, out_path=out)
    ids = [r.game_id for r in read_records(out)]
    assert len(ids) == 8 and len(set(ids)) == 8 and len(recs) == 8


def test_node_budget_wrappers_cap_search_effort() -> None:
    b = Board(GameConfig(7, 4))
    for m in (24, 25, 17):
        b.make(m)
    ab = adapt_for_nodes(AlphaBetaAgent(replace(AB_FULL, max_depth=64)), 3000)
    ab.select_move(b, 1e9)
    assert 0 < ab.last_stats().nodes <= 3000 and ab.last_stats().extra["timed_out"] == 1.0
    plain = adapt_for_nodes(AlphaBetaAgent(replace(AB_PLAIN, max_depth=8)), 500)
    mv = plain.select_move(b, 1e9)
    assert plain.last_stats().nodes <= 500 and mv in b.legal_moves()
    mc = adapt_for_nodes(MCTSAgent(MCTS_RANDOM), 321)
    mc.select_move(b, 1e9)
    assert mc.last_stats().nodes == 321
    with pytest.raises(TypeError):
        adapt_for_nodes(_Sleeper(0.0), 10)


def test_node_budget_tournament_is_deterministic(tmp_path: Path) -> None:
    kw = dict(config=SMALL, time_budget_s=0.0, games_per_pair=2, n_workers=1, seed=4,
              budget_mode="nodes", node_budget=100)
    fac = {"random": RegistryFactory("random"), "ab": RegistryFactory("ab_full"),
           "mcts": RegistryFactory("mcts_random")}
    a = round_robin(fac, **kw)  # type: ignore[arg-type]
    b = round_robin(fac, **kw)  # type: ignore[arg-type]
    assert len(a) == 6
    assert [[m.move for m in r.moves] for r in a] == [[m.move for m in r.moves] for r in b]
    assert all(r.violations == 0 and r.budget_mode == "nodes" for r in a)
    assert len(games_from_records(a)) == 6


def test_round_robin_argument_validation() -> None:
    with pytest.raises(ValueError):
        round_robin(FACTORIES, SMALL, 0.1, 3)
    with pytest.raises(ValueError):
        round_robin(FACTORIES, SMALL, 0.1, 2, budget_mode="bogus")


# ------------------------------------------------------------- puzzles
def test_classify_matches_hand_verified_positions() -> None:
    assert classify(WIN_IN_1_74.board()) == ("win_in_1", set(WIN_IN_1_74.best))
    assert classify(MUST_BLOCK_74.board()) == ("block", set(MUST_BLOCK_74.best))
    assert classify(WIN_IN_3_A_74.board()) == ("win_in_3", set(WIN_IN_3_A_74.best))
    assert classify(WIN_IN_3_B_95.board()) == ("win_in_3", set(WIN_IN_3_B_95.best))
    assert classify(Board(GameConfig(7, 4))) is None


def _puzzle(pos_name: str, cat: str, pos: object) -> Puzzle:
    from tests.positions import Pos

    assert isinstance(pos, Pos)
    return Puzzle(pos_name, pos.cfg, pos.grid, pos.to_move, pos.best, cat)


class _Oracle(Agent):
    def __init__(self, table: dict[str, int]) -> None:
        super().__init__(0)
        self.table = table

    def select_move(self, board: Board, time_budget_s: float) -> int:
        return self.table[str(board)]

    def last_stats(self) -> SearchStats:
        return SearchStats()


def test_puzzle_json_round_trip_and_scoring(tmp_path: Path) -> None:
    ps = [
        _puzzle("a", "win_in_1", WIN_IN_1_74),
        _puzzle("b", "block", MUST_BLOCK_74),
        _puzzle("c", "win_in_3", WIN_IN_3_A_74),
    ]
    path = tmp_path / "p.json"
    save_puzzles(ps, path)
    loaded = load_puzzles(path)
    assert loaded == ps
    assert '"correct": [' in path.read_text() and "[\n  [" not in path.read_text()[:3]
    good = {str(p.make_board()): min(p.correct) for p in ps}
    acc = run_puzzles(_Oracle(good), 0.1, ps)
    assert acc == {"win_in_1": 1.0, "block": 1.0, "win_in_3": 1.0, "all": 1.0}
    bad = {str(p.make_board()): max(set(range(p.config.n**2)) - set(p.correct)) for p in ps}
    assert run_puzzles(_Oracle(bad), 0.1, ps)["all"] == 0.0
    ab = AlphaBetaAgent(replace(AB_FULL, max_depth=4))
    assert run_puzzles(ab, 5.0, ps)["all"] == 1.0


def test_shipped_puzzle_file_is_complete_and_correct() -> None:
    path = ROOT / "experiments" / "puzzles.json"
    ps = load_puzzles(path)
    assert len(ps) == 30
    counts: dict[tuple[int, str], int] = {}
    for p in ps:
        counts[(p.config.n, p.category)] = counts.get((p.config.n, p.category), 0) + 1
        b = p.make_board()
        assert b.to_move == p.to_move
        cat, correct = classify(b)  # type: ignore[misc]
        assert cat == p.category and correct == set(p.correct)
    assert counts == {(n, c): 5 for n in (7, 9) for c in CATEGORIES}
    assert len({p.id for p in ps}) == 30
