"""Benchmark full random playouts (empty board -> terminal -> unmake all).

Run: python -m experiments.run_bench_core [--seconds 3] [--seed 0]
"""
from __future__ import annotations

import argparse
from time import perf_counter

import numpy as np

from core.board import Board
from core.rules import GameConfig

CONFIGS = [(3, 3), (7, 4), (9, 5), (11, 5)]


def bench(cfg: GameConfig, seconds: float, seed: int) -> tuple[float, float]:
    """Return (playouts per second, mean game length in plies)."""
    draws = np.random.default_rng(seed).random(1 << 16).tolist()
    d = 0
    board = Board(cfg)
    empties = board.empty_cells
    playouts = plies = 0
    start = perf_counter()
    while perf_counter() - start < seconds:
        while not board.is_terminal:
            board.make(empties[int(draws[d & 0xFFFF] * len(empties))])
            d += 1
        plies += board.ply
        for _ in range(board.ply):
            board.unmake_move()
        playouts += 1
    return playouts / (perf_counter() - start), plies / playouts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    print(f"{'config':<10}{'playouts/s':>12}{'avg plies':>12}")
    for n, k in CONFIGS:
        pps, avg = bench(GameConfig(n, k), args.seconds, args.seed)
        print(f"{n}x{n} k={k:<4}{pps:>12,.0f}{avg:>12.1f}")


if __name__ == "__main__":
    main()
