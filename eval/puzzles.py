"""Tactical puzzle set: generation, verification and scoring.

Puzzle file format (JSON list); moves are ``[row, col]`` pairs::

    {"id": "7x4-win_in_3-03", "config": {"n": 7, "k": 4, "exact_k": false},
     "board": ". . . ...\\n...", "to_move": "X",
     "correct": [[3, 1], [3, 4]], "category": "win_in_3"}

Categories: ``win_in_1`` (an immediate win exists), ``block`` (the opponent has
exactly one immediate win and the side to move has none, so the single correct
move is the block) and ``win_in_3`` (no immediate win, but a first move that wins
on the third ply whatever the reply). ``correct`` is the exhaustive set of moves
with that property. Positions are classified by an independent exhaustive search
and cross-checked with a deep `AB_FULL` search.

Run: python -m eval.puzzles [--out experiments/puzzles.json] [--per-cell 5]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from agents.alphabeta import WIN_SCORE, AlphaBetaAgent
from agents.base import Agent
from agents.presets import AB_FULL
from core.board import Board
from core.rules import EMPTY, O, X, GameConfig

CATEGORIES = ("win_in_1", "block", "win_in_3")
CONFIGS = (GameConfig(7, 4), GameConfig(9, 5))


@dataclass(frozen=True)
class Puzzle:
    """One puzzle; ``correct`` holds flat move indices."""

    id: str
    config: GameConfig
    board: str
    to_move: int
    correct: frozenset[int]
    category: str

    def make_board(self) -> Board:
        """Rebuild the position."""
        return Board.from_string(self.board, self.config, self.to_move)

    def to_json(self) -> dict[str, object]:
        """JSON-ready dict (moves as [row, col])."""
        n = self.config.n
        return {
            "id": self.id,
            "config": {"n": n, "k": self.config.k, "exact_k": self.config.exact_k},
            "board": self.board,
            "to_move": "X" if self.to_move == X else "O",
            "correct": [list(divmod(m, n)) for m in sorted(self.correct)],
            "category": self.category,
        }

    @staticmethod
    def from_json(d: dict[str, object]) -> Puzzle:
        """Inverse of `to_json`."""
        c = d["config"]
        assert isinstance(c, dict)
        cfg = GameConfig(int(c["n"]), int(c["k"]), bool(c.get("exact_k", False)))
        correct = d["correct"]
        assert isinstance(correct, list)
        return Puzzle(
            str(d["id"]),
            cfg,
            str(d["board"]),
            X if d["to_move"] == "X" else O,
            frozenset(int(r) * cfg.n + int(col) for r, col in correct),
            str(d["category"]),
        )


def save_puzzles(puzzles: list[Puzzle], path: Path) -> None:
    """Write puzzles as a JSON list."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([p.to_json() for p in puzzles], indent=1), encoding="utf-8")


def load_puzzles(path: Path) -> list[Puzzle]:
    """Read a puzzle file."""
    return [Puzzle.from_json(d) for d in json.loads(path.read_text(encoding="utf-8"))]


def immediate_wins(b: Board) -> set[int]:
    """Moves that win on the spot, found by playing each one."""
    out: set[int] = set()
    for m in b.legal_moves():
        b.make(m)
        if b.winner:
            out.add(m)
        b.unmake_move()
    return out


def forced_win_in_three(b: Board) -> set[int]:
    """First moves after which the mover wins on ply 3 against every reply.

    Plain exhaustive search; the caller must know there is no immediate win.
    """
    out: set[int] = set()
    for m in b.legal_moves():
        b.make(m)
        replies = b.legal_moves()
        ok = bool(replies) and not b.winner
        if ok:
            for r in replies:
                b.make(r)
                good = not b.winner and bool(immediate_wins(b))
                b.unmake_move()
                if not good:
                    ok = False
                    break
        b.unmake_move()
        if ok:
            out.add(m)
    return out


def random_position(config: GameConfig, rng: np.random.Generator, stones: int) -> Board:
    """Clustered random position: each stone lands near an existing one with p=0.8."""
    b = Board(config)
    n = config.n
    c = n // 2
    for _ in range(stones):
        if b.is_terminal:
            break
        near = b.candidate_moves(1) if b.ply and rng.random() < 0.8 else None
        if near:
            m = near[int(rng.integers(len(near)))]
        else:
            lo, hi = max(0, c - 2), min(n, c + 3)
            m = int(rng.integers(lo, hi)) * n + int(rng.integers(lo, hi))
            if m not in b.legal_moves():
                m = b.legal_moves()[int(rng.integers(len(b.legal_moves())))]
        b.make(m)
    return b


def classify(b: Board) -> tuple[str, set[int]] | None:
    """Category and correct-move set of a position, or None if it is not a puzzle."""
    if b.is_terminal:
        return None
    mine = immediate_wins(b)
    if mine:
        return "win_in_1", mine
    # Opponent's immediate wins: wins available to them if it were their move.
    b.to_move = -b.to_move
    theirs = immediate_wins(b)
    b.to_move = -b.to_move
    if len(theirs) == 1:
        return "block", theirs
    if not theirs:
        three = forced_win_in_three(b)
        if three:
            return "win_in_3", three
    return None


def _board_text(b: Board) -> str:
    sym = {X: "X", O: "O", EMPTY: "."}
    n = b.n
    return "\n".join(
        " ".join(sym[b.cells_list[r * n + c]] for c in range(n)) for r in range(n)
    )


def verify_with_search(p: Puzzle, budget_s: float = 120.0) -> bool:
    """Cross-check a puzzle with a deep AB_FULL search (agrees on score and move)."""
    cfg = replace(AB_FULL, max_depth=3, candidate_radius=None)
    agent = AlphaBetaAgent(cfg)
    b = p.make_board()
    move = agent.select_move(b, budget_s)
    score = agent.last_stats().extra["score"]
    if p.category == "win_in_1":
        return move in p.correct and score == WIN_SCORE - 1
    if p.category == "win_in_3":
        return move in p.correct and score == WIN_SCORE - 3
    return move in p.correct


def generate(per_cell: int = 5, seed: int = 0, max_tries: int = 200000) -> list[Puzzle]:
    """Generate ``per_cell`` puzzles for every (config, category) pair."""
    rng = np.random.default_rng(seed)
    out: list[Puzzle] = []
    for cfg in CONFIGS:
        found: dict[str, list[Puzzle]] = defaultdict(list)
        seen: set[str] = set()
        tries = 0
        while tries < max_tries and any(len(found[c]) < per_cell for c in CATEGORIES):
            tries += 1
            stones = int(rng.integers(6, 16)) if cfg.n == 7 else int(rng.integers(8, 20))
            b = random_position(cfg, rng, stones)
            if b.is_terminal or b.winner:
                continue
            res = classify(b)
            if res is None:
                continue
            cat, correct = res
            text = _board_text(b)
            if len(found[cat]) >= per_cell or text in seen:
                continue
            seen.add(text)
            p = Puzzle(
                f"{cfg.n}x{cfg.k}-{cat}-{len(found[cat]):02d}", cfg, text,
                b.to_move, frozenset(correct), cat,
            )
            if verify_with_search(p):
                found[cat].append(p)
        out.extend(p for c in CATEGORIES for p in found[c])
    return out


def run_puzzles(
    agent: Agent, time_budget_s: float, puzzles: list[Puzzle] | None = None,
    path: Path = Path("experiments/puzzles.json"),
) -> dict[str, float]:
    """Accuracy per category (plus ``"all"``) of ``agent`` on the puzzle set."""
    items = puzzles if puzzles is not None else load_puzzles(path)
    hit: dict[str, int] = defaultdict(int)
    tot: dict[str, int] = defaultdict(int)
    for p in items:
        move = agent.select_move(p.make_board(), time_budget_s)
        for key in (p.category, "all"):
            tot[key] += 1
            hit[key] += move in p.correct
    return {k: hit[k] / tot[k] for k in tot}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("experiments/puzzles.json"))
    ap.add_argument("--per-cell", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    puzzles = generate(args.per_cell, args.seed)
    save_puzzles(puzzles, args.out)
    counts: dict[str, int] = defaultdict(int)
    for p in puzzles:
        counts[f"{p.config.n}x{p.config.k} {p.category}"] += 1
    print(len(puzzles), "puzzles written to", args.out)
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
