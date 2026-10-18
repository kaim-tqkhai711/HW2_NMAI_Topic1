"""Re-derive every expectation in tests/positions.py by exhaustive search.

`wins_within` shares only the Board make/unmake primitives with the code under
test; it is a plain recursive existence search with no scoring or pruning.
"""
import pytest

from core.board import Board
from tests.positions import ALL_POSITIONS, Pos, midgame_positions_95


def wins_within(b: Board, plies: int) -> bool:
    """Whether the side to move can force a win within `plies` plies."""
    if plies <= 0 or b.is_terminal:
        return False
    for m in b.legal_moves():
        b.make(m)
        won = b.winner != 0
        if not won and plies >= 3:
            # opponent must have no reply that avoids losing within plies - 1
            replies = b.legal_moves()
            won = bool(replies)
            for r in replies:
                b.make(r)
                ok = b.winner == 0 and wins_within(b, plies - 2)
                b.unmake_move()
                if not ok:
                    won = False
                    break
        b.unmake_move()
        if won:
            return True
    return False


def forced_first_moves(b: Board, plies: int) -> set[int]:
    """First moves after which the mover wins within `plies` plies by force."""
    out: set[int] = set()
    for m in b.legal_moves():
        b.make(m)
        if b.winner != 0:
            win = True
        elif plies >= 3:
            replies = b.legal_moves()
            win = bool(replies)
            for r in replies:
                b.make(r)
                ok = b.winner == 0 and wins_within(b, plies - 2)
                b.unmake_move()
                if not ok:
                    win = False
                    break
        else:
            win = False
        b.unmake_move()
        if win:
            out.add(m)
    return out


def opponent_wins_next(b: Board, move: int) -> bool:
    b.make(move)
    try:
        for r in b.legal_moves():
            b.make(r)
            won = b.winner != 0
            b.unmake_move()
            if won:
                return True
        return False
    finally:
        b.unmake_move()


@pytest.mark.parametrize("pos", ALL_POSITIONS, ids=lambda p: p.name)
def test_expectations_hold_by_exhaustive_search(pos: Pos) -> None:
    b = pos.board()
    assert b.winner == 0 and b.to_move == pos.to_move
    if pos.win_ply == 1:
        assert forced_first_moves(b, 1) == set(pos.best)
    elif pos.win_ply == 3:
        assert forced_first_moves(b, 1) == set()
        assert forced_first_moves(b, 3) == set(pos.best)
    elif pos.best:
        assert forced_first_moves(b, 1) == set()
        losing = {m for m in b.legal_moves() if opponent_wins_next(b, m)}
        assert set(b.legal_moves()) - losing == set(pos.best)
    else:
        assert forced_first_moves(b, 1) == set()


def test_midgames_are_valid_and_unfinished() -> None:
    for b in midgame_positions_95():
        assert not b.is_terminal and b.n_empty > 60
