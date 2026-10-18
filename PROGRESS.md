# PROGRESS

Status per milestone, deviations from the specs, interface proposals, and the
commands/time estimates for the full experiment runs.

## Milestone status

| Milestone | State | Notes |
|---|---|---|
| P1 core + interface | done (earlier) | `Board.copy(track_candidates=False)` added in P2 Step 0 |
| P2 backtracking + solver | done | gate: (3,3)=0, (4,4)=0 |
| P3 evaluation + alpha-beta | done | value-equality gate passes on 10 fixed positions + 3 midgames |
| P4 MCTS | done | see "block test budget" below |
| P5 hybrids | MCTS_EVAL, MCTS_AB done | MCTS_SOLVER and threat-space search **not built** (see below) |
| P6 eval harness | done | |
| P7 experiments | done | all configs ran with `--quick`; full runs NOT executed |
| P8 GUI | done | headless-tested; visual checks listed below |

## Deviations and decisions worth knowing about

### P2
* **Solver prunes at proven wins.** `experiments/run_solve.py` stops expanding a
  node once a child proves +1 (it cannot be improved on); the stored value is
  still exact. Without this, memoized full-width minimax could not finish (4,3)
  in 100 s. Three modes are reported in `results/solve.csv`: no memo, plain
  Zobrist memo, and memo keyed on the minimum of the 8 symmetric Zobrist hashes
  (extra column `symmetry`). The memo ablation therefore isolates memoization
  and symmetry; the `BacktrackingAgent` itself has no pruning at all.
* **(5,4) is not solved within the 10-minute budget** (62M nodes) and is reported
  as `solved=0`, as the spec requires. (4,4)=0 draw takes ~50 s with symmetric memo.
* The `BacktrackingAgent` scores `±(1e6 − ply)` so that faster wins win ties (needed
  for a stable win-in-1 test); at the depth horizon it returns 0 as specified.
* Memo-free and plain-memo ablation rows use a 120 s cap (`--ablation-timeout`);
  the symmetric-memo rows use the 600 s cap.

### P3
* Immediate-threat logic (win now / forced block / double threat = lost) is part of
  `ABConfig.move_ordering`, so `AB_PLAIN` is pure alpha-beta. The shortcuts only fire
  where plain minimax at the same horizon would see the same result (win shortcut at
  depth ≥ 1, block/double-threat at depth ≥ 2), which is why values match exactly.
* The TT is cleared at the start of every `select_move`. Entries are only reused at
  equal remaining depth within an iteration (a position fixes its ply), which keeps
  `AB_PLAIN` and `AB_FULL` values identical.
* Leaf values differ between `BacktrackingAgent` (0 at the horizon) and AB (static
  evaluation). The "AB_PLAIN == Backtracking on 4×4" test therefore uses all-zero
  `EvalWeights` for the AB agent.
* `WindowTracker` (window stone counts, one-short-of-k sets) is public in
  `agents/alphabeta.py`; MCTS' heuristic rollout reuses it.
* Midgame positions for the ablation table are fixed move sequences in
  `tests/positions.py` (`midgame_positions_95`).

### P4
* **Block-test budget.** The spec does not fix a simulation count for "heuristic MCTS
  blocks in ≥ 95% of 20 seeds". Measured: 1500 sims are not enough (≈40% on 7×7);
  3000 sims give 10/10 on 7×7 and 8000 sims give 10/10 on 9×9 (2/10 at 3000). The
  cause is statistical: after a non-blocking move the opponent's node has ~35
  children, so UCT needs many visits before the single winning reply dominates the
  average. The tests use 3000 sims / 20 seeds (7×7) and 8000 sims / 8 seeds (9×9).
  **Proposal (not implemented):** expand an immediate win / forced block first in the
  tree (not only in rollouts). That would make blocking sample-efficient.
* Rollouts run on one persistent scratch board without candidate trackers (kept in
  lock-step with the tree board by make/unmake) instead of a fresh `copy()` per
  simulation; it satisfies decisions 7–8 and avoids a copy per simulation.
* Heuristic rollout detection uses the incremental `WindowTracker` (O(1) existence
  check, exact, full board) rather than a scan near the last moves.
* RAVE: AMAF statistics live on the child node; β uses the parent's visit count.

### P5
* **Not built:** `MCTS_SOLVER` and the threat-space search. The spec makes them
  optional "only if P2–P4 gates passed first try"; the P4 block test needed a
  budget fix, so the condition was not met. Easy to add later: `Node.proven`
  already exists for hybrids.
* Squashed leaf values are clamped to ±0.999 so an exact 0/1 reward always means a
  proof, and the hybrids choose a proven-win root child before the most-visited one
  (visit counts saturate when many moves have values ≈ 1).

### P6
* **`budget_mode="nodes"` without touching `agents/`:** `adapt_for_nodes` sets
  `max_iterations` on MCTS configs and swaps alpha-beta / backtracking agents for
  subclasses (in `eval/tournament.py`) that raise the agent's own timeout after
  `node_budget` nodes. Time budget is then effectively infinite. `node_budget` is an
  extra `round_robin` keyword (default 20000); `out_path` is another.
* Workers are spawned (Windows); factories must be picklable → `RegistryFactory(name)`.
* Game ids encode (config, mode, seed, pair, opening, colour swap); resume skips ids
  already in the JSONL and repairs a truncated last line.
* Elo adds 0.1 virtual drawn games per agent pair so the MLE stays finite for an
  unbeaten agent.

## Interface proposals

None needed so far. `Board.copy(track_candidates=...)`, `WindowTracker` (public) and
`Node.proven` are the only additions outside their own milestone's files.

## P7: experiments

Run: `python -m experiments.run --config experiments/configs/<name>.yaml [--quick] [--dry-run]`,
then `python -m experiments.plots`, `python -m experiments.tables`,
`python -m experiments.failure_cases`.

Full-run estimates (printed by the runner; rough, 10 workers = 22 logical cores // 2 - 1):

| config | games | est. wall time |
|---|---|---|
| main_tournament | 39,600 | ~15 h |
| nodes_budget | 26,400 | ~38 h (estimate is pessimistic: the quick run took ~1 min vs 6.6 predicted) |
| ablation_ab | 840 | ~19 min (+ depth table: AB_PLAIN depth 4 takes ~1 min per position) |
| ablation_mcts | 1,120 | ~26 min |
| scaling | 720 | ~14 min |
| failure_mining (extra) | 240 | ~1 min (already run once, not quick) |

* `--quick` = 4 games per pair, first budget, first board, plus per-config `quick:` overrides.
* Extra config `failure_mining.yaml` (not in the spec) supplies games for the failure miner.
* Failure cases (`results/failure_cases.md`): 3 MCTS-missed-forced-win examples, but only 1 alpha-beta
  example in the quick data; the full tournament should supply the rest.
* The quick-run data are tiny (4 games per pair): the figures prove the pipeline, not conclusions.
* `experiments/` imports `tests/positions.py` for the fixed midgame positions.
* mypy is clean on `gui/`, `eval/`, `experiments/` except missing PyYAML stubs; strict mode is only configured for core/agents.
* Installed with pip for this milestone: matplotlib 3.10.9, pygame 2.6.1 (see requirements.txt).

Findings visible already: heuristic MCTS is *worse* than random-rollout MCTS on win-in-1 puzzles
at short budgets (many strong moves share value 1.0, so visit counts do not single out the win);
`ab_plain` (non-iterative, depth 4) collapses to the fallback move under a 0.1 s budget.

## P8: GUI

Run: `python -m gui.app [--load saved.json]`; headless smoke test: `python -m gui.app --headless-check`.
Logic is in `gui/controller.py` (tested without pygame); saves are one-line `GameRecord` JSON in
`results/gui_saves/`, screenshots in `results/gui_screenshots/`.

Visual checks for a human (not automatable here):
1. 11x11 board is legible at the default 1000x760 window and after resizing (stones, grid, panel text).
2. AI thinking indicator appears and the window stays responsive; Cancel/Undo during thinking.
3. Winning-line highlight, last-move ring, and the move-number toggle (M).
4. MCTS visit/value overlay and the AB-score overlay (O cycles) are readable over stones.
5. AI-vs-AI Step / Auto / Speed buttons behave; Save then Load restores the position.
6. Setup slider drag and agent < > selectors with a mouse.
Sample screenshots: `results/gui_screenshots/demo_*.png`.
