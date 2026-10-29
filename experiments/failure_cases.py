"""Failure-case mining over tournament games.

Run: python -m experiments.failure_cases [--results results] [--out results/failure_cases.md]

Two kinds of cases are looked for in the games of the ``full`` run of every config
(pilot and quick runs are skipped; pass ``--all-runs`` to include the newest run of each):

(a) an MCTS-family agent lost although, earlier in the game, a forced win existed
    for it that it did not play (found by exhaustive search for wins in 1 and 3,
    then confirmed with a deep AB_FULL search);
(b) an alpha-beta agent lost although, at one of its own turns, its own static
    evaluation rated the position clearly in its favour.

Up to three examples of each are written with the moves and ASCII boards.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from pathlib import Path

from agents.alphabeta import WIN_SCORE, AlphaBetaAgent
from agents.evaluation import EvalWeights, evaluate
from agents.presets import AB_FULL
from core.board import Board
from core.rules import GameConfig, X
from eval.puzzles import classify
from eval.tournament import GameRecord, games_file, read_records
from experiments.plots import latest_runs

MAX_EXAMPLES = 3
VERIFY_BUDGET_S = 3.0


@dataclass
class Case:
    """One mined example."""

    kind: str
    record: GameRecord
    ply: int
    board_text: str
    played: tuple[int, int]
    note: str


def replay_positions(rec: GameRecord) -> list[tuple[Board, int, int]]:
    """Positions before each agent move: (board copy, flat move played, mover X=1/O=-1)."""
    cfg = GameConfig(rec.config["n"], rec.config["k"], rec.config["exact_k"])
    b = Board(cfg)
    for r, c in rec.opening:
        b.make(b.from_rc(r, c))
    out = []
    for mv in rec.moves:
        m = b.from_rc(*mv.move)
        out.append((b.copy(), m, b.to_move))
        b.make(m)
    return out


def _side_name(rec: GameRecord, mover: int) -> str:
    return rec.agent_x if mover == X else rec.agent_o


def verify_forced_win(b: Board, budget_s: float = VERIFY_BUDGET_S) -> tuple[bool, list[int]]:
    """Deep AB_FULL check that the side to move has a proven win; returns its move(s)."""
    agent = AlphaBetaAgent(replace(AB_FULL, max_depth=7, candidate_radius=None))
    move = agent.select_move(b, budget_s)
    return agent.last_stats().extra["score"] > WIN_SCORE // 2, [move]


def mcts_missed_win(rec: GameRecord) -> Case | None:
    """First position where an MCTS agent that went on to lose had a forced win and missed it."""
    loser_x = rec.result == -1
    name = rec.agent_x if loser_x else rec.agent_o
    if rec.result == 0 or not name.startswith("mcts"):
        return None
    loser = X if loser_x else -X
    for i, (b, played, mover) in enumerate(replay_positions(rec)):
        if mover != loser:
            continue
        cls = classify(b)
        if cls is None or cls[0] == "block" or played in cls[1]:
            continue
        ok, best = verify_forced_win(b)
        if ok and played not in best:
            return Case(
                "mcts_missed_forced_win", rec, i, str(b), b.to_rc(played),
                f"{name} had a forced win ({cls[0]}; correct: "
                f"{sorted(b.to_rc(m) for m in cls[1])}; AB_FULL confirms) and played "
                f"{b.to_rc(played)}.",
            )
    return None


def ab_lost_from_winning_eval(rec: GameRecord, margin_factor: float = 1.0) -> Case | None:
    """First AB turn at which its own evaluation showed a clear edge, in a game it lost."""
    if rec.result == 0:
        return None
    loser = X if rec.result == -1 else -X
    name = _side_name(rec, loser)
    if not name.startswith("ab"):
        return None
    cfg = GameConfig(rec.config["n"], rec.config["k"], rec.config["exact_k"])
    w = EvalWeights.default(cfg.k)
    threshold = margin_factor * 10 ** (cfg.k - 1)
    for i, (b, played, mover) in enumerate(replay_positions(rec)):
        if mover != loser:
            continue
        score = evaluate(b.cells_list, cfg, mover, w)
        if score >= threshold:
            return Case(
                "ab_lost_from_winning_eval", rec, i, str(b), b.to_rc(played),
                f"{name} evaluated this position at {score} (threshold {threshold:.0f}, "
                f"its own scale) and still lost the game.",
            )
    return None


def _loser_name(rec: GameRecord) -> str:
    return rec.agent_x if rec.result == -1 else rec.agent_o


def _spread(items: list[GameRecord], n: int) -> list[GameRecord]:
    """At most ``n`` evenly spaced items, so a scan covers every board and budget."""
    if n >= len(items):
        return list(items)
    return [items[i * len(items) // n] for i in range(n)]


def _spread_cases(items: list[Case], n: int) -> list[Case]:
    if n >= len(items):
        return list(items)
    return [items[i * len(items) // n] for i in range(n)]


def mine(records: list[GameRecord], limit: int = MAX_EXAMPLES, scan: int = 400
         ) -> tuple[list[Case], list[Case]]:
    """Collect up to ``limit`` cases of each kind.

    Games lost by an MCTS-family agent are scanned for (a), an evenly spaced
    sample of at most ``scan`` of them (the check is expensive). Every game lost
    by an alpha-beta agent is scanned for (b) (cheap); the examples are spread
    over the candidates found.
    """
    lost = [r for r in records if r.result != 0]
    a: list[Case] = []
    for rec in _spread([r for r in lost if _loser_name(r).startswith("mcts")], scan):
        if len(a) < limit and (c := mcts_missed_win(rec)):
            a.append(c)
    cands = [c for r in lost if _loser_name(r).startswith("ab")
             if (c := ab_lost_from_winning_eval(r))]
    return a, _spread_cases(cands, limit)


def render(cases_a: list[Case], cases_b: list[Case]) -> str:
    """Markdown report."""
    lines = ["# Failure cases", ""]
    for title, cases in (("(a) MCTS lost although a forced win existed", cases_a),
                         ("(b) Alpha-beta lost from a position its own evaluation rated winning",
                          cases_b)):
        lines += [f"## {title}", ""]
        if not cases:
            lines += ["No example found in the scanned games.", ""]
        for j, c in enumerate(cases, 1):
            r = c.record
            moves = " ".join(f"({m.move[0]},{m.move[1]})" for m in r.moves)
            lines += [
                f"### Example {j}: {r.agent_x} (X) vs {r.agent_o} (O), "
                f"{r.config['n']}x{r.config['n']} k={r.config['k']}, game `{r.game_id}`",
                "",
                c.note,
                "",
                f"Opening: {r.opening}. Agent moves (r,c): {moves}. Result: "
                f"{ {1: 'X won', -1: 'O won', 0: 'draw'}[r.result] }.",
                "",
                f"Position before agent move {c.ply + 1}; move played {c.played}:",
                "",
                "```",
                c.board_text,
                "```",
                "",
            ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=Path("results"))
    ap.add_argument("--out", type=Path, default=Path("results/failure_cases.md"))
    ap.add_argument("--all-runs", action="store_true",
                    help="also scan pilot/quick runs (default: only runs named 'full')")
    args = ap.parse_args()
    records: list[GameRecord] = []
    for run in latest_runs(args.results).values():
        if run.name != "full" and not args.all_runs:
            continue
        f = games_file(run)
        if f.exists():
            records += read_records(f)
    a, b = mine(records)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(a, b), encoding="utf-8")
    print(f"{len(records)} games scanned: {len(a)} MCTS cases, {len(b)} AB cases -> {args.out}")


if __name__ == "__main__":
    main()
