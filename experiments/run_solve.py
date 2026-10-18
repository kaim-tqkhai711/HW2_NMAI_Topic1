"""Exact game-theoretic solving of small (N, k) boards, with and without memoization.

Run: python -m experiments.run_solve [--timeout 600] [--nomemo-timeout 120]
"""
from __future__ import annotations

import argparse
import csv
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import numpy as np

from core.board import Board
from core.rules import GameConfig

CONFIGS = [(3, 3), (4, 3), (4, 4), (5, 4)]
_CLOCK_MASK = 1023


@dataclass(frozen=True)
class SolveResult:
    """Outcome of one exact solve.

    Attributes:
        value: Result for X with perfect play (+1 win, 0 draw, -1 loss), or None
            if the time limit was hit first.
        nodes: Nodes visited (calls of the search function, root included).
        time_s: Wall-clock seconds.
        best_first_move: A first move achieving `value`, or None if unsolved.
        solved: Whether the search completed.
    """

    value: int | None
    nodes: int
    time_s: float
    best_first_move: int | None
    solved: bool


class _Timeout(Exception):
    pass


def _symmetry_perms(n: int) -> list[list[int]]:
    """The 8 dihedral symmetries of an n x n board as cell permutations."""
    maps: list[Callable[[int, int], tuple[int, int]]] = [
        lambda r, c: (r, c),
        lambda r, c: (c, n - 1 - r),
        lambda r, c: (n - 1 - r, n - 1 - c),
        lambda r, c: (n - 1 - c, r),
        lambda r, c: (r, n - 1 - c),
        lambda r, c: (n - 1 - r, c),
        lambda r, c: (c, r),
        lambda r, c: (n - 1 - c, n - 1 - r),
    ]
    return [[a * n + b for a, b in (f(*divmod(m, n)) for m in range(n * n))] for f in maps]


class _Solver:
    """Exact +1/0/-1 negamax. Never prunes except to stop at a proven win.

    A win (+1) cannot be improved on, so expansion of a node stops there; the
    stored value is still exact. With `symmetry` the table key is the minimum
    of the 8 Zobrist hashes of the position's board symmetries, so equivalent
    positions share one entry.
    """

    def __init__(self, board: Board, memo: bool, symmetry: bool, deadline: float) -> None:
        self.board = board
        self.table: dict[int, int] | None = {} if memo else None
        self.symmetry = symmetry
        self.deadline = deadline
        self.nodes = 0
        n = board.n
        rng = np.random.default_rng(0xC0FFEE)
        base = rng.integers(0, 2**63, size=(2, n * n), dtype=np.uint64).tolist()
        perms = _symmetry_perms(n) if symmetry else [list(range(n * n))]
        self.keys = [
            [tuple(base[p][perm[m]] for perm in perms) for m in range(n * n)]
            for p in (0, 1)
        ]
        self.hs: list[int] = [0] * len(perms)
        self.best_first: int | None = None

    def negamax(self) -> int:
        """Value (+1/0/-1) for the side to move."""
        self.nodes += 1
        if not self.nodes & _CLOCK_MASK and perf_counter() > self.deadline:
            raise _Timeout
        board = self.board
        if board.winner:
            return -1
        moves = board.legal_moves()
        if not moves:
            return 0
        table = self.table
        key = 0
        if table is not None:
            key = min(self.hs)
            hit = table.get(key)
            if hit is not None:
                return hit
        side = 0 if board.to_move == 1 else 1
        keys = self.keys[side]
        saved = self.hs
        at_root = board.ply == 0
        best = -1
        for m in moves:
            board.make(m)
            if table is not None:
                self.hs = [a ^ b for a, b in zip(saved, keys[m])]
            try:
                v = -self.negamax()
            finally:
                board.unmake_move()
                self.hs = saved
            if v > best:
                best = v
                if at_root:
                    self.best_first = m
                if best == 1:
                    break
        if table is not None:
            table[key] = best
        return best


def solve(
    config: GameConfig,
    memo: bool = True,
    timeout_s: float = 600.0,
    symmetry: bool = True,
) -> SolveResult:
    """Solve the empty-board game exactly.

    Full minimax over all moves, except that a node stops expanding once a
    winning child is found (+1 is the maximum). Memoization is the only other
    difference between modes, so node counts isolate its effect.

    Args:
        config: Board size and win length.
        memo: Cache values by Zobrist hash.
        timeout_s: Hard wall-clock limit; the search is abandoned cleanly.
        symmetry: With `memo`, identify the 8 symmetric images of a position.

    Returns:
        A `SolveResult`; `solved` is False if the limit was hit.
    """
    board = Board(config)
    t0 = perf_counter()
    solver = _Solver(board, memo, memo and symmetry, t0 + timeout_s)
    try:
        value = solver.negamax()
    except _Timeout:
        return SolveResult(None, solver.nodes, perf_counter() - t0, None, False)
    return SolveResult(value, solver.nodes, perf_counter() - t0, solver.best_first, True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=600.0, help="symmetric-memo runs (s)")
    ap.add_argument("--ablation-timeout", type=float, default=120.0,
                    help="memo-free and plain-memo runs (s)")
    ap.add_argument("--out", type=Path, default=Path("results/solve.csv"))
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    modes = [(False, False), (True, False), (True, True)]
    with args.out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n", "k", "memo", "value", "nodes", "time_s", "solved", "symmetry"])
        for n, k in CONFIGS:
            for memo, sym in modes:
                limit = args.timeout if sym else args.ablation_timeout
                r = solve(GameConfig(n, k), memo=memo, timeout_s=limit, symmetry=sym)
                shown = r.value if r.solved else "not solved within budget"
                print(f"({n},{k}) memo={memo} sym={sym}: value={shown} "
                      f"nodes={r.nodes} t={r.time_s:.1f}s", flush=True)
                w.writerow([n, k, int(memo), "" if r.value is None else r.value,
                            r.nodes, f"{r.time_s:.3f}", int(r.solved), int(sym)])
                f.flush()


if __name__ == "__main__":
    main()
