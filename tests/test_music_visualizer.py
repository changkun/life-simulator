"""Tests for life.modes.music_visualizer — Music Visualizer mode."""
from tests.conftest import make_mock_app
from life.modes.music_visualizer import register


def _make_app():
    app = make_mock_app()
    app.musvis_mode = False
    app.musvis_menu = False
    app.musvis_menu_sel = 0
    app.musvis_running = False
    app.musvis_generation = 0
    app.musvis_preset_name = ""
    app.musvis_preset_idx = 0
    app.musvis_time = 0.0
    app.musvis_spectrum = []
    app.musvis_waveform = []
    app.musvis_peak_history = []
    app.musvis_particles = []
    app.musvis_beat_energy = 0.0
    app.musvis_beat_avg = 0.0
    app.musvis_beat_flash = 0.0
    app.musvis_bass_energy = 0.0
    app.musvis_mid_energy = 0.0
    app.musvis_high_energy = 0.0
    app.musvis_tone_phase = 0.0
    app.musvis_view_mode = 0
    app.musvis_color_mode = 0
    app.musvis_sensitivity = 1.0
    app.musvis_num_bars = 32
    type(app).MUSVIS_PRESETS = [
        ("Spectrum Bars", "FFT frequency spectrum as vertical bars"),
        ("Waveform", "Oscilloscope-style audio waveform"),
        ("Particles", "Beat-reactive particle explosions"),
        ("Combined", "Spectrum + waveform + particles"),
        ("Bass Tunnel", "Bass-reactive tunnel zoom effect"),
        ("Frequency Rain", "Spectrum as falling rain columns"),
    ]
    type(app).MUSVIS_COLOR_NAMES = ["Spectrum", "Fire", "Ocean", "Neon"]
    type(app).MUSVIS_TONE_PATTERNS = [
        [261, 329, 392, 523],
        [220, 277, 330, 440],
        [196, 247, 294, 392],
        [0, 0, 330, 330],
    ]
    type(app).MUSVIS_BAR_CHARS = " ░▒▓█"
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_musvis_mode()
    assert app.musvis_menu is True
    assert app.musvis_menu_sel == 0


def test_step_no_crash():
    app = _make_app()
    app.musvis_mode = True
    app._musvis_init(0)
    assert app.musvis_mode is True
    assert app.musvis_menu is False
    for _ in range(10):
        app._musvis_step()
    assert app.musvis_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.musvis_mode = True
    app._musvis_init(0)
    app._exit_musvis_mode()
    assert app.musvis_mode is False
    assert app.musvis_menu is False
    assert app.musvis_running is False
