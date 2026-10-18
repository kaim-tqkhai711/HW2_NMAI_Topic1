import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import subprocess  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

from agents.mcts import MCTSAgent, MCTSConfig  # noqa: E402
from agents.random_agent import RandomAgent  # noqa: E402
from gui import app as gui_app  # noqa: E402
from gui.controller import GameController, Mode, Setup  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def make_app(mode: Mode = Mode.HUMAN_VS_HUMAN, n: int = 11, k: int = 5) -> gui_app.App:
    reg = {"random": lambda seed: RandomAgent(seed=seed)}
    ctl = GameController(Setup(n, k, False, mode, "random", "random", 0.1), reg)
    return gui_app.App(ctl)


def click(app: gui_app.App, pos: tuple[int, int]) -> None:
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))
    app.frame()


def click_label(app: gui_app.App, label: str) -> None:
    b = next(b for b in app.buttons if b.label.startswith(label))
    click(app, b.rect.center)


@pytest.fixture(autouse=True)
def _quit() -> None:
    yield
    pygame.quit()


def test_window_is_large_enough_for_11x11() -> None:
    app = make_app()
    w, h = app.screen.get_size()
    assert w >= 900 and h >= 700
    app.start_game()
    app.frame()
    rect, cell = app.layout()
    assert cell >= 40 and rect.right <= w - gui_app.PANEL_W and rect.bottom <= h


def test_setup_screen_controls_change_the_setup() -> None:
    app = make_app()
    app.frame()
    click_label(app, "7")
    assert app.setup.n == 7
    click_label(app, "4")
    assert app.setup.k == 4
    click_label(app, "off")
    assert app.setup.exact_k
    click_label(app, Mode.AI_VS_AI.value)
    assert app.setup.mode is Mode.AI_VS_AI
    s = app.slider_rect
    click(app, (s.x + s.w, s.centery))
    assert app.setup.time_budget_s == 5.0
    click(app, (s.x, s.centery))
    assert app.setup.time_budget_s == 0.1


def test_start_click_play_and_win_flow() -> None:
    app = make_app(Mode.HUMAN_VS_HUMAN, n=5, k=4)
    app.frame()
    app.set_setup(n=5, k=4, mode=Mode.HUMAN_VS_HUMAN)
    app.frame()
    click_label(app, "Start game")
    assert app.state == "game"
    app.frame()
    n = 5
    cell = app.board_rect.w // n

    def at(r: int, c: int) -> tuple[int, int]:
        return (app.board_rect.x + c * cell + cell // 2, app.board_rect.y + r * cell + cell // 2)

    for rc in [(0, 0), (4, 4), (0, 1), (4, 3), (0, 2), (3, 3), (0, 3)]:
        click(app, at(*rc))
    assert app.ctrl.is_over and app.ctrl.winner == 1
    app.frame()
    assert app.status_line() == "X wins"
    # clicks after the end change nothing
    ply = app.ctrl.board.ply
    click(app, at(2, 2))
    assert app.ctrl.board.ply == ply


def test_panel_buttons_undo_numbers_overlay_and_menu() -> None:
    app = make_app()
    app.start_game()
    app.frame()
    cell = app.board_rect.w // 11
    click(app, (app.board_rect.x + 5 * cell + 3, app.board_rect.y + 5 * cell + 3))
    assert app.ctrl.board.ply == 1
    click_label(app, "Undo")
    assert app.ctrl.board.ply == 0
    click_label(app, "Numbers")
    assert app.show_numbers
    click_label(app, "Ovl")
    assert app.overlay_idx == 1
    click_label(app, "Menu")
    assert app.state == "setup"


def test_keyboard_shortcuts_and_screenshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gui_app, "SHOT_DIR", tmp_path / "shots")
    monkeypatch.setattr(gui_app, "SAVE_DIR", tmp_path / "saves")
    app = make_app()
    app.start_game()
    app.ctrl.human_move(5, 5)
    for key in (pygame.K_m, pygame.K_o, pygame.K_o, pygame.K_o, pygame.K_p):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
        app.frame()
    shots = list((tmp_path / "shots").glob("*.png"))
    assert len(shots) == 1 and shots[0].stat().st_size > 1000
    img = pygame.image.load(str(shots[0]))
    assert img.get_width() >= 900
    click_label(app, "Save")
    saves = list((tmp_path / "saves").glob("*.json"))
    assert len(saves) == 1
    app.ctrl.restart()
    app.load_last()
    assert app.ctrl.board.ply == 1 and app.state == "game"


def test_ai_vs_ai_autoplay_renders_until_the_end() -> None:
    app = make_app(Mode.AI_VS_AI, n=4, k=3)
    app.start_game()
    app.ctrl.autoplay = True
    app.ctrl.autoplay_delay_s = 0.0
    for _ in range(400):
        app.frame()
        if app.ctrl.is_over:
            break
        pygame.time.wait(5)
    assert app.ctrl.is_over
    app.frame()
    assert app.status_line() in ("Draw", "X wins", "O wins")


def test_all_overlays_and_numbers_render_on_a_busy_board() -> None:
    reg = {"mcts": lambda seed: MCTSAgent(MCTSConfig(max_iterations=60, seed=seed)),
           "random": lambda seed: RandomAgent(seed=seed)}
    app = gui_app.App(GameController(Setup(7, 4, False, Mode.AI_VS_HUMAN, "mcts", "random", 0.1),
                                     reg))
    app.start_game()
    for _ in range(400):
        app.frame()
        if app.ctrl.board.ply >= 1:
            break
        pygame.time.wait(5)
    assert app.ctrl.board.ply == 1
    app.show_numbers = True
    for idx in range(len(gui_app.OVERLAYS)):
        app.overlay_idx = idx
        app.frame()
    app.ctrl.human_move(0, 0)
    app.frame()


def test_load_failure_is_reported_not_raised(tmp_path: Path) -> None:
    app = make_app()
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    app.load_file(bad)
    assert app.message.startswith("load failed") and app.state == "setup"


def test_module_main_initialises_headless() -> None:
    out = subprocess.run([sys.executable, "-m", "gui.app", "--headless-check"], cwd=ROOT,
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and "gui ok" in out.stdout


def test_heat_color_ramp_is_monotone_in_warmth() -> None:
    cold, mid, hot = (gui_app.heat_color(v) for v in (0.0, 0.5, 1.0))
    assert cold[2] > cold[0] and hot[0] > hot[2] and mid != cold != hot
    assert gui_app.heat_color(-3) == cold and gui_app.heat_color(9) == hot
