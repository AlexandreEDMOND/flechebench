"""Deterministic baseline metrics."""

from __future__ import annotations

from flechebench.data.models import EvaluationResult, Puzzle, PuzzlePrediction


def exact_word_accuracy(expected: dict[str, str], predicted: dict[str, str]) -> float:
    """Return the fraction of entries predicted exactly."""

    if not expected:
        return 0.0
    correct = sum(
        1 for entry_id, answer in expected.items() if predicted.get(entry_id, "") == answer
    )
    return correct / len(expected)


def character_accuracy(expected: dict[str, str], predicted: dict[str, str]) -> float:
    """Return character accuracy over aligned answer positions."""

    total = 0
    correct = 0
    for entry_id, answer in expected.items():
        guess = predicted.get(entry_id, "")
        total += len(answer)
        correct += sum(
            1 for index, char in enumerate(answer) if index < len(guess) and guess[index] == char
        )
    if total == 0:
        return 0.0
    return correct / total


def normalized_edit_similarity(expected: str, predicted: str) -> float:
    """Return 1 - normalized Levenshtein distance for two strings."""

    max_length = max(len(expected), len(predicted))
    if max_length == 0:
        return 1.0
    distance = _levenshtein_distance(expected, predicted)
    return 1.0 - (distance / max_length)


def evaluate_words(puzzle: Puzzle, prediction: PuzzlePrediction) -> EvaluationResult:
    """Evaluate word-level predictions for a puzzle."""

    if prediction.puzzle_id != puzzle.puzzle_id:
        raise ValueError("prediction puzzle_id must match puzzle puzzle_id")

    expected = {entry.entry_id: entry.answer for entry in puzzle.entries}
    edit_scores = [
        normalized_edit_similarity(answer, prediction.answers.get(entry_id, ""))
        for entry_id, answer in expected.items()
    ]
    average_edit_similarity = sum(edit_scores) / len(edit_scores) if edit_scores else 0.0

    return EvaluationResult(
        puzzle_id=puzzle.puzzle_id,
        metrics={
            "exact_word_accuracy": exact_word_accuracy(expected, prediction.answers),
            "character_accuracy": character_accuracy(expected, prediction.answers),
            "average_normalized_edit_similarity": average_edit_similarity,
            # TODO: add cell accuracy once full-grid representation is finalized.
        },
    )


def _levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            substitution_cost = 0 if left_char == right_char else 1
            current.append(
                min(
                    previous[right_index] + 1,
                    current[right_index - 1] + 1,
                    previous[right_index - 1] + substitution_cost,
                )
            )
        previous = current
    return previous[-1]
