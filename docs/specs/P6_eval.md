# P6 — Evaluation harness (tournament, Elo, statistics, puzzles)

Do not modify agents/ or core/.

## eval/tournament.py
- `play_game(agent_x, agent_o, config, time_budget_s, seed, opening=None) -> GameRecord`
  with moves (as (r, c) for JSON), result, per-move SearchStats, per-move nodes/s,
  wall time, and budget violations.
- `round_robin(agent_factories, config, time_budget_s, games_per_pair, n_workers,
  seed, budget_mode="time") -> list[GameRecord]`
  - Agents are built from factories inside worker processes.
  - Each pair plays games_per_pair games, half with each color.
  - Balanced openings: 2–4 random pre-placed stones from the seed, each opening played
    with colors swapped.
  - multiprocessing.Pool; `n_workers` default and maximum = physical cores − 1
    (use os.cpu_count() // 2 − 1 as the physical-core estimate if psutil is absent).
  - Results appended incrementally to JSONL; resumable (skip game ids already in file).
  - A move exceeding budget × 1.5 is recorded as a violation.
- `budget_mode="nodes"`: alternative fixed budget per move (nodes for AB, simulations
  for MCTS) to check that conclusions do not depend on machine-load noise. Agents get
  this via a wrapper or config, not by changing the Agent interface; record the
  approach in PROGRESS.md.

## eval/stats.py
Wilson 95% CI (draws as 0.5; also W/D/L separately); first-move win rate per config.

## eval/elo.py
Bradley–Terry MLE Elo, draws as half-wins, RandomAgent anchored at 0; bootstrap 95% CI
(200 resamples of games).

## eval/puzzles.py
- Format (JSON): config, board string, side to move, set of correct moves, category
  ("win_in_1", "block", "win_in_3").
- Generation: random midgame positions; keep those where a deep AB_FULL search
  (generous time) proves a forced win; verify by brute force where feasible.
  Target 30 puzzles across 7×7 k=4 and 9×9 k=5 → experiments/puzzles.json.
- `run_puzzles(agent, time_budget_s) -> accuracy per category`.

## Tests
- Wilson: 50/100 → [0.404, 0.596] (3 decimals).
- Elo fit recovers synthetic ratings within ±25.
- 4-game mini tournament with n_workers=2 runs end to end; killing it mid-run and
  restarting completes without duplicating games.

## Gate
Tests above pass; all tests + mypy green.
