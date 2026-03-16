"""Tests for neural_ca mode."""
from tests.conftest import make_mock_app
from life.modes.neural_ca import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    # NCA needs these attributes
    app.nca_mode = False
    app.nca_menu = False
    app.nca_menu_sel = 0
    app.nca_running = False
    app.nca_training = False
    app.nca_state = None
    app.nca_params = None
    app.nca_target = None
    app.nca_loss_history = []
    app.nca_custom_target = None
    app.nca_grid_h = 12
    app.nca_grid_w = 16
    app.nca_grow_steps = 20
    app.nca_es_pop = 8
    app.nca_es_lr = 0.03
    app.nca_es_sigma = 0.02
    app.nca_target_idx = 0
    app.nca_view = 0
    app.nca_grid_h_actual = 12
    app.nca_grid_w_actual = 16
    app.nca_train_gen = 0
    app.nca_best_loss = float("inf")
    app.nca_best_params = None
    app.nca_sim_step = 0
    app.nca_phase = "idle"
    app.nca_drawing = False
    app.nca_draw_val = 1
    app.colors_enabled = False
    return app


def test_enter():
    app = _make_app()
    app._enter_nca_mode()
    assert app.nca_menu is True
    assert app.nca_mode is False


def test_step_no_crash():
    app = _make_app()
    app.nca_mode = True
    app._nca_init()
    assert app.nca_mode is True
    assert app.nca_state is not None
    # Run in inference mode (not training, too slow)
    app.nca_running = True
    for _ in range(10):
        app._nca_step()


def test_exit_cleanup():
    app = _make_app()
    app.nca_mode = True
    app._nca_init()
    app._exit_nca_mode()
    assert app.nca_mode is False
    assert app.nca_state is None
