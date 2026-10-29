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
| P7 experiments | chunks 1-6 done | full runs of ablation_ab, ablation_mcts, scaling, main_7x7, main_9x9 finished (`results/FULL_RUN_SUMMARY.md`); chunks 7-10 pending |
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

## Follow-ups after P8

### Tactical root check (TAC variants)
`MCTSConfig.tactical_root_check` (default False). At the root only: an immediate win is
returned without search (stats: nodes=0, `extra["tactical"]=1`); otherwise, if the opponent
has immediate wins, the root expands only the blocking moves. Threat detection is
`WindowTracker.winning_cells` from `agents/alphabeta.py` (not duplicated). Presets in separate
dicts (`MCTS_TAC_PRESETS`, `HYBRID_TAC_PRESETS`) so the original variants and their
parametrised tests are untouched: `mcts_heuristic_tac`, `mcts_rave_tac`, `mcts_eval_tac`,
`mcts_ab_tac`. Hybrids had no equivalent root check, hence their TAC versions. Test: block found
in 20/20 seeds at <= 500 simulations on 7x7 and 9x9 (5 seeds for `mcts_ab_tac`, whose
simulations are ~50x slower). The existing 3,000/8,000-simulation tests are unchanged.
Added to `main_tournament`, `nodes_budget` (for symmetry with main) and `ablation_mcts`.

### Solver reporting
`results/solve.csv` columns: `n,k,variant,early_stop,value,nodes,time_s,solved`. Full minimax
(`early_stop=0`) is tried first for every (variant, board); if it does not finish in the cap
(120 s no-memo / plain memo, 600 s memo+symmetry) the early-stop run is added as a second row.
Result: (3,3) all three variants solve without early stop (no memo: exactly 549,946 nodes, the
known tree size). (4,3): without early stop only memo+symmetry finishes (29 s); no memo and plain
memo finish only with early stop (79 s / 7.6 s). (4,4): only memo+symmetry finishes (61 s without
early stop; value draw). (5,4): memo+symmetry with early stop, not solved in 600 s.
The 7x7 node-explosion experiment was confirmed to be plain minimax: `BacktrackingAgent` has no
memo, symmetry or cutoff, and every completed depth in `backtracking_growth.csv` equals the closed
form 1 + sum_i prod(N^2 - j) exactly (checked in a test). Not rerun.

### Chunked, resumable runs and the pilot
Runner additions: `--only NxK@budget ...`, `--run-dir`, `--part i/m` (interleaved opening
slices), `--extras`; the summary is rebuilt from the whole `games.jsonl` after every
invocation, so chunks can finish in any order and an interrupted chunk is resumed by re-running
its command. `round_robin(opening_part=(i, m))` does the splitting (game ids unchanged).

Pilot (`experiments/configs/pilot_main.yaml`; 16 agents, 7x7 and 9x9, 0.5 s, 10 games per pair =
2,400 games, 10 workers): **15.3 min**, parallel efficiency 0.98, mean game length only
8.5 plies (7x7) / 16.0 plies (9x9) (X wins 66% / 54%). This is ~3x faster than the runner's
rough estimate (which assumed 3.5N plies), so the estimates in the P7 section above are
superseded by `results/runtime_estimate.md` (`python -m experiments.estimate_runtime`):

| config | est. hours |
|---|---|
| ablation_ab (incl. depth tables) | 0.24 |
| ablation_mcts | 0.31 |
| scaling | 0.11 |
| main_tournament | 8.4 |
| failure_mining | < 0.1 |
| nodes_budget (after dropping the AB-leaf hybrids) | 16.6 |
| **total** | **25.7** |

Model: per-agent seconds/move and nodes/s measured in the pilot, scaled with the budget for
budget-bound agents, plies per game from the pilot (11x11 scaled from 9x9), efficiency from the
pilot; it reproduces the pilot's own time within 10% (in-sample check only).
Estimates are for an otherwise idle machine; they exclude the AB-leaf overshoot fix below.

Run order (each chunk <= 6 h, all idempotent/resumable; commands in `results/runtime_estimate.md`):
1. ablation_ab (0.2 h) 2. ablation_mcts (0.3 h) 3. scaling (0.1 h) 4. main_tournament chunk A: all
7x7 cells + 9x9 @0.1/0.5 (5.0 h) 5. main_tournament chunk B: 9x9 @1.0 + puzzles (3.3 h)
6. failure_mining (minutes) 7-8. nodes_budget 9x9@10000, parts 1/2 and 2/2 (5.6 h each)
9. nodes_budget everything else (5.5 h). Two overnight sessions cover everything (~26 h).

**`nodes_budget` change.** Dropped `mcts_ab` and `mcts_ab_tac`: one simulation of those is a
depth-2 alpha-beta search (~90-210 sims/s), so a node budget is incomparable for them and they were
~80% of the cost (79.5 h -> 16.6 h with budgets [2000, 10000] unchanged).

**Budget violation found by the pilot: FIXED** (commits `14ae2c7`, `fd50e36`; see "Clock fix and
pilot2 gate" below). Original finding: `mcts_ab` / `mcts_ab_tac` exceeded 1.5x the time budget on
12-13 % (7x7) and 68-70 % (9x9) of their moves; cause: the clock was checked every 64 simulations
and an AB-leaf simulation costs 5-10 ms.

### Clock fix and pilot2 gate

* `agents/mcts.py`: the clock is checked every 64 simulations while the running mean cost of a
  simulation is <= 1 ms, and after every simulation otherwise (one adaptive rule, no per-class
  constant). Determinism under `max_iterations` is unchanged. Tests: `tests/test_mcts_clock.py`.
* `eval/tournament.py`: `GameRecord.violations_x / violations_o` count over-budget moves per side;
  `summary.csv` attributes them to the agent that made them (old records are recomputed from move
  wall times). The old `violations` column added both sides' moves to each agent (e.g. `random`
  showed 9 / 79 violations in the first pilot). Test: `test_violations_are_attributed_to_the_slow_agent`.
* Gate: `pilot_main` rerun to `results/pilot_main/pilot2` (0.5 s, 10 games/pair, 2,400 games).
  Rates computed from the wall time of every move: `python -m experiments.violation_rates <run dir> --md`
  (violation = more than 1.5 x budget; "max x" = worst wall time / budget).

| agent | 7x7 before % | 7x7 after % | 9x9 before % | 9x9 after % | max x before (9x9) | max x after (9x9) |
|---|---|---|---|---|---|---|
| mcts_ab | 12.26 | **0.00** | 67.73 | **0.00** | 7.96 | 1.23 |
| mcts_ab_tac | 12.87 | **0.27** | 70.18 | **0.09** | 7.88 | 1.52 |
| all 14 other agents | 0.00 | 0.00 | 0.00 | 0.00 | <= 1.31 | <= 1.28 |

  Result: worst rate over all agents and boards is 0.27 % (< 1 %): **gate passed**. Mean wall time
  per move of `mcts_ab` / `mcts_ab_tac` fell from 0.60 / 0.48 s (7x7) and 1.07 / 1.02 s (9x9) to
  0.51 / 0.40 s and 0.52 / 0.50 s. Their 9x9 Elo dropped from 1528 / 1528 to 950 / 1128 (10 games per
  pair, CI about +-200): the earlier ranking of the two hybrids was inflated by their extra thinking time.
  Caveat: about 2 minutes of `pytest` ran on the same machine during pilot2, so the few
  remaining 1.4-1.5x maxima (`ab_order` 7x7, `mcts_ab_tac`) may include load noise; they stay below 1 %.

### Full runs, chunks 1-6 (29/10/2026)

Details, CIs and tables: `results/FULL_RUN_SUMMARY.md`. All chunks exit 0, 44,160 games, no missing games or fields.

* **Gate failed at 9x5@0.1 s**: 13 of 15 search agents exceed 1.5x budget on 1.2-6.8 % of moves (worst `mcts_ab_tac`
  6.79 %); the overshoot is an absolute ~56-77 ms for every agent (the agent's own clock agrees). 7x4@0.5, 9x5@0.5
  and 9x5@1.0 pass (worst 0.03 %). The `mcts_ab*` clock fix holds at 0.5 s and 1 s. Cause not isolated (scheduling
  under 10 workers on a hybrid CPU vs coarse clock checks); decision on the 0.1 s cell left to the owner.
* `experiments/failure_cases.py` was scanning non-FULL runs (pilot, quick; 3,264 of 47,424 games) and capped the scan
  at the first 400 lost games in file order (which is why only 2 AB cases were found). Now `full` runs only
  (`--all-runs` to override) and an evenly spread scan; 3 MCTS + 3 AB cases from 44,160 FULL games. All 38 AB candidates
  in the data are `ab_plain`.
* `results/figures/budget_modes.*` still comes from the 264-game quick `nodes_budget` run; it is replaced after chunk 9.
* Findings to keep in the report: only move ordering has a resolvable strength effect among the AB ablations (ID, TT, radius
  indistinguishable at 100 games per cell; benefit of ID/TT does not grow with budget); RAVE helps on 9x9 (0.72 vs plain heuristic)
  but hurts on 7x7 (0.325); TAC helps most at short budgets; AB-vs-MCTS gap shrinks as budget grows and widens with board size.
* nodes/s per move on 9x9@0.5 has no clear two-peak distribution; `ab_order_id_tt` shows a slow shoulder at 0.5-0.6x the main
  peak, consistent with but not proof of P/E-core effects (`results/figures/nps_hist_9x9_0.5.png`).

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
