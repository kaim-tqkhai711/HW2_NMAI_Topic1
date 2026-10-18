"""pygame front end: setup screen and game screen. All game logic is in controller.py.

Run: python -m gui.app [--load saved.json] [--headless-check]

Keys in the game: U undo, R restart, M move numbers, O overlay, S step (AI vs AI),
A autoplay, C cancel AI, P screenshot, Esc back to setup.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from functools import partial
from pathlib import Path

import numpy as np
import pygame
from numpy.typing import NDArray

from gui.controller import (
    BUDGET_RANGE,
    OVERLAYS,
    GameController,
    Mode,
    Setup,
    with_budget,
)

BG = (246, 244, 238)
BOARD_BG = (232, 214, 176)
LINE = (70, 60, 45)
X_COL = (0, 114, 178)
O_COL = (213, 94, 0)
HILITE = (200, 30, 60)
WIN_COL = (0, 158, 115)
TEXT = (30, 30, 30)
MUTED = (110, 110, 110)
BTN = (225, 225, 220)
BTN_ON = (190, 215, 235)
BTN_BORDER = (150, 150, 145)
PANEL_W = 340
MIN_SIZE = (900, 700)
SAVE_DIR = Path("results/gui_saves")
SHOT_DIR = Path("results/gui_screenshots")
N_PRESETS = (3, 4, 7, 9, 11)
K_PRESETS = (3, 4, 5)


@dataclass
class Button:
    """A clickable rectangle."""

    rect: pygame.Rect
    label: str
    action: Callable[[], object]
    active: bool = False
    enabled: bool = True


def heat_color(v: float) -> tuple[int, int, int]:
    """Blue -> yellow -> red ramp for a value in [0, 1]."""
    v = float(min(1.0, max(0.0, v)))
    if v < 0.5:
        t = v / 0.5
        return (int(40 + 215 * t), int(80 + 140 * t), int(220 - 170 * t))
    t = (v - 0.5) / 0.5
    return (255, int(220 - 190 * t), int(50 - 30 * t))


class App:
    """The GUI application.

    Args:
        controller: Game controller to drive (a default one is created if omitted).
        size: Initial window size, at least 900 x 700.
    """

    def __init__(self, controller: GameController | None = None,
                 size: tuple[int, int] = (1000, 760)) -> None:
        pygame.init()
        pygame.display.set_caption("Generalized tic-tac-toe (m,n,k-game)")
        w, h = max(size[0], MIN_SIZE[0]), max(size[1], MIN_SIZE[1])
        self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        self.font = pygame.font.SysFont("consolas,dejavusansmono,couriernew", 16)
        self.small = pygame.font.SysFont("consolas,dejavusansmono,couriernew", 13)
        self.big = pygame.font.SysFont("arial,dejavusans", 26, bold=True)
        self.ctrl = controller or GameController()
        self.setup = self.ctrl.setup
        self.state = "setup"
        self.buttons: list[Button] = []
        self.show_numbers = False
        self.overlay_idx = 0
        self.hover: tuple[int, int] | None = None
        self.dragging_slider = False
        self.slider_rect = pygame.Rect(0, 0, 1, 1)
        self.board_rect = pygame.Rect(0, 0, 1, 1)
        self.message = ""
        self.running = True
        self.clock = pygame.time.Clock()

    # ---------------------------------------------------------- helpers
    def names(self) -> list[str]:
        return sorted(self.ctrl.registry)

    def text(self, s: str, pos: tuple[int, int], font: pygame.font.Font | None = None,
             color: tuple[int, int, int] = TEXT, center: bool = False) -> pygame.Rect:
        surf = (font or self.font).render(s, True, color)
        r = surf.get_rect()
        if center:
            r.center = pos
        else:
            r.topleft = pos
        self.screen.blit(surf, r)
        return r

    def button(self, rect: pygame.Rect, label: str, action: Callable[[], object],
               active: bool = False, enabled: bool = True) -> None:
        self.buttons.append(Button(rect, label, action, active, enabled))
        pygame.draw.rect(self.screen, BTN_ON if active else BTN, rect, border_radius=5)
        pygame.draw.rect(self.screen, BTN_BORDER, rect, 1, border_radius=5)
        self.text(label, rect.center, self.small, TEXT if enabled else MUTED, center=True)

    # ------------------------------------------------------ setup screen
    def set_setup(self, **kw: object) -> None:
        s = replace(self.setup, **kw)  # type: ignore[arg-type]
        if s.k > s.n:
            s = replace(s, k=s.n)
        self.setup = s

    def draw_setup(self) -> None:
        self.buttons = []
        w, h = self.screen.get_size()
        self.screen.fill(BG)
        self.text("Generalized tic-tac-toe", (w // 2, 40), self.big, center=True)
        x0, y = 60, 90
        s = self.setup

        self.text("Board size N", (x0, y))
        bx = x0 + 190
        for n in N_PRESETS:
            self.button(pygame.Rect(bx, y - 4, 44, 28), str(n), partial(self.set_setup, n=n),
                        s.n == n)
            bx += 50
        self.button(pygame.Rect(bx + 10, y - 4, 28, 28), "-",
                    lambda: self.set_setup(n=max(3, s.n - 1)))
        self.text(str(s.n), (bx + 48, y), self.font)
        self.button(pygame.Rect(bx + 80, y - 4, 28, 28), "+",
                    lambda: self.set_setup(n=min(19, s.n + 1)))

        y += 50
        self.text("Win length k", (x0, y))
        bx = x0 + 190
        for k in K_PRESETS:
            self.button(pygame.Rect(bx, y - 4, 44, 28), str(k),
                        partial(self.set_setup, k=min(k, s.n)), s.k == k, k <= s.n)
            bx += 50
        self.button(pygame.Rect(bx + 10, y - 4, 28, 28), "-",
                    lambda: self.set_setup(k=max(2, s.k - 1)))
        self.text(str(s.k), (bx + 48, y), self.font)
        self.button(pygame.Rect(bx + 80, y - 4, 28, 28), "+",
                    lambda: self.set_setup(k=min(s.n, s.k + 1)))

        y += 50
        self.text("Exact k", (x0, y))
        self.button(pygame.Rect(x0 + 190, y - 4, 70, 28), "on" if s.exact_k else "off",
                    partial(self.set_setup, exact_k=not s.exact_k), s.exact_k)
        self.text("on: a run longer than k does not win", (x0 + 280, y), self.small, MUTED)

        y += 50
        self.text("Mode", (x0, y))
        bx = x0 + 190
        for mode in Mode:
            self.button(pygame.Rect(bx, y - 4, 150, 28), mode.value,
                        partial(self.set_setup, mode=mode), s.mode is mode)
            bx += 156

        names = self.names()
        for label, field, player in (("Agent X", "agent_x", 1), ("Agent O", "agent_o", -1)):
            y += 50
            human = s.mode.is_human(player)
            self.text(label, (x0, y), color=MUTED if human else TEXT)
            cur = getattr(s, field)
            idx = names.index(cur) if cur in names else 0
            self.button(pygame.Rect(x0 + 190, y - 4, 28, 28), "<",
                        partial(self.set_setup, **{field: names[(idx - 1) % len(names)]}),
                        enabled=not human)
            self.text("human" if human else cur, (x0 + 230, y), color=MUTED if human else TEXT)
            self.button(pygame.Rect(x0 + 450, y - 4, 28, 28), ">",
                        partial(self.set_setup, **{field: names[(idx + 1) % len(names)]}),
                        enabled=not human)

        y += 56
        lo, hi = BUDGET_RANGE
        self.text(f"Time per move: {s.time_budget_s:.1f} s", (x0, y))
        self.slider_rect = pygame.Rect(x0 + 260, y + 4, 300, 10)
        pygame.draw.rect(self.screen, BTN_BORDER, self.slider_rect, border_radius=5)
        frac = (s.time_budget_s - lo) / (hi - lo)
        knob = (self.slider_rect.x + int(frac * self.slider_rect.w), self.slider_rect.centery)
        pygame.draw.circle(self.screen, X_COL, knob, 10)

        y += 70
        self.button(pygame.Rect(x0, y, 200, 44), "Start game", self.start_game)
        self.button(pygame.Rect(x0 + 220, y, 200, 44), "Load last save", self.load_last)
        if self.message:
            self.text(self.message, (x0, y + 60), color=HILITE)

    def start_game(self) -> None:
        try:
            self.ctrl.start(self.setup)
        except ValueError as exc:
            self.message = str(exc)
            return
        self.message = ""
        self.state = "game"

    def load_last(self) -> None:
        files = sorted(SAVE_DIR.glob("*.json")) if SAVE_DIR.exists() else []
        if not files:
            self.message = f"no saves in {SAVE_DIR}"
            return
        self.load_file(files[-1])

    def load_file(self, path: Path) -> None:
        try:
            self.ctrl.load(path)
        except (OSError, ValueError, KeyError, StopIteration) as exc:
            self.message = f"load failed: {exc}"
            return
        self.setup = self.ctrl.setup
        self.message = f"loaded {path.name}"
        self.state = "game"

    # ------------------------------------------------------- game screen
    def layout(self) -> tuple[pygame.Rect, int]:
        w, h = self.screen.get_size()
        margin = 20
        side = min(h - 2 * margin, w - PANEL_W - 2 * margin)
        n = self.ctrl.config.n
        cell = max(10, side // n)
        rect = pygame.Rect(margin, margin, cell * n, cell * n)
        return rect, cell

    def cell_at(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        if not self.board_rect.collidepoint(pos):
            return None
        n = self.ctrl.config.n
        cell = self.board_rect.w // n
        return ((pos[1] - self.board_rect.y) // cell, (pos[0] - self.board_rect.x) // cell)

    def cell_center(self, r: int, c: int, cell: int) -> tuple[int, int]:
        return (self.board_rect.x + c * cell + cell // 2, self.board_rect.y + r * cell + cell // 2)

    def draw_game(self) -> None:
        ctrl = self.ctrl
        n = ctrl.config.n
        self.buttons = []
        self.screen.fill(BG)
        self.board_rect, cell = self.layout()
        br = self.board_rect
        pygame.draw.rect(self.screen, BOARD_BG, br)
        for i in range(n):
            a = self.cell_center(0, i, cell)
            b = self.cell_center(n - 1, i, cell)
            pygame.draw.line(self.screen, LINE, a, b, 1)
            a = self.cell_center(i, 0, cell)
            b = self.cell_center(i, n - 1, cell)
            pygame.draw.line(self.screen, LINE, a, b, 1)
        pygame.draw.rect(self.screen, LINE, br, 2)

        kind = OVERLAYS[self.overlay_idx]
        heat = ctrl.overlay(kind) if kind != "off" else None
        if heat is not None:
            self.draw_heat(heat, kind, cell)

        if self.hover and ctrl.is_human_turn():
            r, c = self.hover
            if ctrl.board.cells_list[r * n + c] == 0:
                s = pygame.Surface((cell, cell), pygame.SRCALPHA)
                s.fill((*(X_COL if ctrl.to_move == 1 else O_COL), 70))
                self.screen.blit(s, (br.x + c * cell, br.y + r * cell))

        rad = max(4, int(cell * 0.38))
        numbers = {m: i + 1 for i, m in enumerate(ctrl.moves)}
        for m in range(n * n):
            v = ctrl.board.cells_list[m]
            if not v:
                continue
            r, c = divmod(m, n)
            ctr = self.cell_center(r, c, cell)
            if v == 1:
                pygame.draw.circle(self.screen, X_COL, ctr, rad)
                d = int(rad * 0.55)
                if not self.show_numbers:
                    pygame.draw.line(self.screen, (255, 255, 255), (ctr[0] - d, ctr[1] - d),
                                     (ctr[0] + d, ctr[1] + d), max(2, rad // 5))
                    pygame.draw.line(self.screen, (255, 255, 255), (ctr[0] - d, ctr[1] + d),
                                     (ctr[0] + d, ctr[1] - d), max(2, rad // 5))
            else:
                pygame.draw.circle(self.screen, O_COL, ctr, rad)
                pygame.draw.circle(self.screen, BOARD_BG, ctr, int(rad * 0.55))
            if self.show_numbers:
                self.text(str(numbers[m]), ctr, self.small,
                          (255, 255, 255) if v == 1 else TEXT, center=True)
        lm = ctrl.last_move
        if lm is not None:
            r, c = divmod(lm, n)
            pygame.draw.circle(self.screen, HILITE, self.cell_center(r, c, cell), rad + 3, 3)
        line = ctrl.winning_line()
        if line:
            pts = [self.cell_center(*divmod(m, n), cell) for m in line]
            pygame.draw.line(self.screen, WIN_COL, pts[0], pts[-1], max(4, cell // 8))
            for p in pts:
                pygame.draw.circle(self.screen, WIN_COL, p, rad + 5, 3)

        self.draw_panel()

    def draw_heat(self, heat: NDArray[np.float64], kind: str, cell: int) -> None:
        finite = heat[np.isfinite(heat)]
        if finite.size == 0:
            return
        lo, hi = float(finite.min()), float(finite.max())
        if kind == "mcts_values":
            lo, hi = 0.0, 1.0
        span = (hi - lo) or 1.0
        n = self.ctrl.config.n
        for r in range(n):
            for c in range(n):
                v = heat[r, c]
                if not np.isfinite(v) or (kind == "mcts_visits" and v <= 0):
                    continue
                s = pygame.Surface((cell, cell), pygame.SRCALPHA)
                s.fill((*heat_color((v - lo) / span), 150))
                self.screen.blit(s, (self.board_rect.x + c * cell, self.board_rect.y + r * cell))
                if cell >= 40 and self.ctrl.board.cells_list[r * n + c] == 0:
                    label = f"{int(v)}" if kind == "mcts_visits" else f"{v:.2f}" \
                        if kind == "mcts_values" else f"{v:.0f}"
                    self.text(label, self.cell_center(r, c, cell), self.small, TEXT, center=True)

    def status_line(self) -> str:
        c = self.ctrl
        if c.is_over:
            if c.winner == 0:
                return "Draw"
            return f"{'X' if c.winner == 1 else 'O'} wins"
        who = "X" if c.to_move == 1 else "O"
        if c.thinking:
            return f"{who} is thinking..."
        return f"{who} to move" + (" (you)" if c.is_human_turn() else "")

    def draw_panel(self) -> None:
        c = self.ctrl
        w, h = self.screen.get_size()
        x = w - PANEL_W + 10
        y = 20
        self.text(self.status_line(), (x, y), self.big, WIN_COL if c.winner else TEXT)
        y += 38
        s = c.setup
        self.text(f"{s.n}x{s.n}  k={s.k}{' exact' if s.exact_k else ''}  {s.time_budget_s:.1f}s/move",
                  (x, y), self.small, MUTED)
        y += 18
        self.text(f"X: {'human' if s.mode.is_human(1) else s.agent_x}", (x, y), self.small, X_COL)
        y += 16
        self.text(f"O: {'human' if s.mode.is_human(-1) else s.agent_o}", (x, y), self.small, O_COL)
        y += 26

        bw, bh = 98, 28
        rows: list[list[tuple[str, Callable[[], object], bool, bool]]] = [
            [("Undo", self.act_undo, False, c.board.ply > 0),
             ("Restart", c.restart, False, True),
             ("Menu", self.act_menu, False, True)],
            [("Step", c.step, False, s.mode is Mode.AI_VS_AI and not c.thinking and not c.is_over),
             ("Auto", self.act_auto, c.autoplay, s.mode is Mode.AI_VS_AI),
             ("Cancel", c.cancel_ai, False, c.thinking or c.autoplay)],
            [("Numbers", self.act_numbers, self.show_numbers, True),
             (f"Ovl:{OVERLAYS[self.overlay_idx][:7]}", self.act_overlay, self.overlay_idx > 0, True),
             ("Speed", self.act_speed, False, s.mode is Mode.AI_VS_AI)],
            [("Save", self.act_save, False, True), ("Load", self.load_last, False, True),
             ("Shot", self.act_shot, False, True)],
        ]
        for row in rows:
            for i, (label, fn, active, enabled) in enumerate(row):
                self.button(pygame.Rect(x + i * (bw + 6), y, bw, bh), label, fn, active, enabled)
            y += bh + 6
        if s.mode is Mode.AI_VS_AI:
            self.text(f"autoplay delay {c.autoplay_delay_s:.1f}s", (x, y), self.small, MUTED)
        y += 22

        last_ai = next((i for i in reversed(c.infos) if not i.human), None)
        self.text("Last AI move", (x, y), self.font)
        y += 20
        if last_ai is not None:
            r, col = c.board.to_rc(last_ai.move)
            sims = f"{last_ai.nodes_per_s:,.0f}/s"
            lines = [f"move ({r},{col})  ply {last_ai.ply + 1}",
                     f"nodes {last_ai.nodes:,}  {sims}",
                     f"depth {last_ai.depth if last_ai.depth is not None else '-'}  "
                     f"time {last_ai.time_s:.2f}s"]
            for ln in lines:
                self.text(ln, (x, y), self.small)
                y += 16
            if last_ai.pv:
                pv = " ".join(f"({a},{b})" for a, b in (c.board.to_rc(m) for m in last_ai.pv[:6]))
                self.text("PV " + pv, (x, y), self.small)
                y += 16
            if last_ai.win_prob is not None:
                self.text(f"win prob (mover) {last_ai.win_prob:.0%}", (x, y), self.small)
                y += 14
                bar = pygame.Rect(x, y, PANEL_W - 30, 10)
                pygame.draw.rect(self.screen, BTN, bar)
                pygame.draw.rect(self.screen, WIN_COL, (bar.x, bar.y, int(bar.w * last_ai.win_prob), 10))
                y += 16
        y += 8
        self.text("History", (x, y), self.font)
        y += 20
        room = max(0, (h - y - 40) // 15)
        for info in c.infos[-room:] if room else []:
            r, col = c.board.to_rc(info.move)
            depth = info.depth if info.depth is not None else "-"
            tag = "you" if info.human else f"{info.nodes:,}n d{depth}"
            self.text(f"{info.ply + 1:>3} {'X' if info.player == 1 else 'O'} ({r},{col}) {tag}",
                      (x, y), self.small, X_COL if info.player == 1 else O_COL)
            y += 15
        msg = c.last_error or self.message
        if msg:
            self.text(msg[:46], (x, h - 24), self.small, HILITE)

    # ----------------------------------------------------------- actions
    def act_undo(self) -> None:
        if self.ctrl.setup.mode is Mode.HUMAN_VS_HUMAN:
            self.ctrl.undo()
        else:
            self.ctrl.undo_turn()

    def act_menu(self) -> None:
        self.ctrl.cancel_ai()
        self.state = "setup"

    def act_auto(self) -> None:
        self.ctrl.autoplay = not self.ctrl.autoplay

    def act_numbers(self) -> None:
        self.show_numbers = not self.show_numbers

    def act_overlay(self) -> None:
        self.overlay_idx = (self.overlay_idx + 1) % len(OVERLAYS)

    def act_speed(self) -> None:
        delays = (1.5, 0.8, 0.4, 0.1)
        cur = self.ctrl.autoplay_delay_s
        self.ctrl.autoplay_delay_s = next((d for d in delays if d < cur - 1e-9), delays[0])

    def act_save(self) -> None:
        path = SAVE_DIR / f"game-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        self.ctrl.save(path)
        self.message = f"saved {path.name}"

    def act_shot(self) -> Path:
        path = SHOT_DIR / f"shot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        self.screenshot(path)
        self.message = f"screenshot {path.name}"
        return path

    def screenshot(self, path: Path) -> None:
        """Save the current frame as an image."""
        path.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(self.screen, str(path))

    # ------------------------------------------------------------ events
    def slider_from_x(self, x: int) -> None:
        lo, hi = BUDGET_RANGE
        frac = min(1.0, max(0.0, (x - self.slider_rect.x) / self.slider_rect.w))
        self.setup = with_budget(self.setup, round(lo + frac * (hi - lo), 1))

    def handle_event(self, ev: pygame.event.Event) -> None:
        if ev.type == pygame.QUIT:
            self.running = False
        elif ev.type == pygame.VIDEORESIZE:
            w, h = max(ev.w, MIN_SIZE[0]), max(ev.h, MIN_SIZE[1])
            self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for b in reversed(self.buttons):
                if b.rect.collidepoint(ev.pos):
                    if b.enabled:
                        b.action()
                    return
            if self.state == "setup":
                if self.slider_rect.inflate(20, 24).collidepoint(ev.pos):
                    self.dragging_slider = True
                    self.slider_from_x(ev.pos[0])
            else:
                cellrc = self.cell_at(ev.pos)
                if cellrc is not None:
                    self.ctrl.human_move(*cellrc)
        elif ev.type == pygame.MOUSEBUTTONUP:
            self.dragging_slider = False
        elif ev.type == pygame.MOUSEMOTION:
            if self.dragging_slider:
                self.slider_from_x(ev.pos[0])
            self.hover = self.cell_at(ev.pos) if self.state == "game" else None
        elif ev.type == pygame.KEYDOWN and self.state == "game":
            keys = {pygame.K_u: self.act_undo, pygame.K_r: self.ctrl.restart,
                    pygame.K_m: self.act_numbers, pygame.K_o: self.act_overlay,
                    pygame.K_s: self.ctrl.step, pygame.K_a: self.act_auto,
                    pygame.K_c: self.ctrl.cancel_ai, pygame.K_p: self.act_shot,
                    pygame.K_ESCAPE: self.act_menu}
            fn = keys.get(ev.key)
            if fn is not None:
                fn()

    def frame(self) -> None:
        """Process pending events, advance the controller and draw one frame."""
        for ev in pygame.event.get():
            self.handle_event(ev)
        if self.state == "game":
            self.ctrl.tick()
            self.draw_game()
        else:
            self.draw_setup()
        pygame.display.flip()

    def run(self) -> None:
        """Main loop until the window is closed."""
        while self.running:
            self.frame()
            self.clock.tick(60)
        self.ctrl.cancel_ai()
        pygame.quit()


def headless_check() -> int:
    """Initialise the GUI with the dummy video driver, render both screens, exit code 0."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    app = App(GameController(Setup(n=11, k=5, mode=Mode.HUMAN_VS_HUMAN)))
    app.frame()
    app.start_game()
    app.ctrl.human_move(5, 5)
    app.frame()
    with tempfile.TemporaryDirectory() as d:
        app.screenshot(Path(d) / "check.png")
    pygame.quit()
    print("gui ok")
    return 0


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--load", type=Path, default=None)
    ap.add_argument("--headless-check", action="store_true")
    args = ap.parse_args(argv)
    if args.headless_check:
        sys.exit(headless_check())
    app = App()
    if args.load:
        app.load_file(args.load)
    app.run()


if __name__ == "__main__":
    main()
