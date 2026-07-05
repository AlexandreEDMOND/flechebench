import unittest

from flechebench.data import Direction, Entry, Puzzle

from tests.utils import make_sample_puzzle


class ModelTests(unittest.TestCase):
    def test_create_valid_puzzle(self) -> None:
        puzzle = make_sample_puzzle()

        self.assertEqual(puzzle.puzzle_id, "sample-001")
        self.assertEqual(puzzle.language, "fr")
        self.assertEqual(len(puzzle.entries), 2)

    def test_invalid_entry_length(self) -> None:
        with self.assertRaises(ValueError):
            Entry(
                entry_id="bad",
                clue="Article defini",
                answer="LE",
                start_row=0,
                start_column=0,
                direction=Direction.ACROSS,
                length=3,
            )

    def test_invalid_puzzle_dimensions(self) -> None:
        with self.assertRaises(ValueError):
            Puzzle(puzzle_id="bad", width=0, height=3, entries=[])


if __name__ == "__main__":
    unittest.main()
