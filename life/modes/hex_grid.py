"""Hexagonal Grid — Conway-style rules on a hex lattice with six neighbors (B2/S34)."""


def _enter_hex_browser(self):
    """Switch the main grid to hex mode with rule B2/S34."""
    self.hex_mode = True
    self.grid.hex_mode = True
    self.grid.birth = {2}
    self.grid.survival = {3, 4}
    self._flash("Hex grid ON (6 neighbors, rule B2/S34)")



def _exit_hex_browser(self):
    """Switch the main grid back to square cells with rule B3/S23."""
    self.hex_mode = False
    self.grid.hex_mode = False
    self.grid.birth = {3}
    self.grid.survival = {2, 3}
    self._flash("Hex grid OFF")



def register(App):
    """Register hex mode methods on the App class."""
    App._enter_hex_browser = _enter_hex_browser
    App._exit_hex_browser = _exit_hex_browser

