"""Mode: hex — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_hex_browser(self):
    """Enter hex mode (called from mode browser)."""
    self.hex_mode = True
    self.grid.hex_mode = True
    self.grid.birth = {2}
    self.grid.survival = {3, 4}
    self._flash("Hex grid ON (6 neighbors, rule B2/S34)")



def _exit_hex_browser(self):
    """Exit hex mode (called from mode browser)."""
    self.hex_mode = False
    self.grid.hex_mode = False
    self.grid.birth = {3}
    self.grid.survival = {2, 3}
    self._flash("Hex grid OFF")




def register(App):
    """Register hex mode methods on the App class."""
    App._enter_hex_browser = _enter_hex_browser
    App._exit_hex_browser = _exit_hex_browser

