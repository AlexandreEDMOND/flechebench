import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from flechebench.game import assisted
from flechebench.game.assisted import (
    AssistedGame,
    chat_completion_metadata,
    extract_answer,
    load_env_file,
    normalize_answer,
    responses_model_id,
    responses_text,
    run_assisted_game,
)


class FakeRunner:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.prompts: list[str] = []

    def ask(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.outputs.pop(0)


def make_puzzle() -> dict:
    return {
        "puzzle_id": "test_grid",
        "width": 4,
        "height": 2,
        "clue_cells": [{"row": 0, "column": 0}],
        "entries": [
            {
                "entry_id": "001",
                "clue": "Animal",
                "answer": "CHAT",
                "length": 4,
                "direction": "across",
                "start": {"row": 1, "column": 0},
            }
        ],
    }


class AssistedGameTests(unittest.TestCase):
    def test_normalize_answer(self) -> None:
        self.assertEqual(normalize_answer(" é-t rier "), "ETRIER")
        self.assertEqual(normalize_answer("cœur"), "COEUR")

    def test_extract_answer_from_json(self) -> None:
        self.assertEqual(extract_answer('{"answer":"tirera"}'), "tirera")
        self.assertEqual(extract_answer('Voici: {"answer":"TIRERA"}'), "TIRERA")

    def test_responses_helpers(self) -> None:
        self.assertEqual(responses_model_id("opencode/gpt-5.4-mini"), "gpt-5.4-mini")
        self.assertEqual(responses_model_id("gpt-5.4-mini"), "gpt-5.4-mini")
        self.assertEqual(responses_text({"output_text": '{"answer":"TIRERA"}'}), '{"answer":"TIRERA"}')
        payload = {
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": '{"answer":"TIRERA"}'},
                    ]
                }
            ]
        }
        self.assertEqual(responses_text(payload), '{"answer":"TIRERA"}')

    def test_chat_completion_metadata(self) -> None:
        payload = {
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {
                        "content": "",
                        "reasoning_content": "hidden reasoning",
                    },
                }
            ],
            "usage": {
                "completion_tokens": 8192,
                "completion_tokens_details": {"reasoning_tokens": 8192},
            },
        }

        self.assertEqual(
            chat_completion_metadata(payload),
            {
                "finish_reason": "length",
                "content_length": 0,
                "reasoning_length": 16,
                "completion_tokens": 8192,
                "reasoning_tokens": 8192,
            },
        )

    def test_load_env_file(self) -> None:
        import os

        original = os.environ.pop("OPENCODE_API_KEY", None)
        try:
            with TemporaryDirectory() as temp_dir:
                env_path = Path(temp_dir) / ".env"
                env_path.write_text("OPENCODE_API_KEY=test-key\n", encoding="utf-8")

                load_env_file(env_path)

                self.assertEqual(os.environ["OPENCODE_API_KEY"], "test-key")
        finally:
            if original is None:
                os.environ.pop("OPENCODE_API_KEY", None)
            else:
                os.environ["OPENCODE_API_KEY"] = original

    def test_game_retries_until_correct(self) -> None:
        runner = FakeRunner(['{"answer":"chien"}', '{"answer":"chat"}'])
        game = AssistedGame(make_puzzle(), runner, max_attempts_per_entry=3, max_passes=1)

        with redirect_stdout(StringIO()):
            summary = game.run()

        self.assertEqual(summary["solved"], 1)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(game.letters[(1, 0)], "C")
        self.assertEqual(game.letters[(1, 3)], "T")

    def test_completed_entry_is_validated_without_llm(self) -> None:
        runner = FakeRunner([])
        game = AssistedGame(make_puzzle(), runner, max_attempts_per_entry=3, max_passes=1)
        game.letters[(1, 0)] = "C"
        game.letters[(1, 1)] = "H"
        game.letters[(1, 2)] = "A"
        game.letters[(1, 3)] = "T"

        with redirect_stdout(StringIO()):
            summary = game.run()

        self.assertEqual(summary["solved"], 1)
        self.assertEqual(runner.prompts, [])

    def test_completed_entry_with_wrong_letters_raises_logic_error(self) -> None:
        runner = FakeRunner([])
        game = AssistedGame(make_puzzle(), runner, max_attempts_per_entry=3, max_passes=1)
        game.letters[(1, 0)] = "C"
        game.letters[(1, 1)] = "H"
        game.letters[(1, 2)] = "I"
        game.letters[(1, 3)] = "T"

        with self.assertRaisesRegex(RuntimeError, "deja complete mais incoherente"):
            with redirect_stdout(StringIO()):
                game.run()

        self.assertEqual(runner.prompts, [])

    def test_go_runner_receives_max_output_tokens(self) -> None:
        captured: dict[str, int] = {}

        class FakeGoRunner:
            def __init__(self, **kwargs: object) -> None:
                captured["max_tokens"] = int(kwargs["max_tokens"])

            def ask(self, prompt: str) -> str:
                return '{"answer":"chat"}'

        with TemporaryDirectory() as temp_dir:
            puzzle_path = Path(temp_dir) / "puzzle.json"
            puzzle_path.write_text(json.dumps(make_puzzle()), encoding="utf-8")

            with patch.object(assisted, "OpencodeGoApiRunner", FakeGoRunner):
                with redirect_stdout(StringIO()):
                    run_assisted_game(
                        puzzle_path,
                        runner_name="go",
                        max_output_tokens=123,
                        max_attempts_per_entry=1,
                    )

        self.assertEqual(captured["max_tokens"], 123)

    def test_unsolved_entry_is_retried_on_next_pass(self) -> None:
        puzzle = {
            "puzzle_id": "retry_grid",
            "width": 2,
            "height": 1,
            "clue_cells": [],
            "entries": [
                {
                    "entry_id": "001",
                    "clue": "Deux lettres",
                    "answer": "AB",
                    "length": 2,
                    "direction": "across",
                    "start": {"row": 0, "column": 0},
                },
                {
                    "entry_id": "002",
                    "clue": "Premiere lettre",
                    "answer": "A",
                    "length": 1,
                    "direction": "down",
                    "start": {"row": 0, "column": 0},
                },
            ],
        }
        runner = FakeRunner(['{"answer":"zz"}', '{"answer":"a"}', '{"answer":"ab"}'])
        game = AssistedGame(puzzle, runner, max_attempts_per_entry=1, max_passes=2)

        with redirect_stdout(StringIO()):
            summary = game.run()

        self.assertEqual(summary["solved"], 2)
        self.assertEqual(runner.prompts[2].count("Entree: 001"), 1)
        self.assertIn("Motif connu: A _", runner.prompts[2])

    def test_entries_with_more_known_letters_are_prioritized(self) -> None:
        puzzle = {
            "puzzle_id": "priority_grid",
            "width": 2,
            "height": 2,
            "clue_cells": [],
            "entries": [
                {
                    "entry_id": "001",
                    "clue": "Premiere ligne",
                    "answer": "AB",
                    "length": 2,
                    "direction": "across",
                    "start": {"row": 0, "column": 0},
                },
                {
                    "entry_id": "002",
                    "clue": "Deuxieme ligne",
                    "answer": "CD",
                    "length": 2,
                    "direction": "across",
                    "start": {"row": 1, "column": 0},
                },
            ],
        }
        runner = FakeRunner(['{"answer":"cd"}', '{"answer":"ab"}'])
        game = AssistedGame(puzzle, runner, max_attempts_per_entry=1, max_passes=1)
        game.letters[(1, 0)] = "C"

        with redirect_stdout(StringIO()):
            summary = game.run()

        self.assertEqual(summary["solved"], 2)
        self.assertIn("Entree: 002", runner.prompts[0])
        self.assertIn("Motif connu: C _", runner.prompts[0])


if __name__ == "__main__":
    unittest.main()
