"""Terminal-based Conway's Game of Life simulator — modular package."""


def main():
    """Entry point — imports lazily to avoid circular dependencies."""
    from life.app import main as _main
    _main()


__all__ = ["main"]
