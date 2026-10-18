# Project: Generalized Tic-tac-toe (m,n,k-game) AI — CO3061 HW2

## Goal
Implement and rigorously compare Backtracking, Alpha-beta, and MCTS agents on
N×N boards with k-in-a-row win condition. Grading values: correct problem
formulation, originality, challenge, and rigorous comparison — NOT raw playing strength.

## Game definition
- Board N×N, cells ∈ {EMPTY=0, X=1, O=-1}. X moves first.
- Win: k consecutive own stones horizontally, vertically, or diagonally. Overlines
  (more than k) count as a win by default ("freestyle"); `exact_k=True` disables that.
- Draw: board full, no winner.
- Default configs: (3,3), (4,4), (7,4), (9,5), (11,5) as (N,k).

## Tech constraints
- Python 3.10+ (machine runs 3.10.11; mypy targets 3.10). numpy for core logic.
  pygame for GUI. matplotlib for plots. PyYAML for configs.
- No external game/AI libraries.
- Full type hints; `mypy --strict` must pass on core/ and agents/.
- Google-style docstrings on public functions only. No comments on trivial code.
- Deterministic: every stochastic component takes an explicit `seed: int` or
  `np.random.Generator`. Never use the global `random` module state.
- Tests with pytest in `tests/`. Every task must end with all tests green.

## Architecture (do not change interfaces without being asked)
hw2/
├── core/board.py, core/rules.py
├── agents/base.py, random_agent.py, backtracking.py, evaluation.py,
│   alphabeta.py, mcts.py, hybrid.py, presets.py
├── eval/tournament.py, elo.py, puzzles.py, stats.py
├── gui/app.py (+ gui/controller.py)
├── experiments/configs/*.yaml, experiments/run*.py, experiments/plots.py
├── results/
├── docs/specs/P2..P8 *.md
└── tests/

## Design decisions (these OVERRIDE anything conflicting in docs/specs/)
1. Move is a flat int (r*N + c). Use `Board.to_rc` / `Board.from_rc` only for I/O
   (GUI, puzzle files, CSV/JSON output). Specs that write `tuple[int, int]` mean this.
2. Agent is an ABC: `select_move(board, time_budget_s: float) -> int` and
   `last_stats() -> SearchStats`. Time budget is per call, never a constructor arg.
3. SearchStats fields: nodes, time_s, depth_reached, extra (dict[str, float]).
4. `legal_moves()` returns a list[int] copy in unspecified order; empty when terminal.
5. `empty_cells` is a live view without terminal checks; use `is_terminal()`.
6. `candidate_moves(radius)` is tracked lazily and incrementally per radius.
7. `Board.copy(track_candidates: bool = False)`: copies never carry candidate
   counters unless asked. MCTS rollouts run on such scratch copies.
8. Rollout policy: random rollouts sample from `empty_cells`. Candidate restriction
   applies only to MCTS tree expansion and to move generation in search.
9. `unmake_move()` takes no argument and returns the undone move; history is
   `move_history`.
10. Agents must leave the board passed to `select_move` exactly unchanged.

## Working rules
- Before writing code, state a short plan (files touched, interfaces). Then implement.
- Do not modify files outside the task's scope. If an interface seems wrong, record
  the proposal in PROGRESS.md and work around it.
- Performance matters: avoid per-move full-board scans; avoid deep-copying boards in
  search (use make/unmake).
- Tests you write must test against independent references (brute force, known
  values, hand-verified positions) — never against the implementation's own output.
- After implementing, run tests + mypy, and report: what was built, test results,
  measured performance numbers, known limitations.
