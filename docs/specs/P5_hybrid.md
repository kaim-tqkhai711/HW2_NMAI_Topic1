# P5 — Originality: Hybrid MCTS (+ optional threat-space search)

Reuse agents/mcts.py and agents/evaluation.py via composition/subclassing. Do not
duplicate code and do not break existing tests.

## Hybrid variants (agents/hybrid.py)
1. MCTS_EVAL: replace rollout with static evaluation mapped to [−1, 1] via
   tanh(score / scale); `scale` configurable.
2. MCTS_AB: at the leaf, run shallow alpha-beta (depth 2, candidate_radius=1) and map
   its score the same way. Proven wins/losses back up as exact ±1.
3. MCTS_SOLVER (optional, only if P2–P4 gates passed first try): propagate proven
   wins/losses (Winands et al., 2008) so proven-losing children are never chosen.

## Threat-space search (optional, agents/threat_space.py)
Simplified Allis-style search over forcing moves only (moves creating a four or an
open three), depth D; detects forced wins. Flag `use_threat_search: bool` in
ABConfig and hybrid configs so it can be ablated.

Register all variants in agents/presets.py.

## Tests
- All hybrids find win-in-1 and block immediate losses (use tests/positions.py).
- MCTS_AB finds the same forced win-in-3 positions as P3.

## Report
Simulations/sec of each variant vs plain MCTS on 9×9 k=5.

## Gate
Tests above pass; all tests + mypy green.
