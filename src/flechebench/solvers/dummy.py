"""Placeholder solver for tests and examples."""

from __future__ import annotations

from flechebench.data.models import Puzzle, PuzzlePrediction
from flechebench.solvers.base import BaseSolver


class DummySolver(BaseSolver):
    """Solver that returns empty predictions for each entry."""

    def solve(self, puzzle: Puzzle) -> PuzzlePrediction:
        return PuzzlePrediction(
            puzzle_id=puzzle.puzzle_id,
            answers={entry.entry_id: "" for entry in puzzle.entries},
            metadata={"solver": "dummy"},
        )
