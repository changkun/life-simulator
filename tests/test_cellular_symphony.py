"""Tests for life.modes.cellular_symphony — Cellular Symphony mode."""
from tests.conftest import make_mock_app
from life.modes.cellular_symphony import register, RULE_PRESETS


class _FakeSound:
    def __init__(self, enabled=False):
        self.enabled = enabled

    def toggle(self):
        self.enabled = not self.enabled
        return self.enabled


def _make_app():
    app = make_mock_app()
    app.symphony_mode = False
    register(type(app))
    return app


def test_octave_key_cycles_through_all_ranges():
    app = _make_app()
    app._enter_symphony_mode()
    seen = []
    for _ in range(4):
        app._handle_symphony_key(ord('o'))
        seen.append(app.symphony_octave_range)
    assert seen == [4, 5, 2, 3]


def test_exit_restores_rule_and_sound():
    app = _make_app()
    app.sound = _FakeSound(enabled=False)
    app.grid.birth, app.grid.survival = {3, 6}, {2, 3}
    app._enter_symphony_mode()
    assert app.grid.birth == RULE_PRESETS[0]["b"]
    assert app.sound.enabled is True
    app._exit_symphony_mode()
    assert app.grid.birth == {3, 6}
    assert app.grid.survival == {2, 3}
    assert app.sound.enabled is False


def test_exit_keeps_sound_the_user_enabled():
    app = _make_app()
    app.sound = _FakeSound(enabled=True)
    app._enter_symphony_mode()
    app._exit_symphony_mode()
    assert app.sound.enabled is True


def test_advance_row_steps_ca_after_full_scan():
    app = _make_app()
    app._enter_symphony_mode()
    app.symphony_muted = True
    for _ in range(app.grid.rows):
        app._handle_symphony_key(10)
    assert app.symphony_gen_count == 1
    assert app.symphony_scan_row == 0

