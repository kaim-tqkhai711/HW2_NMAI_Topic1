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

## Per cell (hours)

| config | cell | hours |
|---|---|---|
| ablation_ab | 9x5@0.5 | 0.13 |
| ablation_mcts | 9x5@0.5 | 0.35 |
| scaling | 7x4@0.5 | 0.01 |
| scaling | 9x5@0.5 | 0.04 |
| scaling | 11x5@0.5 | 0.04 |
| main_7x7 | 7x4@0.5 | 0.28 |
| main_9x9 | 9x5@0.1 | 0.48 |
| main_9x9 | 9x5@0.5 | 2.16 |
| main_9x9 | 9x5@1 | 3.89 |
| main_11x11 | 11x5@0.5 | 0.61 |
| failure_mining | 7x4@0.1 | 0.00 |
| nodes_budget | 7x4@2000 | 0.91 |
| nodes_budget | 7x4@10000 | 4.49 |
| nodes_budget | 9x5@2000 | 3.90 |

## Per config

| config | games hours | + extras | total |
|---|---|---|---|
| ablation_ab | 0.13 | 0.13 | 0.27 |
| ablation_mcts | 0.35 | 0.00 | 0.35 |
| scaling | 0.09 | 0.00 | 0.09 |
| main_7x7 | 0.28 | 0.00 | 0.28 |
| main_9x9 | 6.54 | 0.07 | 6.60 |
| main_11x11 | 0.61 | 0.00 | 0.61 |
| failure_mining | 0.00 | 0.00 | 0.00 |
| nodes_budget | 9.30 | 0.00 | 9.30 |
| **all** | | | **17.5** |

## Chunks (each <= 6 h, run in this order; all resumable)

| # | est. h | command |
|---|---|---|
| 1 | 0.3 | `python -m experiments.run --config experiments/configs/ablation_ab.yaml --run-dir results/ablation_ab/full --only 9x5@0.5 --workers 10 --extras` |
| 2 | 0.3 | `python -m experiments.run --config experiments/configs/ablation_mcts.yaml --run-dir results/ablation_mcts/full --only 9x5@0.5 --workers 10` |
| 3 | 0.1 | `python -m experiments.run --config experiments/configs/scaling.yaml --run-dir results/scaling/full --only 7x4@0.5 9x5@0.5 11x5@0.5 --workers 10` |
| 4 | 0.3 | `python -m experiments.run --config experiments/configs/main_7x7.yaml --run-dir results/main_7x7/full --only 7x4@0.5 --workers 10` |
| 5 | 2.6 | `python -m experiments.run --config experiments/configs/main_9x9.yaml --run-dir results/main_9x9/full --only 9x5@0.1 9x5@0.5 --workers 10` |
| 6 | 4.0 | `python -m experiments.run --config experiments/configs/main_9x9.yaml --run-dir results/main_9x9/full --only 9x5@1 --workers 10 --extras` |
| 7 | 0.6 | `python -m experiments.run --config experiments/configs/main_11x11.yaml --run-dir results/main_11x11/full --only 11x5@0.5 --workers 10` |
| 8 | 0.0 | `python -m experiments.run --config experiments/configs/failure_mining.yaml --run-dir results/failure_mining/full --only 7x4@0.1 --workers 10` |
| 9 | 5.4 | `python -m experiments.run --config experiments/configs/nodes_budget.yaml --run-dir results/nodes_budget/full --only 7x4@2000 7x4@10000 --workers 10` |
| 10 | 3.9 | `python -m experiments.run --config experiments/configs/nodes_budget.yaml --run-dir results/nodes_budget/full --only 9x5@2000 --workers 10` |

Resume after an interruption by re-running the same command: finished game ids
are skipped and a truncated last JSONL line is repaired. When all chunks of a
config are done, `python -m experiments.plots` etc. pick up `results/<config>/full`.
