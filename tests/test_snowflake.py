"""Tests for Snowflake Growth mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.snowflake import register


class TestSnowflake:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._snowflake_init(0)
        assert self.app.snowflake_mode is True
        assert self.app.snowflake_generation == 0
        assert len(self.app.snowflake_frozen) > 0
        assert self.app.snowflake_steps_per_frame == 1
        assert self.app.snowflake_frozen_count == 1

    def test_step_no_crash(self):
        self.app._snowflake_init(0)
        for _ in range(10):
            self.app._snowflake_step()
        assert self.app.snowflake_generation == 10

    def test_exit_cleanup(self):
        self.app._snowflake_init(0)
        assert self.app.snowflake_mode is True
        self.app._exit_snowflake_mode()
        assert self.app.snowflake_mode is False
        assert self.app.snowflake_running is False
