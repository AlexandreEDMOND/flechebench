"""Prompt templates for benchmark modes.

These helpers only format strings. They do not call language models.
"""

from __future__ import annotations

from flechebench.data.models import Entry, Puzzle


def render_clue_only_prompt(entry: Entry) -> str:
    """Format a clue-only prompt for one entry."""

    return (
        "Resous cette entree de mots fleches en francais.\n"
        f"Indice: {entry.clue}\n"
        f"Longueur: {entry.length}\n"
        "Reponds uniquement avec le mot."
    )


def render_pattern_aware_prompt(entry: Entry, pattern: str) -> str:
    """Format a pattern-aware prompt for one entry."""

    return (
        "Resous cette entree de mots fleches en francais.\n"
        f"Indice: {entry.clue}\n"
        f"Longueur: {entry.length}\n"
        f"Motif connu: {pattern}\n"
        "Reponds uniquement avec le mot."
    )


def render_full_grid_prompt(puzzle: Puzzle) -> str:
    """Format a simple full-grid prompt for a puzzle."""

    lines = [
        "Resous cette grille de mots fleches en francais.",
        f"Puzzle: {puzzle.puzzle_id}",
        f"Dimensions: {puzzle.width}x{puzzle.height}",
        "Entrees:",
    ]
    for entry in puzzle.entries:
        lines.append(
            "- "
            f"{entry.entry_id}: {entry.clue} "
            f"({entry.length}, {entry.direction.value}, "
            f"ligne {entry.start_row}, colonne {entry.start_column})"
        )
    lines.append("Retourne les reponses par identifiant d'entree.")
    return "\n".join(lines)
