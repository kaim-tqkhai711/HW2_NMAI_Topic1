# P4 — MCTS (UCT, heuristic rollout, RAVE)

Move is a flat int (see CLAUDE.md). Read core/ and agents/base.py first; do not change them.

## MCTSConfig
```python
@dataclass(frozen=True)
class MCTSConfig:
    c_uct: float = 1.414
    rollout: Literal["random", "heuristic"] = "random"
    rave: bool = False
    rave_k: float = 1000.0
    candidate_radius: int | None = 2   # tree expansion only
    max_rollout_depth: int | None = None
    reuse_tree: bool = True
    max_iterations: int | None = None  # for deterministic tests
    seed: int = 0
```

## Algorithm
- 4 phases: selection (UCB1), expansion (one child), simulation, backprop.
- Node: move, parent, children, untried_moves, N, W. W is stored from the
  perspective of the player who made the move INTO this node. Document this
  convention in the class docstring (the #1 source of MCTS sign bugs).
- Expansion uses `candidate_moves(candidate_radius)` on the tree board.
- Rollout (CLAUDE.md decisions 7–8): on a scratch `board.copy()` (no candidate
  tracking), sampling from `empty_cells`.
  - random: uniform over empty cells.
  - heuristic: play an immediate win if one exists; else block the opponent's
    immediate win if one exists; else uniform random. Immediate-win detection must
    be cheap: check only cells near the last moves, not a full-board scan.
- RAVE: AMAF stats per (node, move); Q = (1−β)·Q_uct + β·Q_amaf,
  β = sqrt(rave_k / (3·N + rave_k)). Formula in docstring.
- Tree reuse: descend to the child matching the opponent's reply.
- Final move: most-visited child.
- Stop at time_budget_s (check clock every 64 iterations) or max_iterations.
- Stats: nodes = simulations; extra: sims_per_s, max_tree_depth.
- `root_visit_map() -> np.ndarray` [N, N] and `root_value_map()` for the GUI.
- Register MCTS_RANDOM, MCTS_HEURISTIC, MCTS_RAVE in agents/presets.py.

## Tests
- Determinism: same seed + max_iterations → identical move and identical visit counts.
- Sign convention: in a win-in-1 position, the winning child has the highest Q
  after 2,000 iterations, for both X-to-move and mirrored O-to-move positions.
- Heuristic MCTS blocks an opponent's open-(k−1) in ≥ 95% of 20 seeds.
- Board unchanged after select_move.

## Benchmark
Simulations/sec, random vs heuristic rollout, 9×9 k=5 and 11×11 k=5.

## Gate
Determinism, sign-convention and block tests pass; all tests + mypy green.
