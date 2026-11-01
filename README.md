# Generalized tic-tac-toe (m,n,k-game) AI — CO3061 HW2, Topic 1

Backtracking, alpha-beta pruning and MCTS (plus MCTS/evaluation hybrids) on an N×N board with
k-in-a-row (default configs: 3x3 k=3, 4x4 k=4, 7x7 k=4, 9x9 k=5, 11x11 k=5), a pygame GUI, and an
experiment pipeline that compares the agents with Elo, Wilson intervals and colour-swapped openings.

Requires **Python 3.10+** (developed on 3.10.11, Windows 11). All commands are run from the
repository root.

## 1. Install

```
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` pins the exact versions used for the reported results.

## 2. Run the GUI

```
python -m gui.app                       # setup screen: board size, k, mode, agents, time budget
python -m gui.app --load results/gui_saves/<file>.json
python -m gui.app --headless-check      # import + init smoke test (set SDL_VIDEODRIVER=dummy without a display)
```

Modes: human vs human, human vs AI, AI vs AI. Board sizes 3, 4, 7, 9, 11 are offered on the setup
screen. Keys in a game: `U` undo, `R` restart, `M` move numbers, `O` overlay (MCTS visits / values,
alpha-beta scores), `S` step and `A` autoplay (AI vs AI), `C` cancel the AI, `P` screenshot, `Esc` back.

## 3. Tests and type check

```
python -m pytest -q -m "not slow"       # fast subset (213 tests, about 3 minutes)
python -m pytest -q                     # everything (248 tests, about 10 minutes)
python -m mypy                          # mypy --strict on core/ and agents/
```

Tests marked `slow` take more than 10 s each (exhaustive solver values, 9x9 block tests, hybrid
searches). Reference values in the tests are independent of the agents: brute-force minimax, the known
3x3 game-tree size (549,946 nodes), closed-form node counts and hand-verified positions
(`tests/positions.py`, re-derived by an exhaustive search in `tests/test_positions.py`).

## 4. Layout

```
core/         Board (flat int moves, make/unmake, incremental winner check) and rules
agents/       random, backtracking, evaluation, alphabeta, mcts, hybrid, presets (AGENT_REGISTRY)
eval/         tournament (play_game, round_robin, resumable JSONL), elo, puzzles, stats
gui/          pygame app + controller (all game logic, testable without pygame)
experiments/  configs/*.yaml, run.py (runner), plots.py, tables.py, failure_cases.py,
              estimate_runtime.py, violation_rates.py, run_*.py (stand-alone measurements)
scripts/      make_submission.py
results/      measured data (pilots, solver tables, full runs), figures/, tables/
docs/specs/   milestone specs
```

## 5. Experiments

Every experiment is a YAML config in `experiments/configs/`. The runner writes
`results/<config>/<run dir>/{games.jsonl,summary.csv,config.yaml,environment.txt,...}`, is **resumable**
(re-run the same command and finished games are skipped) and can be chunked
(`--only NxK@budget ...`, `--part i/m`). Add `--quick` (4 games per pair, first board and budget) to
test the pipeline, `--dry-run` to print the game count only. Use `--workers 10`: the planned timings
below were measured with 10 workers on a 22-thread machine (`psutil` would otherwise raise the default
cap to the number of physical cores minus one).

| Config | What it measures | Cells (board@budget) | Games/pair | Est. time (10 workers) |
|---|---|---|---|---|
| `ablation_ab.yaml` | alpha-beta presets: node table at fixed depth, nodes-vs-depth, tournament | 9x5@0.5 s | 40 | 0.3 h |
| `ablation_mcts.yaml` | c_uct, rollout type, RAVE, tactical root check, tree reuse | 9x5@0.5 s | 40 | 0.3 h |
| `scaling.yaml` | best AB / MCTS / hybrid on 7x7, 9x9, 11x11 | 7x4, 9x5, 11x5 @0.5 s | 40 | 0.1 h |
| `main_7x7.yaml` | all 16 agents round robin | 7x4@0.5 s | 40 | 0.3 h |
| `main_9x9.yaml` | all 16 agents round robin + puzzle table | 9x5@0.1, 0.5, 1.0 s | 100 | 6.6 h |
| `main_11x11.yaml` | reduced roster (9 agents) | 11x5@0.5 s | 100 | 0.6 h |
| `failure_mining.yaml` | extra games for the failure-case miner | 7x4@0.1 s | 40 | < 0.1 h |
| `nodes_budget.yaml` | same comparison with a node/simulation budget instead of time | 7x4@2000, 7x4@10000, 9x5@2000 | 100 | 9.3 h |

Timings come from `results/runtime_estimate.md` (model fitted to the pilots in
`results/pilot_main/pilot2` and `results/pilot_11x11/pilot`, which also lists the chunk commands in
run order, each chunk at most 6 h). Regenerate it with `python -m experiments.estimate_runtime`.
The estimate was not validated against a full run.

Stand-alone measurements (outputs in `results/`):

| Command | Output | Time |
|---|---|---|
| `python -m experiments.run_solve` | `solve.csv` (exact values of small boards, memo/symmetry ablation) | about 15 min |
| `python -m experiments.run_backtracking_growth` | `backtracking_growth.csv` (node explosion, 7x7 k=4) | about 80 s |
| `python -m experiments.run_ab_ablation` | `ab_ablation.csv` (AB presets, three 9x9 midgames, depth 4) | about 2 min |
| `python -m experiments.run_bench_mcts` | `bench_mcts.csv` (simulations per second) | not re-measured |
| `python -m eval.puzzles` | `experiments/puzzles.json` (30 classified puzzles) | not re-measured |

Fairness check of a run: `python -m experiments.violation_rates results/<config>/full --md` prints, per
agent and board, the share of moves that took more than 1.5 × the time budget (the target is < 1 %;
see `PROGRESS.md` for the pilot numbers).

## 6. Rebuild every figure and table

After the runs of section 5 (the scripts use the latest run directory of each config; `full` sorts last):

```
python -m experiments.plots           # results/figures/*.pdf and *.png (300 dpi)
python -m experiments.tables          # results/tables/*.tex (LaTeX, needs booktabs)
python -m experiments.failure_cases   # results/failure_cases.md
```

| Output | Source |
|---|---|
| `elo_vs_budget`, `h2h_heatmap`, `puzzle_accuracy` | `main_7x7`, `main_9x9`, `main_11x11` |
| `budget_modes` | `main_*` and `nodes_budget` |
| `nodes_vs_depth`, `ablation_ab` | `ablation_ab` |
| `ablation_mcts` | `ablation_mcts` |
| `scaling_winrate` | `scaling` |
| `tables/elo_ranking.tex`, `puzzle_accuracy.tex` | `main_*` |
| `tables/ab_ablation.tex`, `mcts_ablation.tex` | `ablation_ab`, `ablation_mcts` |
| `tables/solve.tex` | `results/solve.csv` |
| `nps_hist_9x9_0.5` (`python -m experiments.nps_hist`) | `main_9x9` (budget 0.5 s) |
| `failure_cases.md` | all `games.jsonl` found under `results/` |

## 7. Submission archive

```
python scripts/make_submission.py --name <TEAM>      # builds HW2_<TEAM>.zip, then verifies it
```

The archive holds the code, tests, docs, README, requirements and the full results (quick-run
directories named `YYYYMMDD-HHMMSS`, caches and `.git` are excluded). The verification step unpacks it
into a temporary directory, creates a fresh virtual environment, installs `requirements.txt` and runs
`pytest -q -m "not slow"` (and `python -m gui.app --headless-check`). Use `--no-verify` to skip it.

```
python scripts/make_submission.py --name <TEAM> --lite   # builds HW2_<TEAM>_lite.zip (< 20 MB)
```

`--lite` leaves out every `games.jsonl[.gz]` larger than 2 MB (the 7x7, 9x9, 9x9 replicate, 11x11 and
node-budget game records); `summary.csv`, `puzzles.csv`, tables, figures, `failure_cases.md` and the logs stay.
`results/OMITTED_DATA.md` inside the archive lists what is missing, with sizes and sha256. The full data is at
**[TODO: link Drive/GitHub Release]**.

**Rebuilding every table and figure from the full data.** Download the files listed in `OMITTED_DATA.md`
into the same paths (keep them as `.jsonl.gz`; all loaders read `.gz` directly), then run

```
python -m experiments.plots
python -m experiments.tables
python -m experiments.failure_cases
python -m experiments.nps_hist
```

`summary.csv` of a run can be rebuilt from its games with
`python -c "from pathlib import Path; import yaml; from experiments.run import write_summary; write_summary(Path('results/main_9x9/full'), yaml.safe_load(open('experiments/configs/main_9x9.yaml')))"`.
Without the large files the same commands still run, but the figures that pool those games
(for example `elo_vs_budget` reads only `summary.csv`, `h2h_heatmap` reads the 7x7 games that are shipped) are
then drawn from what is present.

## 8. Reproducibility

Every stochastic component takes an explicit seed; each run directory stores its config, the git
commit and the environment. Node-budget mode is deterministic; time-budget results depend on the
machine and on its load, so keep it idle and awake during a run (disable sleep, plug in the laptop).
