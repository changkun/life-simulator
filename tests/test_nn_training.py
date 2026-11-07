"""Tests for nn_training mode."""
import random
from tests.conftest import make_mock_app
from life.modes.nn_training import register, NNTRAIN_PRESETS, _MiniNet, _gen_xor


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.nntrain_mode = False
    app.nntrain_menu = False
    app.nntrain_menu_sel = 0
    app.nntrain_running = False
    app.nntrain_net = None
    app.nntrain_data = None
    return app


def test_enter():
    app = _make_app()
    app._enter_nntrain_mode()
    assert app.nntrain_menu is True


def test_step_no_crash():
    app = _make_app()
    app.nntrain_mode = True
    app._nntrain_init(0)  # XOR — small, fast
    assert app.nntrain_net is not None
    for _ in range(10):
        app._nntrain_step()


def test_exit_cleanup():
    app = _make_app()
    app._nntrain_init(0)
    app._exit_nntrain_mode()
    assert app.nntrain_mode is False
    assert app.nntrain_net is None


def test_all_presets_init():
    """Every preset initializes without error."""
    for idx in range(len(NNTRAIN_PRESETS)):
        app = _make_app()
        app._nntrain_init(idx)
        assert app.nntrain_net is not None
        assert app.nntrain_data is not None
        assert len(app.nntrain_data) > 0


def test_xor_loss_decreases():
    """Training on XOR should reduce loss over many epochs."""
    random.seed(42)
    net = _MiniNet([2, 4, 1], act_name="sigmoid", lr=1.0)
    data = _gen_xor(4)
    loss_0, _ = net.train_batch(data)
    for _ in range(200):
        net.train_batch(data)
    loss_final = net.loss_history[-1]
    assert loss_final < loss_0, "Loss should decrease after training on XOR"


def test_step_advances_epoch():
    """Each step should advance the epoch counter."""
    app = _make_app()
    app._nntrain_init(0)
    epoch_before = app.nntrain_epoch
    app._nntrain_step()
    assert app.nntrain_epoch > epoch_before


def test_pause_prevents_training():
    """Paused mode should not advance."""
    app = _make_app()
    app._nntrain_init(0)
    app.nntrain_paused = True
    epoch_before = app.nntrain_epoch
    app._nntrain_step()
    assert app.nntrain_epoch == epoch_before


def test_single_output_net_stays_in_unit_range_with_relu_hidden():
    """A ReLU hidden net must not kill its lone output unit (Two Moons stuck at 50%)."""
    for seed in range(5):
        random.seed(seed)
        app = _make_app()
        app._nntrain_init(3)  # Two Moons, relu
        for _ in range(150):
            app._nntrain_step()
        net = app.nntrain_net
        assert 0.0 < net.activations[-1][0] < 1.0
        assert net.acc_history[-1] > 0.55
        assert net.loss_history[-1] < net.loss_history[0] or net.loss_history[-1] < 0.2
