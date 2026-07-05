"""Utilities for Le Parisien / RCI Jeux mots fleches grids."""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.request import urlopen


MENU_URL = "https://static.rcijeux.fr/drupal_game/leparisien/menu/js/jeux_mfleches{force}.js"
GRID_URL = (
    "https://static.rcijeux.fr/drupal_game/leparisien/"
    "mfleches{force}/grids/mfleches_{force}_{number}.mfj"
)


DEPRECATED_ARROW_SPECS = {
    "a": "s1",
    "b": "s2",
    "c": "s0",
    "d": "s3",
    "y": "s4",
    "é": "s5",
    "l": "d0",
    "v": "d1",
    "g": "d2",
    "q": "d3",
    "m": "d0",
    "w": "d1",
    "h": "d2",
    "r": "d3",
    "k": "d0",
    "u": "d1",
    "f": "d2",
    "p": "d3",
    "n": "d0",
    "x": "d1",
    "i": "d2",
    "s": "d3",
    "j": "d0",
    "t": "d1",
    "e": "d2",
    "o": "d3",
}

CELL_ARROW_SPECS = {
    "s0": ["hb"],
    "s1": ["hd"],
    "s2": ["bb"],
    "s3": ["bd"],
    "s4": ["td"],
    "s5": ["gb"],
    "d0": ["hb", "bb"],
    "d1": ["hb", "bd"],
    "d2": ["hd", "bb"],
    "d3": ["hd", "bd"],
}

ARROWS = {
    "hd": {"column": 1, "row": 0, "direction": "across"},
    "hb": {"column": 1, "row": 0, "direction": "down"},
    "bd": {"column": 0, "row": 1, "direction": "across"},
    "bb": {"column": 0, "row": 1, "direction": "down"},
    "td": {"column": 0, "row": -1, "direction": "across"},
    "gb": {"column": -1, "row": 0, "direction": "down"},
}


@dataclass(frozen=True)
class LeParisienIssue:
    """One published grid in an RCI menu file."""

    published_on: date
    number: str
    force: int


def fetch_text(url: str) -> str:
    """Fetch text from a URL using only the standard library."""

    with urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8-sig")


def parse_menu(js_text: str, force: int) -> list[LeParisienIssue]:
    """Parse a `jeux_mflechesN.js` menu file."""

    issues: list[LeParisienIssue] = []
    for match in re.finditer(r'"(\d{6})"\s*:\s*\["(\d+)"\s*,\s*"(\d+)"', js_text):
        date_token, number, issue_force = match.groups()
        day = int(date_token[0:2])
        month = int(date_token[2:4])
        year = 2000 + int(date_token[4:6])
        parsed_force = int(issue_force)
        if parsed_force == force:
            issues.append(LeParisienIssue(date(year, month, day), number, parsed_force))
    return sorted(issues, key=lambda issue: issue.published_on)


def latest_issues(force: int, count: int, through_date: date | None = None) -> list[LeParisienIssue]:
    """Fetch the latest published issues for a force."""

    menu = fetch_text(MENU_URL.format(force=force))
    issues = parse_menu(menu, force)
    if through_date is None:
        through_date = date.today()
    issues = [issue for issue in issues if issue.published_on <= through_date]
    return issues[-count:]


def parse_mfj(js_text: str) -> dict[str, Any]:
    """Parse an RCI `.mfj` JavaScript grid file into Python values."""

    body_match = re.search(r"var\s+gamedata\s*=\s*\{(.*)\};?\s*$", js_text, re.S)
    if not body_match:
        raise ValueError("could not find `var gamedata = {...}`")

    body = body_match.group(1)
    body = re.sub(r"(\n\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', body)
    body = "{" + body + "}"
    return ast.literal_eval(body)


def clean_clue(lines: list[str]) -> str:
    """Normalize clue lines while preserving French punctuation."""

    return " ".join(lines).replace("– ", "").replace("–", "").replace("- ", "-")


def _arrow_specs_for_cell(character: str) -> list[str]:
    modern_spec = DEPRECATED_ARROW_SPECS[character]
    return CELL_ARROW_SPECS[modern_spec]


def _read_answer(grid: list[str], row: int, column: int, direction: str) -> str:
    answer = ""
    while 0 <= row < len(grid) and 0 <= column < len(grid[row]):
        value = grid[row][column]
        if not value.isalpha() or not value.isupper():
            break
        answer += value
        if direction == "across":
            column += 1
        else:
            row += 1
    return answer


def enrich_grid(gamedata: dict[str, Any], *, force: int, number: str, published_on: date | None) -> dict[str, Any]:
    """Build a stable JSON-friendly puzzle representation."""

    grid = gamedata["grille"]
    definitions = list(gamedata["definitions"])
    definition_index = 0
    entries: list[dict[str, Any]] = []
    clue_cells: list[dict[str, Any]] = []

    for row, line in enumerate(grid):
        for column, character in enumerate(line):
            if not (character.isalpha() and character.islower()):
                continue

            cell_entries = []
            for arrow_spec in _arrow_specs_for_cell(character):
                if definition_index >= len(definitions):
                    raise ValueError("grid has more arrows than definitions")

                arrow = ARROWS[arrow_spec]
                start_row = row + arrow["row"]
                start_column = column + arrow["column"]
                direction = arrow["direction"]
                clue = clean_clue(definitions[definition_index])
                answer = _read_answer(grid, start_row, start_column, direction)

                entry = {
                    "entry_id": f"{definition_index + 1:03d}",
                    "clue": clue,
                    "answer": answer,
                    "length": len(answer),
                    "direction": direction,
                    "clue_cell": {"row": row, "column": column, "arrow": arrow_spec},
                    "start": {"row": start_row, "column": start_column},
                }
                entries.append(entry)
                cell_entries.append(entry["entry_id"])
                definition_index += 1

            clue_cells.append(
                {
                    "row": row,
                    "column": column,
                    "code": character,
                    "entries": cell_entries,
                }
            )

    if definition_index != len(definitions):
        raise ValueError("grid has fewer arrows than definitions")

    return {
        "source": "leparisien-rcijeux",
        "puzzle_id": f"mfleches_{force}_{number}",
        "force": force,
        "number": number,
        "published_on": published_on.isoformat() if published_on else None,
        "width": gamedata["nbcaseslargeur"],
        "height": gamedata["nbcaseshauteur"],
        "grid": grid,
        "clue_cells": clue_cells,
        "entries": entries,
        "raw": gamedata,
    }


def fetch_puzzle(force: int, number: str, published_on: date | None = None) -> dict[str, Any]:
    """Fetch and parse one Le Parisien mots fleches puzzle."""

    mfj_text = fetch_text(GRID_URL.format(force=force, number=number))
    gamedata = parse_mfj(mfj_text)
    return enrich_grid(gamedata, force=force, number=number, published_on=published_on)


def save_puzzles(puzzles: list[dict[str, Any]], output_dir: Path) -> None:
    """Write puzzle JSON files and an index file."""

    output_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for puzzle in puzzles:
        filename = f"{puzzle['puzzle_id']}.json"
        path = output_dir / filename
        path.write_text(json.dumps(puzzle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        index.append(
            {
                "file": filename,
                "puzzle_id": puzzle["puzzle_id"],
                "force": puzzle["force"],
                "number": puzzle["number"],
                "published_on": puzzle["published_on"],
                "entries": len(puzzle["entries"]),
            }
        )
    (output_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
