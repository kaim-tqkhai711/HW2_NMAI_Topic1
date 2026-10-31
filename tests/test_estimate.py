from pathlib import Path

from experiments.estimate_runtime import (
    AgentProfile,
    agent_key,
    calibration_factor,
    chunk_times,
    command,
    move_time,
    plan_chunks,
)
from experiments.run import estimate, load_config, selected_cells

CONFIGS = Path("experiments/configs")


def test_budget_bound_agents_scale_with_budget_fixed_cost_agents_do_not() -> None:
    bound = AgentProfile(per_move_s=0.5, fill=1.0, nps=1000.0)
    fixed = AgentProfile(per_move_s=0.05, fill=0.1, nps=1000.0)
    assert move_time(bound, "time", 1.0, 0.5) == 1.0
    assert move_time(fixed, "time", 1.0, 0.5) == 0.05
    assert move_time(fixed, "time", 0.02, 0.5) == 0.02  # never exceeds the budget
    assert move_time(bound, "nodes", 10000, 0.5) == 10.0
    assert move_time(AgentProfile(0.0, 0.0, 0.0), "nodes", 10000, 0.5) == 0.0


def test_agent_key_maps_variants_to_their_base_preset() -> None:
    assert agent_key("mcts_rave_tac") == "mcts_rave_tac"
    assert agent_key({"name": "uct_c0.5", "type": "mcts", "base": "MCTS_HEURISTIC"}) == "mcts_heuristic"


def test_chunks_never_exceed_the_limit_and_cover_every_cell_exactly() -> None:
    cells = [("a", "7x4@0.1", 1.0), ("a", "7x4@0.5", 2.0), ("a", "9x5@0.5", 4.0),
             ("b", "9x5@1", 13.0), ("b", "7x4@1", 0.5)]
    chunks = plan_chunks(cells, {"b": 0.25}, 6.0)
    assert all(c.hours <= 6.0 + 1e-9 for c in chunks)
    # the 13 h cell is split into 3 interleaved opening slices
    big = [c for c in chunks if c.cells == ["9x5@1"]]
    assert sorted(c.part for c in big) == [(1, 3), (2, 3), (3, 3)]
    assert abs(sum(c.hours for c in big) - 13.0) < 1e-9
    covered = sorted((c.config, cell) for c in chunks for cell in c.cells)
    assert sorted({(c, cell) for c, cell, _ in cells}) == sorted(set(covered))
    assert sum(c.extras for c in chunks if c.config == "b") == 1 and chunks[-1].extras
    total = sum(c.hours for c in chunks)
    assert abs(total - (1 + 2 + 4 + 13 + 0.5 + 0.25)) < 1e-9


def test_command_is_resumable_and_targets_a_fixed_run_dir() -> None:
    chunks = plan_chunks([("main_tournament", "9x5@1", 13.0)], {}, 6.0)
    cmd = command(chunks[1])
    assert "--run-dir results/main_tournament/full" in cmd
    assert "--only 9x5@1" in cmd and "--part 2/3" in cmd
    assert "--extras" not in cmd


def test_calibration_factor_hits_its_knots_clamps_and_interpolates_in_log_budget() -> None:
    assert calibration_factor("time", 0.1) == 1.20
    assert calibration_factor("time", 0.5) == 0.90
    assert calibration_factor("time", 1.0) == 0.90
    assert calibration_factor("time", 0.01) == 1.20 and calibration_factor("time", 5.0) == 0.90
    assert abs(calibration_factor("time", (0.1 * 0.5) ** 0.5) - 1.05) < 1e-9  # geometric midpoint
    assert calibration_factor("nodes", 2000) == 0.90 and calibration_factor("nodes", 10000) == 1.21
    assert calibration_factor("nodes", 500) == 0.90 and calibration_factor("nodes", 50000) == 1.21
    assert abs(calibration_factor("nodes", (2000 * 10000) ** 0.5) - 1.055) < 1e-9


def test_estimate_counts_only_the_selected_cells() -> None:
    cfg = load_config(CONFIGS / "main_9x9.yaml")
    pairs = 16 * 15 // 2
    assert estimate(cfg, 10)[0] == pairs * 100 * 3
    games, secs = estimate(cfg, 10, ["9x5@1"])
    assert games == pairs * 100 and selected_cells(cfg, ["9x5@1"]) == [(9, 5, 1.0)]
    assert estimate(cfg, 10, ["9x5@0.1", "9x5@0.5"])[0] == pairs * 100 * 2
    assert estimate(cfg, 10, ["7x4@0.5"]) == (0, 0.0)
    assert secs > 0


def test_chunk_times_pairs_each_start_with_its_end(tmp_path: Path) -> None:
    log = tmp_path / "progress.txt"
    lines = [
        "2026-10-29 02:55:13  chunk 2 (a) START attempt 1",
        "2026-10-29 03:14:21  chunk 2 (a) END attempt 1 exit=0",
        "2026-10-29 03:14:21  chunk 3 (b): free RAM 3.61 GB",
        "2026-10-29 03:14:21  chunk 3 (b) START attempt 1",
        "2026-10-29 03:19:45  chunk 3 (b) END attempt 1 exit=0",
    ]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert chunk_times(log) == {2: 19 * 60 + 8, 3: 5 * 60 + 24}
