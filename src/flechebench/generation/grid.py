"""Grid generation placeholders.

Real synthetic generation will be added after the puzzle data contract is
stable.
"""


def generate_placeholder_grid(width: int, height: int) -> list[list[str]]:
    """Return an empty rectangular grid for smoke tests and examples."""

    if width <= 0:
        raise ValueError("grid width must be positive")
    if height <= 0:
        raise ValueError("grid height must be positive")
    return [["" for _ in range(width)] for _ in range(height)]
