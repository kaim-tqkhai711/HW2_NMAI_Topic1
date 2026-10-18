# Failure cases

## (a) MCTS lost although a forced win existed

### Example 1: mcts_random (X) vs mcts_heuristic (O), 7x7 k=4, game `7x4|t0.1|20260306|mcts_random|mcts_heuristic|o1|s0`

mcts_random had a forced win (win_in_3; correct: [(3, 2)]; AB_FULL confirms) and played (2, 0).

Opening: [[2, 2], [3, 4]]. Agent moves (r,c): (4,2) (6,1) (2,0) (4,3) (1,2) (5,2). Result: O won.

Position before agent move 3; move played (2, 0):

```
   0 1 2 3 4 5 6
0  . . . . . . .
1  . . . . . . .
2  . . X . . . .
3  . . . . O . .
4  . . X . . . .
5  . . . . . . .
6  . O . . . . .
```

### Example 2: mcts_random (X) vs mcts_heuristic (O), 7x7 k=4, game `7x4|t0.1|20260306|mcts_random|mcts_heuristic|o3|s0`

mcts_random had a forced win (win_in_3; correct: [(1, 4), (4, 1)]; AB_FULL confirms) and played (1, 5).

Opening: [[3, 2], [4, 4], [2, 3], [4, 3]]. Agent moves (r,c): (1,5) (4,5) (4,2) (6,5) (2,2) (4,6). Result: O won.

Position before agent move 1; move played (1, 5):

```
   0 1 2 3 4 5 6
0  . . . . . . .
1  . . . . . . .
2  . . . X . . .
3  . . X . . . .
4  . . . O O . .
5  . . . . . . .
6  . . . . . . .
```

### Example 3: mcts_heuristic (X) vs mcts_random (O), 7x7 k=4, game `7x4|t0.1|20260306|mcts_random|mcts_heuristic|o4|s1`

mcts_heuristic had a forced win (win_in_1; correct: [(2, 2)]; AB_FULL confirms) and played (2, 1).

Opening: [[3, 2], [2, 3], [4, 2]]. Agent moves (r,c): (2,4) (5,2) (6,2) (2,1) (2,2) (3,3) (2,5). Result: O won.

Position before agent move 4; move played (2, 1):

```
   0 1 2 3 4 5 6
0  . . . . . . .
1  . . . . . . .
2  . . . O O . .
3  . . X . . . .
4  . . X . . . .
5  . . X . . . .
6  . . O . . . .
```

## (b) Alpha-beta lost from a position its own evaluation rated winning

### Example 1: ab_plain (X) vs backtracking_d2 (O), 7x7 k=4, game `7x4|t0.1|20260301|backtracking_d2|ab_plain|o1|s1`

ab_plain evaluated this position at 2174 (threshold 1000, its own scale) and still lost the game.

Opening: [[4, 3], [2, 2], [2, 3]]. Agent moves (r,c): (0,0) (6,3) (6,2) (6,1) (6,0) (5,6) (5,5) (5,4) (5,3) (5,2) (3,4) (5,1) (4,6) (4,5) (3,6) (4,4) (4,2) (4,1) (4,0) (6,6) (3,5) (5,0) (3,3). Result: O won.

Position before agent move 20; move played (6, 6):

```
   0 1 2 3 4 5 6
0  O . . . . . .
1  . . . . . . .
2  . . O X . . .
3  . . . . O . O
4  O X O X X X O
5  . X X O X O X
6  O X O X . . .
```
