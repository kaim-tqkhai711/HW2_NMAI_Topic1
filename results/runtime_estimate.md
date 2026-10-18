# Runtime estimate

Pilot: 2400 games, budget 0.5 s, 10 workers, elapsed 15.3 min, summed game wall time 2.50 h, parallel efficiency 0.98.

Mean plies per game: 7x7: 8.5, 9x9: 16.0.

Per-agent time per move at the pilot budget (9x9):

| agent | s/move | fill | nodes/s |
|---|---|---|---|
| ab_full | 0.364 | 0.73 | 8,968 |
| ab_full_timed | 0.402 | 0.80 | 8,949 |
| ab_order | 0.369 | 0.74 | 9,700 |
| ab_order_id_tt | 0.389 | 0.78 | 10,241 |
| ab_plain | 0.504 | 1.01 | 18,219 |
| backtracking_d2 | 0.047 | 0.09 | 129,103 |
| mcts_ab | 1.074 | 2.15 | 210 |
| mcts_ab_tac | 1.020 | 2.04 | 88 |
| mcts_eval | 0.516 | 1.03 | 2,353 |
| mcts_eval_tac | 0.455 | 0.91 | 2,167 |
| mcts_heuristic | 0.530 | 1.06 | 2,240 |
| mcts_heuristic_tac | 0.502 | 1.00 | 1,109 |
| mcts_random | 0.520 | 1.04 | 1,864 |
| mcts_rave | 0.530 | 1.06 | 2,262 |
| mcts_rave_tac | 0.487 | 0.97 | 1,035 |
| random | 0.000 | 0.00 | 0 |

Model check on the pilot itself (in-sample, so it only tests the plumbing): predicted 16.8 min vs measured 15.3 min.


## Per cell (hours, extrapolated)

| config | cell | hours |
|---|---|---|
| ablation_ab | 9x5@0.5 | 0.11 |
| ablation_mcts | 9x5@0.5 | 0.31 |
| scaling | 7x4@0.5 | 0.01 |
| scaling | 9x5@0.5 | 0.04 |
| scaling | 11x5@0.5 | 0.06 |
| main_tournament | 7x4@0.1 | 0.24 |
| main_tournament | 7x4@0.5 | 0.65 |
| main_tournament | 7x4@1 | 1.05 |
| main_tournament | 9x5@0.1 | 0.94 |
| main_tournament | 9x5@0.5 | 2.14 |
| main_tournament | 9x5@1 | 3.26 |
| failure_mining | 7x4@0.1 | 0.00 |
| nodes_budget | 7x4@2000 | 0.55 |
| nodes_budget | 7x4@10000 | 2.69 |
| nodes_budget | 9x5@2000 | 2.24 |
| nodes_budget | 9x5@10000 | 11.16 |

## Per config

| config | games hours | + extras | total |
|---|---|---|---|
| ablation_ab | 0.11 | 0.13 | 0.24 |
| ablation_mcts | 0.31 | 0.00 | 0.31 |
| scaling | 0.11 | 0.00 | 0.11 |
| main_tournament | 8.29 | 0.07 | 8.35 |
| failure_mining | 0.00 | 0.00 | 0.00 |
| nodes_budget | 16.64 | 0.00 | 16.64 |
| **all** | | | **25.7** |

## Chunks (each <= 6 h, run in this order; all resumable)

| # | est. h | command |
|---|---|---|
| 1 | 0.2 | `python -m experiments.run --config experiments/configs/ablation_ab.yaml --run-dir results/ablation_ab/full --only 9x5@0.5 --extras` |
| 2 | 0.3 | `python -m experiments.run --config experiments/configs/ablation_mcts.yaml --run-dir results/ablation_mcts/full --only 9x5@0.5` |
| 3 | 0.1 | `python -m experiments.run --config experiments/configs/scaling.yaml --run-dir results/scaling/full --only 7x4@0.5 9x5@0.5 11x5@0.5` |
| 4 | 5.0 | `python -m experiments.run --config experiments/configs/main_tournament.yaml --run-dir results/main_tournament/full --only 7x4@0.1 7x4@0.5 7x4@1 9x5@0.1 9x5@0.5` |
| 5 | 3.3 | `python -m experiments.run --config experiments/configs/main_tournament.yaml --run-dir results/main_tournament/full --only 9x5@1 --extras` |
| 6 | 0.0 | `python -m experiments.run --config experiments/configs/failure_mining.yaml --run-dir results/failure_mining/full --only 7x4@0.1` |
| 7 | 5.6 | `python -m experiments.run --config experiments/configs/nodes_budget.yaml --run-dir results/nodes_budget/full --only 9x5@10000 --part 1/2` |
| 8 | 5.6 | `python -m experiments.run --config experiments/configs/nodes_budget.yaml --run-dir results/nodes_budget/full --only 9x5@10000 --part 2/2` |
| 9 | 5.5 | `python -m experiments.run --config experiments/configs/nodes_budget.yaml --run-dir results/nodes_budget/full --only 7x4@2000 7x4@10000 9x5@2000` |

Resume after an interruption by re-running the same command: finished game ids
are skipped and a truncated last JSONL line is repaired. When all chunks of a
config are done, `python -m experiments.plots` etc. pick up `results/<config>/full`.
