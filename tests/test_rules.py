import pytest

from core.board import Board
from core.rules import GameConfig


def play(b: Board, moves: list[tuple[int, int]]) -> None:
    for r, c in moves:
        b.make(r * b.n + c)


def test_invalid_config() -> None:
    with pytest.raises(ValueError):
        GameConfig(3, 4)


@pytest.mark.parametrize(
    "line",
    [
        [(0, 0), (0, 1), (0, 2)],
        [(0, 0), (1, 0), (2, 0)],
        [(0, 0), (1, 1), (2, 2)],
        [(0, 2), (1, 1), (2, 0)],
    ],
)
def test_three_in_a_row_all_directions(line: list[tuple[int, int]]) -> None:
    b = Board(GameConfig(5, 3))
    filler = [(4, 4), (4, 0), (4, 2), (3, 3)]
    filler = [f for f in filler if f not in line][:2]
    play(b, [line[0], filler[0], line[1], filler[1], line[2]])
    assert b.winner == 1 and b.is_terminal


def test_win_by_middle_stone() -> None:
    b = Board(GameConfig(5, 3))
    play(b, [(2, 0), (0, 0), (2, 2), (0, 4), (2, 1)])
    assert b.winner == 1


def test_no_wraparound() -> None:
    b = Board(GameConfig(4, 3))
    play(b, [(0, 2), (3, 0), (0, 3), (3, 1), (1, 0)])
    assert b.winner == 0


def test_o_can_win() -> None:
    b = Board(GameConfig(4, 3))
    play(b, [(0, 0), (3, 0), (0, 1), (3, 1), (1, 3), (3, 2)])
    assert b.winner == -1


OVERLINE = [(0, 0), (4, 0), (0, 1), (4, 1), (0, 3), (3, 3), (0, 4), (3, 0), (0, 2)]


def test_overline_wins_when_freestyle() -> None:
    b = Board(GameConfig(5, 3, exact_k=False))
    play(b, OVERLINE)
    assert b.winner == 1


def test_overline_does_not_win_when_exact() -> None:
    b = Board(GameConfig(5, 3, exact_k=True))
    play(b, OVERLINE)
    assert b.winner == 0


def test_draw() -> None:
    b = Board(GameConfig(3, 3))
    play(b, [(0, 0), (0, 1), (0, 2), (1, 1), (1, 0), (1, 2), (2, 1), (2, 0), (2, 2)])
    assert b.is_terminal and b.winner == 0 and b.result() == 0
