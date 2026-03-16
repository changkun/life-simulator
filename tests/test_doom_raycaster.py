"""Tests for life.modes.doom_raycaster — Doom Raycaster mode."""
from tests.conftest import make_mock_app
from life.modes.doom_raycaster import register


def _make_app():
    app = make_mock_app()
    app.doomrc_mode = False
    app.doomrc_menu = False
    app.doomrc_menu_sel = 0
    app.doomrc_running = False
    app.doomrc_generation = 0
    app.doomrc_preset_name = ""
    app.doomrc_map = []
    app.doomrc_map_h = 0
    app.doomrc_map_w = 0
    app.doomrc_px = 0.0
    app.doomrc_py = 0.0
    app.doomrc_pa = 0.0
    app.doomrc_fov = 3.14159 / 3.0
    app.doomrc_depth = 16.0
    app.doomrc_speed = 0.15
    app.doomrc_rot_speed = 0.08
    app.doomrc_show_map = True
    app.doomrc_show_help = True
    type(app).DOOMRC_PRESETS = [
        ("Classic Maze", "Simple maze corridors", "maze"),
        ("Arena", "Open arena with pillars", "arena"),
    ]
    type(app).DOOMRC_MAPS = {
        "maze": [
            "########",
            "#......#",
            "#.##.#.#",
            "#....#.#",
            "#.####.#",
            "#......#",
            "#.#..#.#",
            "########",
        ],
        "arena": [
            "##########",
            "#........#",
            "#..#..#..#",
            "#........#",
            "#..#..#..#",
            "#........#",
            "##########",
        ],
    }
    type(app).DOOMRC_SHADE_WALL = "█▓▒░·"
    type(app).DOOMRC_SHADE_FLOOR = "#x=-.  "
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_doomrc_mode()
    assert app.doomrc_menu is True
    assert app.doomrc_menu_sel == 0


def test_step_no_crash():
    app = _make_app()
    app.doomrc_mode = True
    app._doomrc_init(0)
    assert app.doomrc_mode is True
    assert app.doomrc_menu is False
    for _ in range(10):
        app._doomrc_step()
    assert app.doomrc_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.doomrc_mode = True
    app._doomrc_init(0)
    app._exit_doomrc_mode()
    assert app.doomrc_mode is False
    assert app.doomrc_menu is False
    assert app.doomrc_running is False
