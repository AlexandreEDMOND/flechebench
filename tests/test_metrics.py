import unittest

from flechebench.evaluation import evaluate_words, exact_word_accuracy
from flechebench.solvers import DummySolver

from tests.utils import make_sample_puzzle


class MetricsTests(unittest.TestCase):
    def test_exact_word_accuracy(self) -> None:
        expected = {"e1": "CHAT", "e2": "AMI"}
        predicted = {"e1": "CHAT", "e2": "AME"}

        self.assertEqual(exact_word_accuracy(expected, predicted), 0.5)

    def test_evaluate_words(self) -> None:
        puzzle = make_sample_puzzle()
        prediction = DummySolver().solve(puzzle)
        result = evaluate_words(puzzle, prediction)

        self.assertEqual(result.puzzle_id, puzzle.puzzle_id)
        self.assertEqual(result.metrics["exact_word_accuracy"], 0.0)
        self.assertEqual(result.metrics["character_accuracy"], 0.0)


if __name__ == "__main__":
    unittest.main()
