# P3 — Alpha-beta with ablation flags

Move is a flat int (see CLAUDE.md). Read core/ and agents/base.py first; do not change them.

## agents/evaluation.py
- Pattern-based static evaluation, side-to-move perspective (negamax convention).
- For each length-k window in all 4 directions: a window containing only one
  side's stones contributes w[count] for that side; mixed windows contribute 0.
- Also detect open vs half-open threats (open-(k−1), half-open-(k−1), open-(k−2))
  with a separate weight table.
- All weights in one `EvalWeights` dataclass (tunable / ablatable).
- Full evaluation AND incremental version (rescan only windows through the changed
  cell). Test incremental == full on 500 random positions.
- Module docstring contains the exact formula in LaTeX-like notation for the report.

## agents/alphabeta.py — AlphaBetaAgent(ABConfig)
```python
@dataclass(frozen=True)
class ABConfig:
    move_ordering: bool
    iterative_deepening: bool
    transposition_table: bool
    candidate_radius: int | None   # None = all legal moves
    max_depth: int
    killer_moves: bool = False
    tt_size: int = 2**20
```
- Negamax, alpha-beta, fail-soft.
- Terminal scores: win = +WIN_SCORE − ply, loss = −WIN_SCORE + ply.
- Move ordering: (1) TT best move, (2) immediate wins, (3) blocks of opponent's
  immediate win, (4) rest sorted by a cheap local score.
- Immediate-threat check at each node: if side to move has a winning move, return
  it; if opponent has ≥1 winning move, restrict to blocking moves.
- TT entries: hash, depth, value, flag (EXACT/LOWER/UPPER), best_move; replace by depth.
- Iterative deepening respects time_budget_s: abort the running iteration on timeout,
  return the best move of the last completed depth.
- Stats: nodes, depth_reached, extra: tt_hits, cutoffs, effective branching factor.
- `last_pv() -> list[int]` for the GUI.

## agents/presets.py
AB_PLAIN, AB_ORDER, AB_ORDER_ID, AB_ORDER_ID_TT, AB_FULL (adds candidate_radius=2).
Also an `AGENT_REGISTRY: dict[str, Callable[[int], Agent]]` (seed → agent) that later
milestones extend.

## Fixed test positions
Create tests/positions.py with ≥ 8 hand-built positions (7×7 k=4 and 9×9 k=5) via
Board.from_string, each with a docstring stating what it tests and the expected
answer verified by hand or by brute force (BacktrackingAgent at sufficient depth on
small boards). Must include: win-in-1, must-block, forced win-in-3 (at least 2),
quiet midgame (for value equality).

## Tests
- KEY: AB_PLAIN and AB_FULL with same depth and candidate_radius=None return the
  SAME minimax value on every fixed position (pruning must not change the result).
  Also compare AB_PLAIN value against BacktrackingAgent at the same depth on 4×4.
- Finds win-in-1 and forced win-in-3; blocks opponent's open-(k−1).
- Iterative deepening never exceeds budget × 1.1.
- Board unchanged after select_move.

## Report table
For each preset on 3 fixed midgame 9×9 k=5 positions at depth 4: nodes, time, cutoffs.

## Gate
Value equality test passes; incremental == full eval on 500 positions; forced win-in-3
found; ID within budget × 1.1; all tests + mypy green.
