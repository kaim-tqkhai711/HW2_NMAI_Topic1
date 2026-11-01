# Failure cases

## (a) MCTS lost although a forced win existed

### Example 1: mcts_random (X) vs backtracking_d2 (O), 11x11 k=5, game `11x5|t0.5|20260312|backtracking_d2|mcts_random|o0|s1`

mcts_random had a forced win (win_in_3; correct: [(4, 5), (8, 5)]; AB_FULL confirms) and played (1, 1).

Opening: [[6, 5], [7, 7], [3, 4]]. Agent moves (r,c): (0,0) (5,5) (10,7) (9,9) (10,5) (7,5) (10,3) (1,1) (10,1) (3,7) (9,10) (7,9) (9,8) (4,4) (9,6) (7,4) (9,4) (9,5) (8,5) (3,9) (9,2) (7,6) (8,9) (8,1) (8,7) (6,4) (5,4) (8,6) (9,0) (7,2) (7,3) (10,4) (8,2) (6,2) (7,8) (6,3) (6,9). Result: O won.

Position before agent move 8; move played (1, 1):

```
     0  1  2  3  4  5  6  7  8  9 10
 0   O  .  .  .  .  .  .  .  .  .  .
 1   .  .  .  .  .  .  .  .  .  .  .
 2   .  .  .  .  .  .  .  .  .  .  .
 3   .  .  .  .  X  .  .  .  .  .  .
 4   .  .  .  .  .  .  .  .  .  .  .
 5   .  .  .  .  .  X  .  .  .  .  .
 6   .  .  .  .  .  X  .  .  .  .  .
 7   .  .  .  .  .  X  .  O  .  .  .
 8   .  .  .  .  .  .  .  .  .  .  .
 9   .  .  .  .  .  .  .  .  .  X  .
10   .  .  .  O  .  O  .  O  .  .  .
```

### Example 2: mcts_random (X) vs mcts_eval (O), 11x11 k=5, game `11x5|t0.5|20260312|mcts_random|mcts_eval|o21|s0`

mcts_random had a forced win (win_in_3; correct: [(4, 7)]; AB_FULL confirms) and played (9, 3).

Opening: [[3, 7], [7, 3], [7, 7]]. Agent moves (r,c): (6,6) (2,7) (8,2) (7,1) (8,3) (5,7) (6,3) (9,3) (5,3) (7,6) (4,3). Result: O won.

Position before agent move 8; move played (9, 3):

```
     0  1  2  3  4  5  6  7  8  9 10
 0   .  .  .  .  .  .  .  .  .  .  .
 1   .  .  .  .  .  .  .  .  .  .  .
 2   .  .  .  .  .  .  .  X  .  .  .
 3   .  .  .  .  .  .  .  X  .  .  .
 4   .  .  .  .  .  .  .  .  .  .  .
 5   .  .  .  .  .  .  .  X  .  .  .
 6   .  .  .  O  .  .  O  .  .  .  .
 7   .  X  .  O  .  .  .  X  .  .  .
 8   .  .  O  O  .  .  .  .  .  .  .
 9   .  .  .  .  .  .  .  .  .  .  .
10   .  .  .  .  .  .  .  .  .  .  .
```

### Example 3: mcts_ab_tac (X) vs mcts_heuristic_tac (O), 11x11 k=5, game `11x5|t0.5|20260312|mcts_heuristic_tac|mcts_ab_tac|o14|s1`

mcts_ab_tac had a forced win (win_in_3; correct: [(4, 4)]; AB_FULL confirms) and played (3, 0).

Opening: [[3, 5], [6, 4], [3, 6]]. Agent moves (r,c): (5,8) (1,7) (4,10) (5,2) (3,3) (6,3) (4,3) (7,0) (1,8) (2,6) (7,9) (3,0) (4,9) (6,1) (4,4) (2,3) (4,2) (2,10) (4,6) (4,5) (4,0) (4,1) (7,4) (9,0) (4,7) (4,8) (5,4) (8,4) (3,4). Result: O won.

Position before agent move 12; move played (3, 0):

```
     0  1  2  3  4  5  6  7  8  9 10
 0   .  .  .  .  .  .  .  .  .  .  .
 1   .  .  .  .  .  .  .  X  O  .  .
 2   .  .  .  .  .  .  X  .  .  .  .
 3   .  .  .  O  .  X  X  .  .  .  .
 4   .  .  .  O  .  .  .  .  .  .  O
 5   .  .  X  .  .  .  .  .  O  .  .
 6   .  .  .  X  O  .  .  .  .  .  .
 7   X  .  .  .  .  .  .  .  .  O  .
 8   .  .  .  .  .  .  .  .  .  .  .
 9   .  .  .  .  .  .  .  .  .  .  .
10   .  .  .  .  .  .  .  .  .  .  .
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

### Example 2: ab_plain (X) vs mcts_ab (O), 9x9 k=5, game `9x5|t0.1|20260311|ab_plain|mcts_ab|o44|s0`

ab_plain evaluated this position at 11527 (threshold 10000, its own scale) and still lost the game.

Opening: [[2, 5], [3, 4]]. Agent moves (r,c): (0,0) (2,0) (8,6) (5,4) (8,4) (3,3) (8,2) (1,6) (8,0) (7,8) (7,7) (2,3) (7,5) (4,0) (7,3) (7,4) (7,1) (6,8) (6,7) (2,1) (6,6) (5,0) (6,4) (3,1) (6,2) (4,6) (6,0) (6,5) (5,7) (5,3) (5,5) (0,6) (8,3) (1,0) (5,1) (3,0). Result: O won.

Position before agent move 31; move played (5, 5):

```
   0 1 2 3 4 5 6 7 8
0  X . . . . . . . .
1  . . . . . . O . .
2  O O . O . X . . .
3  . O . O O . . . .
4  O . . . . . O . .
5  O . . O O . . X .
6  X . X . X O X X O
7  . X . X O X . X O
8  X . X . X . X . .
```

### Example 3: ab_plain (X) vs backtracking_d2 (O), 7x7 k=4, game `7x4|n10000|20260305|backtracking_d2|ab_plain|o30|s1`

ab_plain evaluated this position at 1086 (threshold 1000, its own scale) and still lost the game.

Opening: [[3, 4], [2, 4], [4, 3]]. Agent moves (r,c): (0,0) (6,3) (6,2) (6,1) (5,2) (6,0) (5,5) (5,4) (5,3) (5,6) (5,1) (5,0) (4,6) (4,5) (4,4) (6,4) (3,5). Result: O won.

Position before agent move 16; move played (6, 4):

```
   0 1 2 3 4 5 6
0  O . . . . . .
1  . . . . . . .
2  . . . . O . .
3  . . . . X . .
4  . . . X O X O
5  X O O O X O X
6  X X O X . . .
```
