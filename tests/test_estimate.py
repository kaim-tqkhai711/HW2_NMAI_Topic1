from experiments.estimate_runtime import (
    AgentProfile,
    agent_key,
    command,
    move_time,
    plan_chunks,
)


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
