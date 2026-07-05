"""Core data structures for FlecheBench."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Direction(str, Enum):
    """Entry direction in a puzzle grid."""

    ACROSS = "across"
    DOWN = "down"


@dataclass(frozen=True)
class Cell:
    """A single grid coordinate."""

    row: int
    column: int
    value: str | None = None
    is_blocked: bool = False

    def __post_init__(self) -> None:
        if self.row < 0:
            raise ValueError("cell row must be non-negative")
        if self.column < 0:
            raise ValueError("cell column must be non-negative")
        if self.value is not None and len(self.value) != 1:
            raise ValueError("cell value must be a single character")


@dataclass(frozen=True)
class Entry:
    """One answer entry and its clue."""

    entry_id: str
    clue: str
    answer: str
    start_row: int
    start_column: int
    direction: Direction
    length: int

    def __post_init__(self) -> None:
        if not self.entry_id:
            raise ValueError("entry_id must not be empty")
        if self.start_row < 0:
            raise ValueError("entry start_row must be non-negative")
        if self.start_column < 0:
            raise ValueError("entry start_column must be non-negative")
        if self.length <= 0:
            raise ValueError("entry length must be positive")
        if len(self.answer) != self.length:
            raise ValueError("entry length must match answer length")
        if not isinstance(self.direction, Direction):
            raise TypeError("entry direction must be a Direction")


@dataclass(frozen=True)
class Puzzle:
    """A FlecheBench puzzle instance."""

    puzzle_id: str
    width: int
    height: int
    entries: list[Entry]
    language: str = "fr"
    blocked_cells: set[tuple[int, int]] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.puzzle_id:
            raise ValueError("puzzle_id must not be empty")
        if self.width <= 0:
            raise ValueError("puzzle width must be positive")
        if self.height <= 0:
            raise ValueError("puzzle height must be positive")
        for row, column in self.blocked_cells:
            if row < 0 or column < 0:
                raise ValueError("blocked cell coordinates must be non-negative")
            if row >= self.height or column >= self.width:
                raise ValueError("blocked cell coordinates must be inside the grid")
        for entry in self.entries:
            if entry.start_row >= self.height or entry.start_column >= self.width:
                raise ValueError("entry start must be inside the grid")


@dataclass(frozen=True)
class PuzzlePrediction:
    """Predicted answers for a puzzle."""

    puzzle_id: str
    answers: dict[str, str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.puzzle_id:
            raise ValueError("prediction puzzle_id must not be empty")


@dataclass(frozen=True)
class EvaluationResult:
    """Metric output for one evaluated puzzle or run."""

    puzzle_id: str
    metrics: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.puzzle_id:
            raise ValueError("evaluation puzzle_id must not be empty")
