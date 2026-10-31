# Runtime estimate

Pilots: `results\pilot_main\pilot2` (2400 games, 15.9 min, 10 workers); `results\pilot_11x11\pilot` (360 games, 3.5 min, 10 workers).
Budget 0.5 s, summed game wall time 3.18 h, parallel efficiency 0.98. Planned runs use 10 workers.

Mean plies per game: 7x7: 8.7, 9x9: 18.1, 11x11: 18.2.

Per-agent time per move at the pilot budget (7x7):

| agent | s/move | fill | nodes/s |
|---|---|---|---|
| ab_full | 0.222 | 0.44 | 5,831 |
| ab_full_timed | 0.225 | 0.45 | 6,068 |
| ab_order | 0.237 | 0.47 | 4,477 |
| ab_order_id_tt | 0.213 | 0.43 | 6,916 |
| ab_plain | 0.507 | 1.01 | 11,085 |
| backtracking_d2 | 0.026 | 0.05 | 114,173 |
| mcts_ab | 0.514 | 1.03 | 398 |
| mcts_ab_tac | 0.404 | 0.81 | 137 |
| mcts_eval | 0.518 | 1.04 | 1,998 |
| mcts_eval_tac | 0.384 | 0.77 | 1,850 |
| mcts_heuristic | 0.522 | 1.04 | 2,588 |
| mcts_heuristic_tac | 0.389 | 0.78 | 1,755 |
| mcts_random | 0.521 | 1.04 | 2,190 |
| mcts_rave | 0.522 | 1.04 | 2,379 |
| mcts_rave_tac | 0.387 | 0.77 | 1,695 |
| random | 0.000 | 0.00 | 0 |

Per-agent time per move at the pilot budget (9x9):

| agent | s/move | fill | nodes/s |
|---|---|---|---|
| ab_full | 0.398 | 0.80 | 5,988 |
| ab_full_timed | 0.435 | 0.87 | 5,698 |
| ab_order | 0.394 | 0.79 | 6,364 |
| ab_order_id_tt | 0.407 | 0.81 | 6,607 |
| ab_plain | 0.509 | 1.02 | 11,033 |
| backtracking_d2 | 0.078 | 0.16 | 75,592 |
| mcts_ab | 0.518 | 1.04 | 125 |
| mcts_ab_tac | 0.498 | 1.00 | 52 |
| mcts_eval | 0.525 | 1.05 | 1,482 |
| mcts_eval_tac | 0.465 | 0.93 | 1,593 |
| mcts_heuristic | 0.507 | 1.01 | 1,334 |
| mcts_heuristic_tac | 0.473 | 0.95 | 767 |
| mcts_random | 0.524 | 1.05 | 1,213 |
| mcts_rave | 0.508 | 1.02 | 1,431 |
| mcts_rave_tac | 0.455 | 0.91 | 729 |
| random | 0.000 | 0.00 | 0 |

Per-agent time per move at the pilot budget (11x11):

| agent | s/move | fill | nodes/s |
|---|---|---|---|
| ab_full | 0.434 | 0.87 | 5,323 |
| ab_order_id_tt | 0.436 | 0.87 | 4,827 |
| backtracking_d2 | 0.146 | 0.29 | 83,351 |
| mcts_ab_tac | 0.509 | 1.02 | 34 |
| mcts_eval | 0.529 | 1.06 | 1,350 |
| mcts_eval_tac | 0.459 | 0.92 | 1,335 |
| mcts_heuristic_tac | 0.476 | 0.95 | 736 |
| mcts_random | 0.522 | 1.04 | 1,122 |
| random | 0.000 | 0.00 | 0 |

Model check on `results\pilot_main\pilot2` (in-sample, so it only tests the plumbing): predicted 17.1 min vs measured 15.9 min.

Model check on `results\pilot_11x11\pilot` (in-sample, so it only tests the plumbing): predicted 3.7 min vs measured 3.5 min.

## Per cell (hours, calibrated)

Pilot-profile model times `calibration_factor` (time budgets: 1.20 at 0.1 s, 0.90 at 0.5 s and 1 s; node budgets: 0.90 at 2,000 and 1.21 at 10,000 nodes, log-linear in between; both measured on full runs).

| config | cell | hours |
|---|---|---|
| ablation_ab | 9x5@0.5 | 0.12 |
| ablation_mcts | 9x5@0.5 | 0.31 |
| scaling | 7x4@0.5 | 0.01 |
| scaling | 9x5@0.5 | 0.03 |
| scaling | 11x5@0.5 | 0.03 |
| main_7x7 | 7x4@0.5 | 0.25 |
| main_9x9 | 9x5@0.1 | 0.58 |
| main_9x9 | 9x5@0.5 | 1.94 |
| main_9x9 | 9x5@1 | 3.50 |
| main_11x11 | 11x5@0.5 | 0.55 |
| failure_mining | 7x4@0.1 | 0.01 |
| nodes_budget | 7x4@2000 | 0.82 |
| nodes_budget | 7x4@10000 | 5.44 |
| nodes_budget | 9x5@2000 | 3.51 |

## Per config

| config | games hours | + extras | total |
|---|---|---|---|
| ablation_ab | 0.12 | 0.13 | 0.25 |
| ablation_mcts | 0.31 | 0.00 | 0.31 |
| scaling | 0.08 | 0.00 | 0.08 |
| main_7x7 | 0.25 | 0.00 | 0.25 |
| main_9x9 | 6.03 | 0.07 | 6.10 |
| main_11x11 | 0.55 | 0.00 | 0.55 |
| failure_mining | 0.01 | 0.00 | 0.01 |
| nodes_budget | 9.76 | 0.00 | 9.76 |
| **all** | | | **17.3** |

## Calibration on the full runs

| config | cell | games | predicted CPU h | actual CPU h | actual / predicted |
|---|---|---|---|---|---|
| ablation_ab | 9x5@0.5 | 840 | 1.29 | 1.76 | 1.36 |
| ablation_mcts | 9x5@0.5 | 1800 | 3.42 | 3.16 | 0.92 |
| scaling | 7x4@0.5 | 240 | 0.12 | 0.11 | 0.87 |
| scaling | 9x5@0.5 | 240 | 0.37 | 0.28 | 0.77 |
| scaling | 11x5@0.5 | 240 | 0.37 | 0.37 | 0.99 |
| main_7x7 | 7x4@0.5 | 4800 | 2.73 | 2.54 | 0.93 |
| main_9x9 | 9x5@0.1 | 12000 | 4.76 | 5.72 | 1.20 |
| main_9x9 | 9x5@0.5 | 12000 | 21.20 | 19.08 | 0.90 |
| main_9x9 | 9x5@1 | 12000 | 38.22 | 34.42 | 0.90 |
| main_11x11 | 11x5@0.5 | 3600 | 5.99 | 5.58 | 0.93 |
| failure_mining | 7x4@0.1 | 240 | 0.04 | 0.04 | 1.01 |
| nodes_budget | 7x4@2000 | 9100 | 8.92 | 7.99 | 0.90 |
| nodes_budget | 7x4@10000 | 9090 | 44.05 | 53.49 | 1.21 |

Elapsed time per chunk (progress log):

| chunk | elapsed min |
|---|---|
| 2 | 19.1 |
| 3 | 5.4 |
| 4 | 15.5 |
| 5 | 150.4 |
| 6 | 210.5 |
| 7 | 34.1 |
| 8 | 0.3 |

## Node-budget calibration (chunk 9, 7x4, 18,190 games)

Method: for each node-budget cell the summed `wall_time_s` of its games is divided by the pilot
model's prediction for the same games (`cell_seconds`, per-agent nodes / pilot nodes-per-second).
The two ratios (0.90 at 2,000 nodes, 1.21 at 10,000) are the knots of `NODES_CAL` and are
interpolated log-linearly in the budget. By pair class at 2,000 nodes the ratio is 0.96 for
alpha-beta vs MCTS, 0.85 for MCTS vs MCTS, 0.66 for alpha-beta vs alpha-beta (iterative deepening
stops below the node budget); at 10,000 nodes MCTS vs MCTS is 1.65 (tree growth lowers nodes/s).
Chunk 9 used 10 workers for 61.5 CPU hours, i.e. the 6.15 h from 14:37 to its last game at 20:46
(parallel efficiency 1.00); the run was then stalled with the last 10 games unfinished until it
was interrupted at 00:04 (cause unknown, the 10 games replay in under 25 s each).

Prediction for 9x5@2000 on 10 workers: **3.5 h** (uncalibrated model 3.9 h;
pessimistic bound with the 10,000-node factor 4.7 h). Caveat: on 9x5 alpha-beta agents fill more of
the node budget than on 7x4, so the true value is likely between the calibrated and the pessimistic figure.
(parallel efficiency used: 0.98)

## Chunks (each <= 6 h, run in this order; all resumable)

| # | est. h | command |
|---|---|---|
| 1 | 0.3 | `python -m experiments.run --config experiments/configs/ablation_ab.yaml --run-dir results/ablation_ab/full --only 9x5@0.5 --workers 10 --extras` |
| 2 | 0.3 | `python -m experiments.run --config experiments/configs/ablation_mcts.yaml --run-dir results/ablation_mcts/full --only 9x5@0.5 --workers 10` |
| 3 | 0.1 | `python -m experiments.run --config experiments/configs/scaling.yaml --run-dir results/scaling/full --only 7x4@0.5 9x5@0.5 11x5@0.5 --workers 10` |
| 4 | 0.2 | `python -m experiments.run --config experiments/configs/main_7x7.yaml --run-dir results/main_7x7/full --only 7x4@0.5 --workers 10` |
| 5 | 2.5 | `python -m experiments.run --config experiments/configs/main_9x9.yaml --run-dir results/main_9x9/full --only 9x5@0.1 9x5@0.5 --workers 10` |
| 6 | 3.6 | `python -m experiments.run --config experiments/configs/main_9x9.yaml --run-dir results/main_9x9/full --only 9x5@1 --workers 10 --extras` |
| 7 | 0.5 | `python -m experiments.run --config experiments/configs/main_11x11.yaml --run-dir results/main_11x11/full --only 11x5@0.5 --workers 10` |
| 8 | 0.0 | `python -m experiments.run --config experiments/configs/failure_mining.yaml --run-dir results/failure_mining/full --only 7x4@0.1 --workers 10` |
| 9 | 0.8 | `python -m experiments.run --config experiments/configs/nodes_budget.yaml --run-dir results/nodes_budget/full --only 7x4@2000 --workers 10` |
| 10 | 5.4 | `python -m experiments.run --config experiments/configs/nodes_budget.yaml --run-dir results/nodes_budget/full --only 7x4@10000 --workers 10` |
| 11 | 3.5 | `python -m experiments.run --config experiments/configs/nodes_budget.yaml --run-dir results/nodes_budget/full --only 9x5@2000 --workers 10` |

Resume after an interruption by re-running the same command: finished game ids
are skipped and a truncated last JSONL line is repaired. When all chunks of a
config are done, `python -m experiments.plots` etc. pick up `results/<config>/full`.
