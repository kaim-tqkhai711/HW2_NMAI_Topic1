# P2 — Backtracking + exact solving

## Step 0 — pending P1 follow-ups (do these first, separate commits)
1. Add `Board.copy(track_candidates: bool = False)`. A default copy carries no
   candidate counters. Test: default copy has no counters, and make/unmake on it
   does no counter work.
2. Add `.gitattributes` with `* text=auto eol=lf`, run `git add --renormalize .`,
   commit as "chore: normalize line endings".

## agents/backtracking.py — BacktrackingAgent
- Plain recursive minimax over `legal_moves()` (NO pruning, NO ordering — it is the
  baseline; keep it honest).
- Optional `max_depth: int | None`. At depth cutoff, return 0 (no heuristic);
  document this choice in the docstring.
- Count every visited node in SearchStats.
- Respect time budget: if exceeded, return the best move found so far and set
  `extra["timed_out"] = 1`.

## Solver (experiments/run_solve.py)
- `solve(config) -> SolveResult(value, nodes, time_s, best_first_move)`.
- Full minimax with memoization by Zobrist hash, AND a second run without
  memoization, so the report can show the effect.
- Solve (3,3), (4,3), (4,4). Attempt (5,4) with a hard timeout of 10 min and report
  "not solved within budget" if it fails — never hang.
- Output CSV results/solve.csv: n,k,memo,value,nodes,time_s,solved.

## Node-explosion experiment
- 7×7 k=4: depth-limited backtracking from the empty board for depths 1..D, stopping
  at the first depth whose single call exceeds 60 s. Record nodes and time per depth
  to results/backtracking_growth.csv, plus the theoretical upper bound
  ∏_{i=0}^{d-1}(N²−i) per depth in the same CSV.

## Tests
- (3,3) value = 0 (draw). (4,4) value = 0.
- Win-in-1 position: agent picks the winning move.
- Board unchanged after select_move.

## Gate
(3,3)=0 and (4,4)=0; win-in-1 test passes; all tests + mypy green.
