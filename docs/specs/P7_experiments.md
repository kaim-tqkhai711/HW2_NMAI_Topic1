# P7 — Experiment runner + plots

Do not modify agents/, core/, eval/.

## Configs (experiments/configs/*.yaml), each with a global seed
- main_tournament.yaml: (7,4), (9,5); budgets [0.1, 0.5, 1.0]; agents: Random,
  Backtracking (depth-limited), AB presets, MCTS (random, heuristic, RAVE), hybrids;
  games_per_pair 100.
- ablation_ab.yaml, ablation_mcts.yaml (c_uct ∈ {0.5, 1.0, 1.414, 2.0}).
- scaling.yaml: best AB vs best MCTS vs best hybrid across N ∈ {7, 9, 11}.
- nodes_budget.yaml: the main comparison repeated with budget_mode="nodes".

## Runner
`python -m experiments.run --config <yaml> [--quick]` →
results/<config_name>/<timestamp>/: games.jsonl, config.yaml, summary.csv,
environment.txt (python version, CPU, git commit hash).
`--quick`: 4 games per pair, single budget. Before any full run, print the estimated
wall time and game count.

## Plots (experiments/plots.py) — matplotlib, PDF + PNG, 300 dpi
1. Elo vs time budget (line per agent, CI error bars).
2. Nodes vs depth (log y): Backtracking vs AB presets + theoretical bound.
3. Win rate of AB_FULL vs best MCTS across N, Wilson CI.
4. Ablation bar charts (nodes at fixed depth; Elo delta).
5. Puzzle accuracy per agent per category.
6. Head-to-head win-rate matrix heatmap.
7. Time-budget vs nodes-budget conclusions side by side.

## Tables
LaTeX booktabs → results/tables/*.tex: solve results, AB ablation, MCTS ablation,
Elo ranking, puzzle accuracy.

## Failure-case mining
Scan games.jsonl: (a) MCTS lost while a forced win existed for it (verify with deep AB);
(b) AB lost from a position its own eval rated winning. Save 3 examples each (moves +
ASCII boards) to results/failure_cases.md.

## Gate
Every config runs with --quick and produces all files, plots, and tables above;
all tests + mypy green. Full-run commands and time estimates recorded in PROGRESS.md.
