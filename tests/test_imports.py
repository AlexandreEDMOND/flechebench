import unittest

import flechebench
from flechebench.prompts import (
    render_clue_only_prompt,
    render_full_grid_prompt,
    render_pattern_aware_prompt,
)
from flechebench.solvers import DummySolver

from tests.utils import make_sample_puzzle


class ImportTests(unittest.TestCase):
    def test_package_imports(self) -> None:
        self.assertTrue(hasattr(flechebench, "Puzzle"))

    def test_dummy_solver_prediction_has_puzzle_id(self) -> None:
        puzzle = make_sample_puzzle()
        prediction = DummySolver().solve(puzzle)

        self.assertEqual(prediction.puzzle_id, puzzle.puzzle_id)
        self.assertEqual(set(prediction.answers), {"e1", "e2"})

    def test_prompt_templates_render(self) -> None:
        puzzle = make_sample_puzzle()
        entry = puzzle.entries[0]

        self.assertIn(entry.clue, render_clue_only_prompt(entry))
        self.assertIn("C _ A _", render_pattern_aware_prompt(entry, "C _ A _"))
        self.assertIn(puzzle.puzzle_id, render_full_grid_prompt(puzzle))


if __name__ == "__main__":
    unittest.main()
