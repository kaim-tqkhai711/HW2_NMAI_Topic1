# Failure cases

## (a) MCTS lost although a forced win existed

### Example 1: backtracking_d2 (X) vs mcts_ab (O), 7x7 k=4, game `7x4|t0.5|20260301|backtracking_d2|mcts_ab|o4|s0`

mcts_ab had a forced win (win_in_3; correct: [(1, 3)]; AB_FULL confirms) and played (6, 4).

Opening: [[4, 2], [2, 4], [4, 4], [4, 3]]. Agent moves (r,c): (0,0) (0,1) (6,2) (0,5) (6,0) (6,6) (5,5) (3,5) (5,3) (6,4) (5,1) (2,5) (3,3). Result: X won.

Position before agent move 10; move played (6, 4):

```
   0 1 2 3 4 5 6
0  X O . . . O .
1  . . . . . . .
2  . . . . O . .
3  . . . . . O .
4  . . X O X . .
5  . . . X . X .
6  X . X . . . O
```

### Example 2: mcts_heuristic (X) vs mcts_random (O), 7x7 k=4, game `7x4|t0.5|20260301|mcts_random|mcts_heuristic|o1|s1`

mcts_random had a forced win (win_in_3; correct: [(1, 1), (4, 4)]; AB_FULL confirms) and played (4, 6).

Opening: [[4, 3], [2, 2], [2, 3]]. Agent moves (r,c): (5,4) (5,3) (3,3) (3,2) (4,6) (1,4) (4,4) (4,1). Result: X won.

Position before agent move 5; move played (4, 6):

```
   0 1 2 3 4 5 6
0  . . . . . . .
1  . . . . . . .
2  . . O X . . .
3  . . X O . . .
4  . . . X . . .
5  . . . X O . .
6  . . . . . . .
```

### Example 3: mcts_ab (X) vs mcts_random (O), 7x7 k=4, game `7x4|t0.5|20260301|mcts_random|mcts_ab|o2|s1`

mcts_ab had a forced win (win_in_3; correct: [(5, 3)]; AB_FULL confirms) and played (6, 0).

Opening: [[3, 3], [2, 4]]. Agent moves (r,c): (5,2) (2,3) (5,4) (3,4) (6,0) (2,5) (5,1) (2,6). Result: O won.

Position before agent move 5; move played (6, 0):

```
   0 1 2 3 4 5 6
0  . . . . . . .
1  . . . . . . .
2  . . . O O . .
3  . . . X O . .
4  . . . . . . .
5  . . X . X . .
6  . . . . . . .
```

## (b) Alpha-beta lost from a position its own evaluation rated winning

### Example 1: random (X) vs ab_plain (O), 9x9 k=5, game `9x5|t0.5|20260302|random|ab_plain|o5|s0`

ab_plain evaluated this position at 10898 (threshold 10000, its own scale) and still lost the game.

Opening: [[4, 2], [5, 6]]. Agent moves (r,c): (7,1) (0,0) (1,0) (8,5) (6,6) (8,3) (0,2) (8,1) (2,2) (7,8) (5,5) (7,6) (3,5) (7,4) (1,4) (7,2) (3,1) (7,0) (5,4) (6,7) (2,8) (6,5) (4,5) (6,3) (5,2) (6,1) (7,7) (5,8) (6,2) (8,7) (8,6) (8,2) (3,2). Result: X won.

Position before agent move 24; move played (6, 3):

```
   0 1 2 3 4 5 6 7 8
0  O . X . . . . . .
1  X . . . X . . . .
2  . . X . . . . . X
3  . X . . . X . . .
4  . . X . . X . . .
5  . . . . X X O . .
6  . . . . . O X O .
7  O X O . O . O . O
8  . O . O . O . . .
```

### Example 2: mcts_random (X) vs ab_plain (O), 9x9 k=5, game `9x5|t0.1|20260311|ab_plain|mcts_random|o39|s1`

ab_plain evaluated this position at 11386 (threshold 10000, its own scale) and still lost the game.

Opening: [[6, 5], [3, 4], [4, 5], [6, 2]]. Agent moves (r,c): (3,5) (0,0) (5,3) (8,3) (2,7) (8,1) (4,8) (7,8) (2,0) (7,6) (8,2) (7,4) (0,5) (7,2) (7,1) (7,0) (0,7) (6,7) (0,1) (8,8) (5,4) (6,3) (7,3) (6,1) (1,2) (5,8) (5,1) (5,6) (3,2) (8,5) (4,2) (5,2) (7,5) (5,0) (5,5). Result: X won.

Position before agent move 34; move played (5, 0):

```
   0 1 2 3 4 5 6 7 8
0  O X . . . X . X .
1  . . X . . . . . .
2  X . . . . . . X .
3  . . X . O X . . .
4  . . X . . X . . X
5  . X O X X . O . O
6  . O O O . X . O .
7  O X O X O X O . O
8  . O X O . O . . O
```

### Example 3: ab_plain (X) vs mcts_rave_tac (O), 9x9 k=5, game `9x5|t0.1|20260311|ab_plain|mcts_rave_tac|o21|s0`

ab_plain evaluated this position at 10997 (threshold 10000, its own scale) and still lost the game.

Opening: [[6, 6], [6, 5]]. Agent moves (r,c): (0,0) (7,4) (8,6) (6,2) (8,4) (8,1) (8,2) (6,7) (8,0) (8,5) (7,7) (5,7) (7,5) (7,1) (7,3) (1,2) (7,2) (4,8) (6,8) (3,3) (8,8) (3,1) (6,4) (5,8) (8,3) (7,8) (6,0) (1,0) (7,6) (4,3) (5,5) (4,4) (5,3) (4,6) (5,1) (4,2) (6,1) (4,5). Result: O won.

Position before agent move 33; move played (5, 3):

```
   0 1 2 3 4 5 6 7 8
0  X . . . . . . . .
1  O . O . . . . . .
2  . . . . . . . . .
3  . O . O . . . . .
4  . . . O O . . . O
5  . . . . . X . O O
6  X . O . X O X O X
7  . O X X O X X X O
8  X O X X X O X . X
```
