import csv
import pickle
from pathlib import Path
from typing import Any

import pytest
import yaml

from agents.base import Agent, SearchStats
from agents.mcts import MCTSAgent
from core.board import Board
from core.rules import GameConfig
from eval.tournament import play_game
from experiments import failure_cases, plots, tables
from experiments.run import (
    ConfigFactory,
    apply_quick,
    estimate,
    load_config,
    parse_agents,
    run_experiment,
)

CONFIGS = Path(__file__).resolve().parent.parent / "experiments" / "configs"
NAMES = ["main_tournament", "ablation_ab", "ablation_mcts", "scaling", "nodes_budget"]


def test_all_shipped_configs_load_and_have_a_seed() -> None:
    for name in NAMES:
        cfg = load_config(CONFIGS / f"{name}.yaml")
        assert cfg["name"] == name and isinstance(cfg["seed"], int)
        assert parse_agents(cfg["agents"])


def test_spec_contents_of_configs() -> None:
    main = load_config(CONFIGS / "main_tournament.yaml")
    assert main["boards"] == [[7, 4], [9, 5]] and main["budgets"] == [0.1, 0.5, 1.0]
    assert main["games_per_pair"] == 100
    mcts = load_config(CONFIGS / "ablation_mcts.yaml")
    cs = sorted(a["params"]["c_uct"] for a in mcts["agents"] if isinstance(a, dict)
                and "c_uct" in a["params"])
    assert cs == [0.5, 1.0, 1.414, 2.0]
    assert load_config(CONFIGS / "scaling.yaml")["boards"] == [[7, 4], [9, 5], [11, 5]]
    assert load_config(CONFIGS / "nodes_budget.yaml")["budget_mode"] == "nodes"


def test_quick_mode_shrinks_the_run() -> None:
    for name in NAMES:
        q = apply_quick(load_config(CONFIGS / f"{name}.yaml"))
        assert q["games_per_pair"] == 4 and len(q["budgets"]) == 1 and len(q["boards"]) == 1
        assert "quick" not in q


def test_estimate_is_positive_and_scales_with_games() -> None:
    cfg = load_config(CONFIGS / "main_tournament.yaml")
    a = len(cfg["agents"])
    pairs = a * (a - 1) // 2
    games, secs = estimate(cfg, 4)
    assert games == pairs * 100 * 2 * 3 and secs > 0
    g2, s2 = estimate(apply_quick(cfg), 4)
    assert g2 == pairs * 4 and s2 < secs
    assert {"mcts_heuristic_tac", "mcts_rave_tac"} <= set(cfg["agents"])


def test_config_factory_builds_picklable_variants() -> None:
    fac = ConfigFactory("mcts", "MCTS_HEURISTIC", {"c_uct": 0.5})
    agent = pickle.loads(pickle.dumps(fac))(3)
    assert isinstance(agent, MCTSAgent) and agent.config.c_uct == 0.5 and agent.config.seed == 3
    with pytest.raises(ValueError):
        ConfigFactory("nope", "x")(0)


def _tiny(name: str, tmp: Path) -> Path:
    cfg: dict[str, Any] = yaml.safe_load((CONFIGS / f"{name}.yaml").read_text(encoding="utf-8"))
    cfg.pop("quick", None)
    cfg["boards"] = [[4, 3]]
    cfg["budgets"] = [0.02] if cfg["budget_mode"] == "time" else [40]
    cfg["games_per_pair"] = 2
    keep = {"main_tournament": 4, "nodes_budget": 4, "ablation_ab": 3, "ablation_mcts": 3,
            "scaling": 4}[name]
    cfg["agents"] = cfg["agents"][:keep]
    if name == "scaling":
        cfg["boards"] = [[4, 3], [5, 3]]
    if "puzzles" in cfg:
        cfg["puzzles"] = {"budget": 0.02}
    if "depth_table" in cfg:
        cfg["depth_table"] = {"depth": 1}
    if "depth_scaling" in cfg:
        cfg["depth_scaling"] = {"n": 7, "k": 4, "depths": [1, 2], "cap_s": 5,
                                "agents": ["backtracking", "ab_plain"]}
    path = tmp / f"{name}.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def tiny_results(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("results")
    for name in NAMES:
        run_experiment(_tiny(name, root), results_root=root, n_workers=2, timestamp="t1")
    (root / "solve.csv").write_text(
        "n,k,memo,value,nodes,time_s,solved,symmetry\n"
        "3,3,0,0,96679,0.5,1,0\n4,4,1,,100,1.0,0,1\n4,4,1,0,5572627,50.7,1,1\n",
        encoding="utf-8",
    )
    return root


def test_each_config_produces_all_run_files(tiny_results: Path) -> None:
    for name in NAMES:
        d = tiny_results / name / "t1"
        for f in ("games.jsonl", "config.yaml", "summary.csv", "environment.txt"):
            assert (d / f).stat().st_size > 0, (name, f)
        env = (d / "environment.txt").read_text()
        assert "python:" in env and "git_commit:" in env
    main = tiny_results / "main_tournament" / "t1"
    assert (main / "puzzles.csv").exists()
    abl = tiny_results / "ablation_ab" / "t1"
    assert (abl / "ab_depth.csv").exists() and (abl / "nodes_vs_depth.csv").exists()
    rows = list(csv.DictReader((main / "summary.csv").open()))
    assert {r["agent"] for r in rows} == {"random", "backtracking_d2", "ab_plain", "ab_order"}
    anchor = [r for r in rows if r["agent"] == "random"][0]
    assert float(anchor["elo"]) == 0.0
    assert all(float(r["elo_lo"]) <= float(r["elo"]) <= float(r["elo_hi"]) for r in rows)
    assert all(int(r["games"]) == int(r["wins"]) + int(r["draws"]) + int(r["losses"])
               for r in rows)


def test_resuming_a_run_directory_does_not_duplicate_games(tiny_results: Path) -> None:
    root = tiny_results
    before = (root / "scaling" / "t1" / "games.jsonl").read_text().count("\n")
    run_experiment(_tiny("scaling", root), results_root=root, n_workers=2, timestamp="t1")
    assert (root / "scaling" / "t1" / "games.jsonl").read_text().count("\n") == before


def test_all_figures_are_written_as_pdf_and_png(tiny_results: Path, tmp_path: Path) -> None:
    done = plots.make_all(tiny_results, tmp_path / "figs")
    assert len(done) == len(plots.PLOTS) == 8
    for name, paths in done.items():
        assert len(paths) == 2, name
        assert {p.suffix for p in paths} == {".pdf", ".png"}
        assert all(p.stat().st_size > 1000 for p in paths)
    from PIL import Image

    with Image.open(tmp_path / "figs" / "elo_vs_budget.png") as im:
        assert round(im.info.get("dpi", (0, 0))[0]) == 300


def test_missing_data_skips_figures_gracefully(tmp_path: Path) -> None:
    assert all(not v for v in plots.make_all(tmp_path, tmp_path / "f").values())


def test_all_tables_are_booktabs_latex(tiny_results: Path, tmp_path: Path) -> None:
    files = tables.make_all(tiny_results, tmp_path / "t")
    assert sorted(p.name for p in files) == [
        "ab_ablation.tex", "elo_ranking.tex", "mcts_ablation.tex", "puzzle_accuracy.tex",
        "solve.tex"]
    for p in files:
        text = p.read_text(encoding="utf-8")
        assert "\\toprule" in text and "\\midrule" in text and "\\bottomrule" in text
        assert text.count("\\begin{table}") == text.count("\\end{table}") >= 1
    solve = (tmp_path / "t" / "solve.tex").read_text()
    assert "not solved" in solve and "draw" in solve and "5,572,627" in solve


def test_latex_escaping() -> None:
    assert tables.esc("ab_full & 50%") == r"ab\_full \& 50\%"


# --------------------------------------------------------- failure cases
class _Script(Agent):
    def __init__(self, moves: list[tuple[int, int]]) -> None:
        super().__init__(0)
        self.moves = list(moves)

    def select_move(self, board: Board, time_budget_s: float) -> int:
        return board.from_rc(*self.moves.pop(0))

    def last_stats(self) -> SearchStats:
        return SearchStats()


def _scripted(name_x: str, name_o: str, xs: list[tuple[int, int]],
              os_: list[tuple[int, int]]) -> Any:
    return play_game(_Script(xs), _Script(os_), GameConfig(5, 3), 1.0, 0,
                     names=(name_x, name_o), game_id=f"{name_x}-{name_o}")


def test_mines_an_mcts_miss_of_a_forced_win() -> None:
    # X has (0,0),(0,1) and wins at (0,2) but plays (4,0); O then wins on the diagonal.
    rec = _scripted("mcts_x", "ab_o", [(0, 0), (0, 1), (4, 0)], [(2, 2), (4, 4), (3, 3)])
    assert rec.result == -1
    case = failure_cases.mcts_missed_win(rec)
    assert case is not None and case.ply == 4 and case.played == (4, 0)
    assert "(0, 2)" in case.note
    ok = _scripted("mcts_x", "ab_o", [(0, 0), (0, 1), (0, 2)], [(2, 2), (4, 4)])
    assert failure_cases.mcts_missed_win(ok) is None


def test_mines_an_ab_loss_from_a_winning_evaluation() -> None:
    rec = _scripted("ab_x", "mcts_o", [(2, 2), (2, 3), (4, 4)], [(0, 0), (0, 1), (0, 2)])
    assert rec.result == -1
    case = failure_cases.ab_lost_from_winning_eval(rec)
    assert case is not None and case.ply == 4
    assert failure_cases.ab_lost_from_winning_eval(
        _scripted("mcts_x", "ab_o", [(2, 2), (2, 3), (4, 4)], [(0, 0), (0, 1), (0, 2)])
    ) is None


def test_failure_report_is_rendered(tmp_path: Path) -> None:
    a = _scripted("mcts_x", "ab_o", [(0, 0), (0, 1), (4, 0)], [(2, 2), (4, 4), (3, 3)])
    b = _scripted("ab_x", "mcts_o", [(2, 2), (2, 3), (4, 4)], [(0, 0), (0, 1), (0, 2)])
    ca, cb = failure_cases.mine([a, b])
    text = failure_cases.render(ca, cb)
    assert len(ca) == 1 and len(cb) == 1
    assert "```" in text and "forced win" in text and "its own scale" in text
    empty = failure_cases.render([], [])
    assert empty.count("No example found") == 2
