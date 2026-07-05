"""Solver interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from flechebench.data.models import Puzzle, PuzzlePrediction


class BaseSolver(ABC):
    """Abstract base class for benchmark solvers."""

    @abstractmethod
    def solve(self, puzzle: Puzzle) -> PuzzlePrediction:
        """Return predictions for every entry in a puzzle."""
