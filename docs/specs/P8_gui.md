# P8 — GUI (pygame)

Use only public interfaces of core/ and agents/ (Agent, Board, SearchStats, presets
registry; optional introspection `last_pv`, `root_visit_map`, `root_value_map` via
hasattr). Keep logic in gui/controller.py (pure Python, testable headless) and
drawing in gui/app.py.

## Features
- Setup screen: N, k (presets + custom), exact_k toggle, mode (Human vs AI,
  AI vs Human, AI vs AI, Human vs Human), agent per side from the registry,
  time budget slider 0.1–5 s.
- Board: click to move, last-move highlight, winning line highlight, move numbers toggle.
- AI runs in a background thread so the UI never freezes; thinking indicator; cancel.
- Side panel: per-move nodes, depth, sims/sec, time; PV line for AB; win-probability
  estimate for MCTS.
- Overlay toggle: heatmap of MCTS root visits or AB root move scores.
- Controls: undo, restart, AI-vs-AI step / autoplay with speed, save/load JSON
  (same format as tournament GameRecord), screenshot export.
- Readable at 11×11 in a ≥ 900×700 window.

## Tests (SDL_VIDEODRIVER=dummy)
Controller: move legality, undo, mode switching, AI handoff via thread with a
RandomAgent, save → load → replay equality, loading a tournament GameRecord.

## Gate
`python -m gui.app` imports and initializes headless; controller tests pass; all
tests + mypy green. List visual checks for the human in PROGRESS.md.
