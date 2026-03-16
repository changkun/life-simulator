"""Tests for stock_market mode."""
from tests.conftest import make_mock_app
from life.modes.stock_market import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.mkt_mode = False
    app.mkt_menu = False
    app.mkt_menu_sel = 0
    app.mkt_running = False
    app.mkt_agents = []
    app.mkt_price_history = []
    app.mkt_bids = []
    app.mkt_asks = []
    app.mkt_steps_per_frame = 1
    return app


def test_enter():
    app = _make_app()
    app._enter_mkt_mode()
    assert app.mkt_menu is True


def test_step_no_crash():
    app = _make_app()
    app.mkt_mode = True
    app._mkt_init(0)
    assert app.mkt_mode is True
    for _ in range(10):
        app._mkt_step()


def test_exit_cleanup():
    app = _make_app()
    app._mkt_init(0)
    app._exit_mkt_mode()
    assert app.mkt_mode is False
    assert app.mkt_agents == []
